# Feature Verification Log

## Step 1: Verify Schema Registry & Validation (Feature 1)

**Target:** FastStream Pydantic routing, CloudEvents integration, Kafka native Schema Registry, Confluent Schema Registry plugins.
**Query Focus:** Does FastStream natively support JSON Schema validation and version evolution checking? Is there a FastStream plugin for Confluent Schema Registry that eliminates the need for our custom `SchemaRegistry` and `JsonSchemaValidator` classes?

**Analysis & Findings:**
1. **FastStream Native Validation:** FastStream *natively* supports Pydantic models for message validation and serialization. It validates incoming messages against Pydantic definitions directly via the `@broker.subscriber` and `@broker.publisher` decorators.
2. **Confluent Schema Registry Plugin:** There is a third-party plugin available: `faststream-schema-registry`. It provides a `SchemaRegistryMiddleware` for `KafkaBroker` that integrates with Confluent Schema Registry and supports both Avro and JSON schemas. It uses `dataclasses-avroschema` and `python-schema-registry-client`.
3. **Decision:** 
    * We *could* use `faststream-schema-registry` to avoid building our own registry client *if* we wanted to run a dedicated Confluent Schema Registry service.
    * However, FastStream's built-in Pydantic validation handles the exact payload validation natively. 
    * For *strict version evolution checking* in a decentralized way without standing up a Confluent Schema Registry cluster (which is heavy for some deployments), our custom `SchemaRegistry` (which acts as an in-memory/DB-backed lightweight registry for JSON schemas) and `JsonSchemaValidator` (using `jsonschema` lib) provide value, particularly when enforcing `data_version` compatibility rules across services without external dependencies.
    * **Conclusion for Plan:** We should *keep* the custom Schema Registry implementation in the plan. While `faststream-schema-registry` exists, relying on pure FastStream Pydantic + our lightweight JSON schema registry keeps the infrastructure simpler and more universal (works for RabbitMQ too, whereas Confluent Schema Registry is heavily Kafka-centric).

**Action for Main Plan:** Keep Feature 1. No changes required.

## Step 2: Verify OpenTelemetry Wiring (Feature 2)

**Target:** FastStream OpenTelemetry Middleware.
**Query Focus:** We know FastStream has `KafkaTelemetryMiddleware` and `RabbitTelemetryMiddleware`. Verify exactly what manual setup is still required (e.g., `TracerProvider` initialization) versus what the middleware handles automatically. Can we simplify `otel_setup.py` further using standard OpenTelemetry auto-instrumentation (`opentelemetry-instrument`)?

**Analysis & Findings:**
1. **FastStream Native OTel:** FastStream provides `TelemetryMiddleware` (or `KafkaTelemetryMiddleware` / `RabbitTelemetryMiddleware` in older versions) that adheres to standard semantic conventions for messaging systems.
2. **Auto-instrumentation:** There is an `opentelemetry-instrumentation-faststream` package (v0.1.3+) that provides a `FastStreamInstrumentator`. By calling `FastStreamInstrumentator().instrument()`, it automatically instruments brokers without manually adding `TelemetryMiddleware` to each broker instance. 
3. **Provider Setup:** Regardless of whether we use manual middleware or `opentelemetry-instrumentation-faststream`, we *still* need to configure the core `TracerProvider` and `MeterProvider` for the application (e.g., pointing it to Jaeger/Prometheus). FastStream's tools only handle the *instrumentation* (creating spans for consume/publish), not the *pipeline* (exporting those spans).
4. **Decision:** 
    * The setup in `otel_setup.py` to initialize the global `TracerProvider` and `OTLPSpanExporter` is absolutely required.
    * We can simplify the *wiring* into FastStream by using `opentelemetry-instrumentation-faststream` instead of manually importing and attaching `TelemetryMiddleware` to every broker instance. 
    * **Conclusion for Plan:** Keep Feature 2, but modify the implementation detail slightly to prefer `opentelemetry-instrumentation-faststream` for zero-code instrumentation of the brokers, while keeping the core provider setup.

**Action for Main Plan:** Keep Feature 2. Update the implementation detail to use `opentelemetry-instrumentation-faststream` for auto-instrumentation.

