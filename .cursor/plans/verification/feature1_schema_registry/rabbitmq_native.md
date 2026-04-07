# Feature 1: Schema Registry - RabbitMQ Native Check

## Query
Does RabbitMQ natively support schema validation, JSON Schema, or message contract enforcement?

## Context7 MCP Findings

**Source**: RabbitMQ documentation (https://www.rabbitmq.com/docs/)

**Key findings**:
- ✅ **Message properties validation**: RabbitMQ validates certain message properties like `user-id` (must match connection user)
- ✅ **Exchange declaration validation**: Enforces type consistency, prevents redeclaration with different types
- ✅ **Content-type header**: Applications can set `content_type` property (e.g., `application/json`), but RabbitMQ does NOT validate payload against it
- ❌ **No JSON Schema validation**: No native support for validating message payloads against JSON Schema
- ❌ **No schema registry**: No built-in schema versioning or compatibility checking

**What "schema" means in RabbitMQ**:
RabbitMQ's "schema" refers to **topology metadata** (users, vhosts, queues, exchanges, bindings) for import/export, **NOT** message payload validation.

## Web Search Cross-Verification

**Stack Overflow finding** (2022, still relevant 2026):
> "Is there a way to validate the routing key format or a message schema for RabbitMQ?"
> 
> Answer: "No, RabbitMQ does not natively support message schema validation or routing key format validation out-of-the-box. You would need a custom plugin or application-level validation."

**Third-party tools found**:
- **rabbitmq-schema** (Node.js npm package): Provides JSON Schema validation for messages, but this is **application-level**, not broker-level
- **Custom plugin approach**: Would require developing a RabbitMQ plugin (similar to Message Timestamp plugin)

## Verdict

**NOT COVERED** - RabbitMQ broker does not natively support:
- ❌ JSON Schema validation
- ❌ Schema versioning
- ❌ Compatibility checks
- ❌ Schema registry functionality
- ❌ Message payload validation against schemas

**What IS supported**:
- ✅ Message property validation (user-id, headers structure)
- ✅ Topology schema export/import (not message schema)
- ✅ Content-type header (metadata only, no validation)

**Validation approach in RabbitMQ ecosystem**:
- **Application-level**: Validate before publish / after consume
- **Third-party libraries**: rabbitmq-schema (Node.js) or similar
- **Custom plugins**: Possible but requires C/Erlang development

## Impact on Feature 1

RabbitMQ provides **no alternative** to custom schema validation. If we're publishing to RabbitMQ, schema validation must happen:
1. In the eventing microservice (before publishing to RabbitMQ)
2. In downstream consumers (after consuming from RabbitMQ)
3. OR via custom RabbitMQ plugin (not recommended due to complexity)

**Conclusion**: Custom schema registry implementation remains necessary for RabbitMQ path.
