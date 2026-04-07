# Feature 8: Kafka-RabbitMQ Bridge - All Sources Summary

## Feature Requirement
Consume from Kafka, route to RabbitMQ exchanges with routing keys (single-chain architecture)

## Kafka Plugins

### Kafka Connect RabbitMQ Sink
- ✅ **Exists**: Kafka Connect RabbitMQ sink connector
- ✅ **Functionality**: Reads from Kafka topics, writes to RabbitMQ exchanges
- ⚠️ **External process**: Requires Kafka Connect cluster (separate infrastructure)
- ⚠️ **Configuration-based**: JSON config files, not code
- ⚠️ **Limited customization**: Fixed routing logic via connector config
- ❌ **No custom business logic**: Cannot inject schema validation, circuit breakers, rate limiting

### Example Config
```json
{
  "connector.class": "com.datamountaineer.streamreactor.connect.rabbitmq.sink.RabbitMQSinkConnector",
  "topics": "kafka-topic",
  "connect.rabbitmq.host": "localhost",
  "connect.rabbitmq.exchange.name": "rabbit-exchange"
}
```

### Verdict: **Exists but insufficient** - No custom logic injection

## RabbitMQ Plugins

### RabbitMQ Shovel
- ✅ **Exists**: Shovel plugin for message routing between brokers
- ⚠️ **RabbitMQ → RabbitMQ**: Primarily for RabbitMQ-to-RabbitMQ transfers
- ❌ **No Kafka source**: Shovel does NOT consume from Kafka
- ❌ **Not applicable**: Cannot use for Kafka-to-RabbitMQ bridge

### Verdict: **NOT APPLICABLE** - Shovel doesn't support Kafka source

## FastStream

### Multi-Broker Support
- ✅ **Multi-broker applications**: FastStream supports multiple brokers in one app
  ```python
  kafka_broker = KafkaBroker("localhost:9092")
  rabbit_broker = RabbitBroker("amqp://localhost")
  app = FastStream(kafka_broker)  # or rabbit_broker
  ```
- ✅ **Consume from one, publish to another**:
  ```python
  @kafka_broker.subscriber("kafka-topic")
  async def bridge_handler(msg: dict) -> None:
      # Process message
      await rabbit_broker.publish(msg, exchange="rabbit-exchange")
  ```
- ✅ **Full control**: Can inject middleware, validation, routing logic
- ✅ **Single codebase**: All logic in Python, no external processes

### Verdict: **PATTERN SUPPORTED** - FastStream provides the building blocks

## Our Requirements (Why Generic Solutions Don't Fit)

### Custom Logic Needed
1. **Schema validation**: Validate against JSON Schema before publishing to RabbitMQ
2. **Circuit breaker**: Stop publishing to RabbitMQ if it's down
3. **Rate limiting**: Control message flow rate
4. **Custom routing**: Build routing key from CloudEvents metadata
5. **OTel tracing**: Link Kafka consume span to RabbitMQ publish span
6. **Prometheus metrics**: Emit custom metrics for bridge operations

### Kafka Connect Limitations
- ❌ Cannot inject Python code
- ❌ Cannot use FastStream middleware
- ❌ Cannot integrate with schema registry (our custom implementation)
- ❌ Requires separate Kafka Connect cluster infrastructure
- ❌ Config-driven only (no code flexibility)

## Final Decision: **KEEP**

### Why KEEP
1. **Custom business logic**: Schema validation, routing, circuit breaker, rate limiting
2. **FastStream integration**: Use FastStream middleware for all cross-cutting concerns
3. **Single codebase**: All logic in one Python service, no external Kafka Connect
4. **Observability**: OTel tracing, Prometheus metrics, custom logging
5. **Flexibility**: Can change routing logic without redeploying Kafka Connect

### What We're NOT Duplicating
- ❌ NOT re-implementing Kafka consumer (FastStream provides this)
- ❌ NOT re-implementing RabbitMQ publisher (FastStream provides this)
- ✅ **Implementing**: Bridge **business logic** (routing, validation, resilience)

### Implementation (Confirmed Correct)

**Our plan** already uses FastStream multi-broker pattern:

```python
# Bridge consumer
@kafka_broker.subscriber("events")
async def kafka_to_rabbitmq_bridge(event: CloudEvent) -> None:
    # 1. Validate schema
    schema_registry.validate(event.type, event.data)
    
    # 2. Build routing key
    routing_key = routing_key_builder.build(event.type, event.data)
    
    # 3. Publish to RabbitMQ (with middleware: circuit breaker, rate limiter, OTel)
    await rabbit_publisher.publish(
        exchange="events",
        routing_key=routing_key,
        message=event.model_dump()
    )
```

**Middleware stacking** (automatic via FastStream):
```python
kafka_broker = KafkaBroker(..., middlewares=[
    TelemetryMiddleware(),  # OTel tracing
    CircuitBreakerMiddleware(),  # Resilience
    RateLimiterMiddleware(),  # Backpressure
])

rabbit_broker = RabbitBroker(..., middlewares=[
    TelemetryMiddleware(),  # OTel tracing
    CircuitBreakerMiddleware(),  # Resilience
    RateLimiterMiddleware(),  # Backpressure
])
```

### Comparison to Kafka Connect

| Feature | Kafka Connect | Our Bridge | Winner |
|---------|--------------|-----------|--------|
| Infrastructure | Separate cluster | Embedded | ✅ Our bridge |
| Configuration | JSON files | Python code | ✅ Our bridge |
| Custom logic | Limited plugins | Full Python code | ✅ Our bridge |
| Schema validation | Via connector plugin | Custom registry | ✅ Our bridge |
| Circuit breaker | Not supported | FastStream middleware | ✅ Our bridge |
| Rate limiting | Not supported | aiolimiter middleware | ✅ Our bridge |
| OTel tracing | Via Java agent | FastStream TelemetryMiddleware | ✅ Our bridge |
| Operational overhead | High (separate cluster) | Low (single service) | ✅ Our bridge |
| Battle-tested | Very mature | New implementation | ❌ Kafka Connect |

### When to Use Kafka Connect Instead
- ✅ If organization already has Kafka Connect infrastructure
- ✅ If bridge logic is simple (no custom validation/routing)
- ✅ If using Java/Scala ecosystem (not Python)
- ✅ If need connector ecosystem (100+ connectors)

### Our Case
- ❌ No existing Kafka Connect infrastructure
- ❌ Complex business logic (schema validation, custom routing)
- ✅ Python ecosystem (FastStream, Pydantic, aiolimiter)
- ✅ Single-service deployment preferred

## Conclusion

**KEEP** - Kafka Connect exists but doesn't fit our requirements. FastStream provides the multi-broker pattern we need with full control over business logic.

**Implementation approach**: Use FastStream's multi-broker support to build custom bridge with schema validation, circuit breaker, rate limiting, and OTel tracing - all via FastStream middleware.