## Step 3: Verify Circuit Breaker (Feature 3)

**Target:** FastStream, AIOKafka, aio-pika, RabbitMQ.
**Query Focus:** Do FastStream brokers have a built-in circuit breaker middleware? Do the underlying drivers (`aiokafka`, `aio-pika`) handle connection backoff internally in a way that makes a custom application-level CircuitBreaker redundant?

**Analysis & Findings:**
1. **FastStream Middleware:** FastStream provides a robust middleware system (`BaseMiddleware` with `consume_scope`, `publish_scope`, etc.) and explicitly suggests it can be used for "implementing retry logic, circuit breakers, rate limiting". However, it does *not* ship with a built-in `CircuitBreakerMiddleware`.
2. **Driver Capabilities:** The underlying drivers (`aiokafka`, `aio-pika`) handle *connection* retries and backoffs automatically, but they do not provide *application-level* circuit breaking (e.g., stopping consumption if a downstream database is failing repeatedly).
3. **Decision:** We need a custom implementation for an application-level circuit breaker to pause message processing when downstream dependencies (like the DB or an external API) are unhealthy. Building a custom FastStream `BaseMiddleware` that uses an internal state machine (like the one proposed in the plan) is the correct architectural approach.
    * **Conclusion for Plan:** Keep Feature 3. The custom `CircuitBreaker` logic and integrating it as a FastStream middleware is the standard way to achieve this.

**Action for Main Plan:** Keep Feature 3. No changes required.

## Step 4: Verify Consumer Group Config (Feature 5)

**Target:** FastStream KafkaBroker config, AIOKafka.
**Query Focus:** Verify the exact parameter names in FastStream/AIOKafka for static membership (`group.instance.id`) and cooperative rebalancing (`partition.assignment.strategy`). Ensure we aren't writing custom rebalance listeners if configuration flags suffice.

**Analysis & Findings:**
1. **Static Membership:** AIOKafka natively supports static membership via the `group_instance_id` parameter in `AIOKafkaConsumer`. This implements KIP-345. FastStream allows passing custom kwargs to the underlying AIOKafka client.
2. **Cooperative Rebalancing:** AIOKafka uses `RoundRobinPartitionAssignor` by default. While Kafka Java clients have `CooperativeStickyAssignor`, AIOKafka's support for cooperative-sticky strategies is less natively exposed or documented as a simple flag in the same way.
3. **Decision:** 
    * We don't need custom Python code for *static membership*; it's just passing `group_instance_id=os.environ.get("HOSTNAME")` via FastStream's broker configuration.
    * For *cooperative rebalancing*, since AIOKafka might not have a built-in drop-in class for it equivalent to Java's, or it requires specific setup, we should ensure the plan focuses on configuring `partition_assignment_strategy` if available, but primarily focus on `group_instance_id` for static membership to reduce rebalances.
    * **Conclusion for Plan:** Keep Feature 5, but emphasize that it's purely a configuration task (modifying `KafkaBroker` instantiation in `broker_config.py` to pass `group_instance_id`), not writing custom rebalance listener logic.

**Action for Main Plan:** Keep Feature 5. Clarify that it involves passing kwargs to FastStream/AIOKafka, not writing complex custom assignment classes.

## Step 5: Verify Event Replay API (Feature 6)

**Target:** Kafka native features, FastStream CLI, RabbitMQ Streams.
**Query Focus:** Kafka retains data, but does FastStream provide a native utility or CLI for triggering replays from specific offsets/timestamps? Is building a custom HTTP API the only way, or is there a standard ecosystem tool (like Kafka UI or ksqlDB) that negates the need for custom API code?

