# Feature 10: Contract Testing - All Sources Summary

## Feature Requirement
Event version compatibility validation across consumers (prevent breaking changes)

## Kafka Plugins

### Confluent Schema Registry Compatibility Modes
- ✅ **Full support**: Confluent Schema Registry provides compatibility checking
  - **BACKWARD**: New schema can read old data
  - **FORWARD**: Old schema can read new data
  - **FULL**: Both BACKWARD and FORWARD
  - **TRANSITIVE**: Checks compatibility across all versions, not just adjacent
- ✅ **REST API**: Check compatibility before registering new schema
  ```bash
  POST /compatibility/subjects/{subject}/versions/{version}
  {
    "schema": "{...new schema...}"
  }
  # Returns: {"is_compatible": true/false}
  ```
- ✅ **Automatic enforcement**: Registry rejects incompatible schemas

### Example Workflow
```python
# Check if new schema version is compatible
response = schema_registry_client.test_compatibility(
    subject="user-created-value",
    schema=new_schema,
    version="latest"
)

if not response["is_compatible"]:
    raise ValueError(f"Schema incompatible: {response['messages']}")
```

### Verdict: **FULLY COVERED** by Confluent Schema Registry

### But Wait...

**IF we use Confluent Schema Registry** (see Feature 1), then Feature 10 is **covered**.

**IF we use custom schema registry** (current plan), then Feature 10 needs **custom implementation**.

## Apicurio Registry

### Similar Support
- ✅ Compatibility modes (same as Confluent)
- ✅ REST API for compatibility checking
- ✅ Automatic enforcement

### Verdict: **FULLY COVERED** by Apicurio Registry (same caveat as Confluent)

## RabbitMQ

### No Schema Registry
- ❌ RabbitMQ has no schema registry
- ❌ No compatibility checking
- ❌ Not applicable

### Verdict: **NOT APPLICABLE**

## FastStream

### Pydantic Validation
- ✅ **Runtime validation**: Pydantic validates message against model
  ```python
  class UserV1(BaseModel):
      name: str
      age: int
  
  class UserV2(BaseModel):
      name: str
      age: int
      email: str = ""  # New optional field (backward compatible)
  ```
- ❌ **No version tracking**: FastStream doesn't track schema versions
- ❌ **No compatibility modes**: No BACKWARD/FORWARD/FULL checking
- ❌ **No cross-handler coordination**: Each handler has its own model

### Verdict: **Runtime validation only, NO compatibility checking**

## Our Decision (Depends on Feature 1)

### Scenario A: Use External Schema Registry (SIMPLIFY Feature 1)

**IF** we adopt Confluent or Apicurio Schema Registry:
- ✅ Feature 10 is **COVERED** by registry's compatibility checking
- ✅ Just use registry's REST API or client libraries
- ❌ No custom implementation needed

**Decision**: **DROP Feature 10** - Rely on Schema Registry compatibility

### Scenario B: Custom Schema Registry (KEEP Feature 1)

**IF** we implement custom schema registry (current plan):
- ❌ Feature 10 is **NOT COVERED** by any library
- ✅ Must implement custom compatibility checking

**Decision**: **KEEP Feature 10** - Implement custom compatibility validation

## Current Plan: Custom Schema Registry → KEEP Feature 10

### Why KEEP (Given Custom Schema Registry)
1. **Prevent breaking changes**: Ensure new schema versions don't break existing consumers
2. **CloudEvents-specific**: Check compatibility of CloudEvents data payloads
3. **Integration with custom registry**: Use our schema registry as source of truth

### Implementation Approach

**Compatibility checking logic**:
```python
class CompatibilityMode(Enum):
    BACKWARD = "backward"  # New schema reads old data
    FORWARD = "forward"    # Old schema reads new data
    FULL = "full"          # Both directions
    NONE = "none"          # No checking

class SchemaCompatibilityChecker:
    def check_backward_compatible(self, old_schema: dict, new_schema: dict) -> bool:
        # New schema can read old data
        # Rules: Can add optional fields, cannot remove required fields
        ...
    
    def check_forward_compatible(self, old_schema: dict, new_schema: dict) -> bool:
        # Old schema can read new data
        # Rules: Can remove optional fields, cannot add required fields
        ...
    
    def check_compatibility(
        self, old_schema: dict, new_schema: dict, mode: CompatibilityMode
    ) -> tuple[bool, list[str]]:
        # Returns (is_compatible, error_messages)
        ...
```

