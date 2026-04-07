# Feature 1: Schema Registry - Kafka Native Check

## Query
Does Kafka broker natively support JSON Schema validation, versioning, or compatibility checks?

## Context7 MCP Findings

**Source**: Apache Kafka documentation (https://github.com/apache/kafka/blob/trunk/docs/operations/multi-tenancy.md)

**Key finding**:
> "Kafka does not include a schema registry, but there are third-party implementations available. A schema registry manages the event schemas and maps the schemas to topics, so that producers know which topics are accepting which types (schemas) of events, and consumers know how to read and parse events in a topic."

**Additional findings**:
- Kafka provides serialization/deserialization interfaces (`Serializer`, `Deserializer`, `Serde`)
- Custom JSON Serdes can be implemented by developers
- No built-in JSON Schema validation, versioning, or compatibility checking

## Web Search Cross-Verification (2026)

**Key findings**:
1. **KIP-940**: Apache Kafka is developing "Broker extension point for validating record contents at produce time" - but this is still **under discussion**, no release date specified
2. **Current state**: Kafka broker does NOT natively validate schemas
3. **Confluent Cloud**: Offers broker-side schema ID validation, but only on Dedicated clusters (proprietary feature, not open-source Kafka)
4. **Workaround**: Schema validation currently relies on client-side serializers/deserializers and external Schema Registry

## Verdict

**NOT COVERED** - Kafka broker does not natively support:
- JSON Schema validation
- Schema versioning
- Compatibility checks
- Schema registry functionality

**Reason**: All schema-related features require external Schema Registry (e.g., Confluent Schema Registry, Apicurio Registry). KIP-940 may change this in the future, but as of 2026, it's still under discussion.

**Impact on Feature 1**: Custom schema registry implementation is still needed unless we adopt external Schema Registry solution.