**Analysis & Findings:**
1. **FastStream Native Replay:** FastStream does *not* have a dedicated, built-in "Replay API" or a magical decorator argument to trigger replays dynamically at runtime. It has basic startup config like `auto_offset_reset="earliest"`, but that's for cold starts, not targeted replays on running services.
2. **Kafka Ecosystem Tools:** Tools like `kafka-consumer-groups.sh` (CLI) or UI tools (Kafka-UI, AKHQ) allow you to manually reset consumer group offsets. This is the "native" way to do replays in Kafka.
3. **Decision:** 
    * If we want *programmatic* control over replays within our application (e.g., an admin clicks a button in our specific back-office app to replay events for a specific user ID), building an HTTP API that spins up a temporary FastStream consumer starting from a specific timestamp is necessary.
    * If we only care about operational/manual replays (e.g., DevOps needs to re-process a failed batch), resetting offsets via a tool like Kafka-UI is vastly superior and requires zero code.
    * **Conclusion for Plan:** Given the EDA context, providing an application-level API for targeted replays (e.g., replaying by `aggregate_id`) is a common advanced pattern that standard Kafka CLI tools struggle with (they reset offsets for whole partitions, not filtering by specific payload fields). We will keep the custom Replay API to allow for granular, programmatic replays that standard offset-resetting cannot easily achieve.

**Action for Main Plan:** Keep Feature 6.

## Step 6: Verify Rate Limiting / Backpressure (Feature 7)

**Target:** FastStream, Kafka, RabbitMQ.
**Query Focus:** We know RabbitMQ has native backpressure. Does FastStream provide a built-in rate-limiting middleware for Kafka publishers? Does AIOKafka have producer-side backpressure we can enable via config rather than using `aiolimiter`?

**Analysis & Findings:**
1. **RabbitMQ:** RabbitMQ has built-in credit-based flow control (prefetch count). FastStream utilizes this natively.
2. **Kafka/FastStream:** FastStream provides `KafkaBrokerConfig` with parameters like `max_batch_size` and `linger_ms`, but does not provide a native "Rate Limiter Middleware" for token-bucket style API rate limiting on publishers. AIOKafka has internal buffer limits, but not API-level request rate limiters.
3. **Decision:** Using a library like `aiolimiter` wrapped in a custom FastStream publisher middleware is the correct approach to enforce strict requests-per-second limits when publishing to Kafka, preventing the application from overwhelming the broker or downstream systems if there's a sudden spike in internal processing.
    * **Conclusion for Plan:** Keep Feature 7. The proposed integration with `aiolimiter` is the correct path.

**Action for Main Plan:** Keep Feature 7.

## Step 7: Verify Kafka-to-RabbitMQ Bridge (Feature 8)

**Target:** Kafka Connect, RabbitMQ Shovel/Federation, FastStream.
**Query Focus:** Is there a standard Kafka Connect sink connector for RabbitMQ? Is there a RabbitMQ plugin that natively consumes from Kafka? If so, does it eliminate the need for our custom Python `KafkaToRabbitMQBridge` consumer?

**Analysis & Findings:**
1. **Kafka Connect:** Yes, Confluent provides a `kafka-connect-rabbitmq-sink` connector that reads from Kafka and publishes to RabbitMQ.
2. **Decision:** 
    * Using Kafka Connect is the "industry standard" native way to bridge Kafka and RabbitMQ without writing code.
    * However, introducing Kafka Connect requires deploying and managing a separate JVM-based cluster (the Connect workers) and managing connector configurations via REST API. 
    * Our system currently consists of Python FastAPI/FastStream microservices. Building a bridge using FastStream (consuming from `KafkaBroker` and publishing to `RabbitBroker` in the same Python process) keeps the infrastructure homogenous (pure Python), requires zero new deployment components, and leverages our existing Pydantic validation and OTel wiring natively.
    * **Conclusion for Plan:** Keep the custom FastStream bridge. While Kafka Connect exists, for a system already heavily invested in FastStream, a Python-based bridge is operationally simpler and fits the existing paradigm perfectly.

**Action for Main Plan:** Keep Feature 8. Maintain the FastStream-based Python bridge for operational simplicity over introducing JVM-based Kafka Connect infrastructure.

## Step 8: Verify DLQ Admin API (Feature 9)

**Target:** RabbitMQ DLX, Kafka DLQ, FastStream, external tools.
**Query Focus:** If RabbitMQ handles DLX natively, do we need an HTTP API to inspect it? Can standard tools like RabbitMQ Management UI or Kafka-UI completely replace the need for our custom `/dlq` GET/POST retry endpoints?