**Integration with schema registry**:
```python
class SchemaRegistry:
    def register_schema(
        self, event_type: str, version: str, schema: dict, mode: CompatibilityMode
    ) -> None:
        # Get latest schema
        latest = self.get_schema(event_type, "latest")
        
        # Check compatibility
        is_compatible, errors = self.compatibility_checker.check_compatibility(
            latest, schema, mode
        )
        
        if not is_compatible:
            raise SchemaIncompatibleError(
                f"Schema incompatible with mode {mode}: {errors}"
            )
        
        # Store new version
        self._store_schema(event_type, version, schema)
```

### Contract Testing Strategy

**Test compatibility rules**:
```python
def test_backward_compatible_add_optional_field():
    old_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    }
    new_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"}  # New optional field
        },
        "required": ["name"]
    }
    assert checker.check_backward_compatible(old_schema, new_schema) == True

def test_backward_incompatible_remove_required_field():
    old_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"]
    }
    new_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]  # Removed required field
    }
    assert checker.check_backward_compatible(old_schema, new_schema) == False
```

### Property-Based Testing
```python
from hypothesis import given, strategies as st

@given(
    old_schema=st.json_schemas(),
    new_schema=st.json_schemas()
)
def test_compatibility_is_transitive(old_schema, new_schema):
    # If A→B and B→C are backward compatible, then A→C should be too
    ...
```

## Comparison to Confluent Schema Registry

| Feature | Confluent Registry | Our Implementation | Winner |
|---------|------------------|------------------|--------|
| Compatibility modes | ✅ All modes | ✅ Implement BACKWARD/FORWARD/FULL | Tie |
| REST API | ✅ Built-in | ✅ Custom endpoints | Tie |
| Battle-tested | ✅ Very mature | ❌ New implementation | ❌ Confluent |
| CloudEvents integration | ⚠️ Generic | ✅ Specific to our use case | ✅ Ours |
| External infrastructure | ❌ Required | ✅ Embedded | ✅ Ours |
| JSON Schema focus | ✅ Yes (+ Avro, Protobuf) | ✅ Yes (JSON Schema only) | Tie |

## Final Decision: **KEEP (If keeping Feature 1 custom registry)**

### Decision Tree

```
Is Feature 1 using external Schema Registry?
├─ Yes (Confluent/Apicurio) → DROP Feature 10 (covered by registry)
└─ No (Custom registry) → KEEP Feature 10 (implement compatibility checking)
```

### Current Plan: **KEEP** (Custom registry → custom compatibility)

**Rationale**:
1. Feature 1 decision: KEEP custom schema registry
2. Therefore: Need custom compatibility checking
3. Implementation: Core compatibility rules + schema registry integration
4. Testing: Unit tests + property-based tests for edge cases

### Scope (Lightweight)
- ✅ Implement BACKWARD, FORWARD, FULL modes
- ✅ JSON Schema compatibility rules
- ❌ Skip TRANSITIVE modes (check only adjacent versions, not all history)
- ❌ Skip complex features (schema references, nested compatibility)

### Future Migration
If we later migrate to Confluent/Apicurio Schema Registry:
1. Remove `SchemaCompatibilityChecker` class
2. Use registry's compatibility API instead
3. No changes to consumer code (compatibility is enforced at registration time)

## Conclusion

**KEEP** - Feature 10 depends on Feature 1 decision. Since we're keeping custom schema registry, we need custom compatibility checking to prevent breaking changes across event versions.

**Implementation approach**: Lightweight compatibility checker with core rules (add optional field, remove optional field, change type) for BACKWARD/FORWARD/FULL modes.
