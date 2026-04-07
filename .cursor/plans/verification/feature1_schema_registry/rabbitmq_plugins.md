# Feature 1: Schema Registry - RabbitMQ Plugins Check

## Query
RabbitMQ plugins for schema validation, message contracts, or JSON Schema support

## Web Search Findings

**Key finding**: RabbitMQ has **no official plugins** for schema validation or schema registry functionality as of 2026.

## Available Third-Party Solutions

### 1. rabbitmq-schema (Node.js library, not a plugin)
- **Type**: Application-level library (npm package)
- **Last updated**: 2022
- **Capabilities**:
  - JSON Schema validation for messages
  - Topology validation (exchanges, queues, bindings)
  - Schema-aware routing
- **Limitation**: **Not a RabbitMQ plugin** - runs in application code, not broker

### 2. rabbitmq-message-validator (Custom plugin, experimental)
- **Author**: Luke Bakken (RabbitMQ team member)
- **Type**: Custom RabbitMQ plugin (based on Message Timestamp plugin)
- **Purpose**: Validate message schemas and routing key formats at broker level
- **Status**: Experimental, **not officially supported**
- **Limitation**: Requires custom plugin development and maintenance

### 3. queue-pilot (MCP server, not a plugin)
- **Version**: v0.5.3 (2026)
- **Type**: External MCP server supporting both RabbitMQ and Kafka
- **Capabilities**: JSON Schema validation for message inspection and publishing
- **Limitation**: External service, not broker-level validation

### 4. External Schema Registry integration
- **Approach**: Use Confluent/Apicurio Schema Registry with RabbitMQ
- **Implementation**: Application validates against Schema Registry before publishing to RabbitMQ
- **Limitation**: Adds external dependency, validation not enforced by RabbitMQ broker

## rabbitmq-conf (Configuration validation, not message validation)
- **Version**: v0.20.0 (updated 2026)
- **Purpose**: Validates RabbitMQ **configuration files**, not message payloads
- **Scope**: Core and tier-1 plugin configuration keys
- **Not applicable**: Does not validate message schemas

## Verdict

**NOT COVERED** - RabbitMQ plugins do not provide:
- ❌ No official schema validation plugin
- ❌ No official schema registry plugin
- ❌ No JSON Schema enforcement at broker level

**Available workarounds**:
1. **Application-level validation**: Use libraries like rabbitmq-schema in Node.js
2. **Custom plugin**: Develop RabbitMQ plugin (requires Erlang expertise, not officially supported)
3. **External Schema Registry**: Validate against Confluent/Apicurio before publishing (adds infrastructure)
4. **MCP server**: Use queue-pilot or similar external validation service

**Why no official plugin exists**:
- RabbitMQ design philosophy: Keep broker lightweight, push validation to clients
- Protocol agnostic: RabbitMQ is designed to route **any** message format
- Complexity: Schema validation requires language-specific parsers (JSON, Avro, Protobuf)

## Impact on Feature 1

**Conclusion**: RabbitMQ ecosystem provides no drop-in solution for schema validation. Custom implementation remains necessary.

**Validation strategy for RabbitMQ path**:
- ✅ Validate in eventing microservice before publishing to RabbitMQ (recommended)
- ✅ Store schema registry in database/in-memory (lightweight, no external infrastructure)
- ✅ CloudEvents + data_version integration (custom requirement not covered by generic schema registries)