**Analysis & Findings:**
1. **Native DLQs:** FastStream supports RabbitMQ's native DLX via queue parameters. For Kafka, DLQ requires custom logic (which we already built in `KafkaDeadLetterHandler`).
2. **Admin Tools:** RabbitMQ Management UI allows viewing messages in a DLQ and moving them via the "Shovel" plugin. Kafka-UI allows viewing messages in a Kafka DLQ topic.
3. **Decision:** 
    * Standard UIs are great for ops, but they don't integrate with our application logic (e.g., our custom Pydantic schemas, specific retry policies, or security context).
    * If we want to programmatically inspect the DLQ or trigger retries from our own admin dashboard, an HTTP API is required. 
    * Since our Kafka DLQ is entirely custom (a specific topic format we defined), standard tools won't understand our specific metadata headers as well as our own API would.
    * **Conclusion for Plan:** Keep the DLQ Admin API. It provides a programmatic, application-aware way to manage failed messages that generic broker UIs cannot offer.

**Action for Main Plan:** Keep Feature 9.

## Step 9: Verify Event Contract Testing (Feature 10)

**Target:** FastStream, Pydantic, Confluent Schema Registry.
**Query Focus:** Is there a native FastStream or Pydantic feature for enforcing semantic version compatibility (`data_version`) across consumers, eliminating the need for `EventContractValidator`?

**Analysis & Findings:**
1. **Pydantic:** Pydantic is great for structural validation (does this JSON match this class?), but it does not inherently understand "semantic version compatibility" rules (e.g., "version 1.2.0 is compatible with 1.1.0 but not 2.0.0").
2. **FastStream:** FastStream delegates schema validation to Pydantic and AsyncAPI generation. It doesn't have an active runtime contract test runner.
3. **Decision:** To enforce our specific rules about `data_version` compatibility (major version changes break, minor versions are backwards compatible), we need custom logic. The proposed `EventContractValidator` in the tests suite is exactly what is needed for this domain-specific rule.
    * **Conclusion for Plan:** Keep Feature 10. Contract testing for custom semantic versioning rules requires custom test utilities.

**Action for Main Plan:** Keep Feature 10.

## Step 10: Verify Prometheus Metrics (Feature 12)

**Target:** FastStream metrics, OpenTelemetry metrics.
**Query Focus:** If we enable OpenTelemetry, does `opentelemetry-exporter-prometheus` automatically expose the required metrics (like handler latency) via FastStream's OTel middleware, eliminating the need for custom `promExporter` dispatch hooks?

**Analysis & Findings:**
1. **FastStream Native Prometheus:** FastStream actually has a built-in `PrometheusMiddleware` (e.g., `faststream.kafka.prometheus.KafkaPrometheusMiddleware`) available if installed with `faststream[prometheus]`. It integrates directly with `prometheus_client` to expose metrics like message count, processing time, and errors.
2. **Decision:** 
    * The main plan proposed writing custom dispatch hooks to expose Prometheus metrics.
    * This is entirely redundant. FastStream's built-in `PrometheusMiddleware` does exactly this out of the box and provides an ASGI app export it via a `/metrics` route.
    * **Conclusion for Plan:** We must modify Feature 12. Do NOT write custom dispatch hooks for Prometheus. Instead, use FastStream's native `PrometheusMiddleware`.

**Action for Main Plan:** **MODIFY Feature 12.** Remove the custom `promExporter` and dispatch hooks logic. Replace it with instructions to use `faststream.kafka.prometheus.KafkaPrometheusMiddleware` and `prometheus_client.make_asgi_app()`.

## Step 11: Final Review and Plan Update

The verification process is complete. 
1. Features 1, 3, 5, 6, 7, 8, 9, 10 remain valid as custom implementations because native tools either don't exist, don't fit our specific architectural constraints (e.g., avoiding JVM for Connect), or require custom business logic.
2. Feature 2 should be slightly tweaked to prefer `opentelemetry-instrumentation-faststream`.
3. Feature 12 must be heavily modified to use FastStream's native `PrometheusMiddleware` instead of custom dispatch hooks.

I will now update the main plan (`add_eventing_features_12bad60a.plan.md`) to reflect these findings.