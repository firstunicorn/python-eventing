# Feature 1: Schema Registry - Final Verdict

## Summary of Findings

| Source | JSON Schema Support | Versioning | Compatibility Modes | Verdict |
|--------|-------------------|------------|-------------------|---------|
| **Kafka native** | ❌ No | ❌ No | ❌ No | NOT COVERED |
| **Kafka plugins** | ✅ Yes (Confluent/Apicurio) | ✅ Yes | ✅ Yes (BACKWARD/FORWARD/FULL/TRANSITIVE) | FULLY COVERED |
| **RabbitMQ native** | ❌ No | ❌ No | ❌ No | NOT COVERED |
| **RabbitMQ plugins** | ❌ No official plugins | ❌ No | ❌ No | NOT COVERED |
| **FastStream** | ⚠️ Pydantic only | ❌ No | ❌ No | NOT COVERED |

## Key Insights

### 1. Kafka + RabbitMQ Native: No Support
- Both message brokers are **schema-agnostic** by design
- Neither validates message payloads
- Schema validation is pushed to clients/applications

### 2. External Schema Registry: Full Coverage
**Confluent Schema Registry** and **Apicurio Registry** provide:
- ✅ JSON Schema, Avro, Protobuf support
- ✅ Schema versioning with global IDs
- ✅ Compatibility modes (BACKWARD, FORWARD, FULL, TRANSITIVE)
- ✅ REST API for schema management
- ✅ Client serializers/deserializers with automatic validation

**Trade-off**: Requires deploying and operating external infrastructure

### 3. FastStream: Complementary, Not Replacement
- FastStream validates **individual messages** using Pydantic models
- Does NOT manage schemas, versions, or compatibility
- Works at **runtime** (per-message), not **schema management** (cross-service coordination)

## Decision Framework

### Option A: SIMPLIFY - Use External Schema Registry

**When to choose**:
- ✅ Organization already uses Confluent/Apicurio Schema Registry
- ✅ Multiple services need schema coordination
- ✅ Industry-standard compliance required
- ✅ Team has ops expertise for managing registry infrastructure

**Pros**:
- Battle-tested, production-ready
- Industry standard
- Rich tooling ecosystem
- Automatic client-side validation

**Cons**:
- Additional infrastructure (Schema Registry cluster + storage)
- Operational overhead (monitoring, backups, upgrades)
- Network dependency (registry must be available)
- May be overkill for single-service use case

**Implementation**:
```python
# Use Confluent serializers with FastStream
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer

schema_registry_client = SchemaRegistryClient({"url": "http://localhost:8081"})
serializer = JSONSerializer(schema_str, schema_registry_client)

@broker.subscriber("events")
async def handle(msg: bytes) -> None:
    # Validate against registered schema
    data = serializer.deserialize(msg)
```

### Option B: KEEP - Custom Lightweight Schema Registry

**When to choose**:
- ✅ Single microservice or small team
- ✅ CloudEvents + data_version specific requirements
- ✅ Want to avoid external infrastructure
- ✅ Schema validation is needed but not schema coordination across many services

**Pros**:
- No external dependencies
- Tailored to exact CloudEvents use case
- Simpler deployment (embedded in service)
- Lower operational overhead

**Cons**:
- Re-implementing well-solved problem
- Development and maintenance burden
- May need migration later if requirements grow

**Implementation** (as planned):
```python
class SchemaRegistry:
    """Lightweight JSON Schema registry with versioning and compatibility checks."""
    
    def register_schema(self, event_type: str, version: str, schema: dict) -> None: ...
    def get_schema(self, event_type: str, version: str) -> dict: ...
    def check_compatibility(self, event_type: str, new_schema: dict, mode: CompatibilityMode) -> bool: ...
    def validate_payload(self, event_type: str, version: str, payload: dict) -> None: ...
```

## Final Verdict: KEEP (with caveat)

**Decision**: **KEEP custom implementation** for this project

**Rationale**:
1. **Architecture**: Single eventing microservice, not multi-service mesh
2. **Requirements**: CloudEvents + data_version integration (specific to this use case)
3. **Deployment**: Avoid operational overhead of external Schema Registry
4. **Scope**: Feature scope is limited to validating events in this microservice before publishing to RabbitMQ

**However**, document this as a **future migration path**:
- If organization adopts Confluent/Apicurio Schema Registry later
- If multiple services need schema coordination
- If schema governance becomes a cross-team concern

Then migrate to external registry with minimal code changes (interface remains the same).

## Implementation Guidance

**Keep custom implementation lightweight**:
- Store schemas in database table (version, event_type, schema JSON)
- Implement core compatibility modes (BACKWARD, FORWARD, FULL)
- Focus on JSON Schema validation for CloudEvents payloads
- Skip features not needed: schema references, TRANSITIVE modes, subject hierarchies

**Integration with FastStream**:
```python
# 1. Schema registry validates against JSON Schema
schema_registry.validate_payload(event_type="user.created", version="2.0.0", payload=event.data)

# 2. FastStream Pydantic model provides type safety (optional)
@broker.subscriber("events")
async def handle(event: CloudEvent[UserCreatedData]) -> None:
    # Both validations passed: JSON Schema (schema registry) + Pydantic (FastStream)
    ...
```

**Testing strategy**:
- Unit tests: Schema registration, versioning, compatibility checking
- Integration tests: Validate against real JSON Schemas
- Property-based tests: Schema evolution scenarios (add field, remove field, change type)

## Migration Path (if needed later)

**Step 1**: Extract schema registry interface
```python
class ISchemaRegistry(ABC):
    @abstractmethod
    def register_schema(...) -> None: ...
    @abstractmethod
    def validate_payload(...) -> None: ...
```

**Step 2**: Implement Confluent adapter
```python
class ConfluentSchemaRegistry(ISchemaRegistry):
    def __init__(self, schema_registry_client: SchemaRegistryClient): ...
    def register_schema(...) -> None:
        # Delegate to Confluent Schema Registry REST API
        ...
```

**Step 3**: Swap implementation via dependency injection
```python
# Old: schema_registry = CustomSchemaRegistry()
# New: schema_registry = ConfluentSchemaRegistry(client)
```

No changes to consumer code.
