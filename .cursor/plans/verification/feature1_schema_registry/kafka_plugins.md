# Feature 1: Schema Registry - Kafka Plugins Check

## Query
Confluent Schema Registry vs Apicurio Schema Registry for JSON Schema support - features, compatibility modes, version management

## Context7 MCP Findings (Confluent Schema Registry)

**Source**: /confluentinc/schema-registry documentation

**Key features found**:

### JSON Schema Support
- ✅ Full JSON Schema support (draft_7 specification)
- ✅ `KafkaJsonSchemaSerializer` and `KafkaJsonSchemaDeserializer` for client-side validation
- ✅ Auto-registration of schemas from POJOs
- ✅ Schema validation before serialization (`FAIL_INVALID_SCHEMA`)

### Versioning
- ✅ Version tracking per subject
- ✅ REST API: `POST /subjects/{subject}/versions` to register new versions
- ✅ Global schema ID assignment
- ✅ Version history tracking

### Compatibility Modes
- ✅ **BACKWARD**: New schema can read data written with previous schema
- ✅ **FORWARD**: Previous schema can read data written with new schema
- ✅ **FULL**: Both BACKWARD and FORWARD compatible
- ✅ **NONE**: No compatibility checks
- ✅ **BACKWARD_TRANSITIVE**, **FORWARD_TRANSITIVE**, **FULL_TRANSITIVE**: Extended modes
- ✅ Global and subject-specific compatibility configuration via REST API

### API Endpoints
```
GET /config - Get global compatibility
PUT /config - Set global compatibility
GET /config/{subject} - Get subject-specific compatibility
PUT /config/{subject} - Set subject-specific compatibility
DELETE /config/{subject} - Revert to global compatibility
POST /subjects/{subject}/versions - Register new schema version
```

## Web Search Cross-Verification

**Apicurio Registry findings**:
- ✅ Also supports JSON Schema, Avro, Protobuf, OpenAPI, AsyncAPI
- ✅ Provides Confluent-compatible (ccompat) API layer as drop-in replacement
- ✅ Schema dereferencing for inlining references
- ⚠️ Minor API incompatibilities with Confluent (e.g., `references` field handling)

**Key insight**: Both registries are **external infrastructure components** that must be deployed separately from Kafka broker.

## Verdict

**FULLY COVERED by external plugins** - Both Confluent Schema Registry and Apicurio Registry provide:
- ✅ JSON Schema validation
- ✅ Schema versioning
- ✅ Compatibility checks (BACKWARD, FORWARD, FULL, TRANSITIVE variants)
- ✅ REST API for schema management
- ✅ Client serializers/deserializers with automatic validation

**Trade-offs**:

### Option 1: Use Confluent Schema Registry
- **Pros**: Industry standard, excellent documentation, battle-tested
- **Cons**: Requires additional infrastructure, operational overhead, not part of Kafka broker

### Option 2: Use Apicurio Registry
- **Pros**: Open-source, Confluent-compatible API, more permissive license
- **Cons**: Smaller community, minor API incompatibilities, requires additional infrastructure

### Option 3: Custom schema registry (current plan)
- **Pros**: No external infrastructure, tailored to exact use case, CloudEvents + data_version integration
- **Cons**: Development and maintenance overhead, re-inventing well-solved problem

## Impact on Feature 1

**DECISION POINT**: Should we:
- **A) SIMPLIFY**: Adopt Confluent/Apicurio Schema Registry instead of custom implementation
- **B) KEEP**: Implement custom lightweight schema registry for CloudEvents + data_version integration

**Recommendation**: If the project already has Schema Registry infrastructure OR plans to use it for other services, **SIMPLIFY** to external registry. If this is a standalone microservice with specific CloudEvents requirements, **KEEP** custom implementation for simplicity.
