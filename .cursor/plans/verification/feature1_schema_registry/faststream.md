# Feature 1: Schema Registry - FastStream Check

## Query
FastStream Pydantic validation vs JSON Schema validation - does FastStream support JSON Schema registry, versioning, or compatibility modes?

## Context7 MCP Findings

**Source**: FastStream documentation (/airtai/faststream)

### What FastStream Provides

**✅ Pydantic-based validation**:
```python
class User(BaseModel):
    user: str = Field(..., examples=["John"])
    user_id: PositiveInt = Field(..., examples=["1"])

@broker.subscriber("in")
async def handle_msg(data: User) -> str:
    # FastStream automatically validates incoming messages
    # Raises pydantic.ValidationError if validation fails
    return f"User: {data.user} registered"
```

**Features**:
- ✅ Automatic message validation using Pydantic models
- ✅ Type safety and serialization/deserialization
- ✅ ValidationError with descriptive logs on schema mismatch
- ✅ Message filtering by headers or body type (consume different schemas from single stream)
- ✅ AsyncAPI 3.0 schema generation for documentation

### What FastStream Does NOT Provide

**❌ No Schema Registry**:
- No centralized schema storage
- No schema versioning system
- No schema lookup by ID or subject

**❌ No Compatibility Modes**:
- No BACKWARD/FORWARD/FULL compatibility checking
- No schema evolution management
- No transitive compatibility validation

**❌ No Event Type Registry**:
- No mapping of event types to schemas
- No version history tracking
- No schema compatibility enforcement across services

### How FastStream Handles Schemas

**Per-handler validation**:
- Each subscriber defines its own Pydantic model
- Validation is **local** to the handler
- No cross-handler schema coordination
- No versioning between handlers

**Example**:
```python
# Handler 1: Expects User v1 schema
@broker.subscriber("users")
async def handle_user_v1(data: UserV1) -> None: ...

# Handler 2: Expects User v2 schema
@broker.subscriber("users")
async def handle_user_v2(data: UserV2) -> None: ...

# FastStream does NOT coordinate or validate compatibility between UserV1 and UserV2
```

## Verdict

**NOT COVERED** - FastStream does not provide:
- ❌ JSON Schema registry (only Pydantic models)
- ❌ Schema versioning
- ❌ Compatibility mode checking
- ❌ Event type to schema mapping
- ❌ Centralized schema management

**What FastStream provides**:
- ✅ Per-message validation (Pydantic or Msgspec)
- ✅ Automatic serialization/deserialization
- ✅ AsyncAPI documentation generation (describes schemas, but doesn't manage them)

**Gap**:
FastStream validates **individual messages** against **individual Pydantic models**, but provides no mechanism for:
1. Storing schemas centrally
2. Versioning schemas over time
3. Checking compatibility between schema versions
4. Coordinating schemas across multiple services/handlers

## Impact on Feature 1

**FastStream is orthogonal to schema registry**:
- FastStream provides **runtime validation** (per-message type checking)
- Schema registry provides **schema management** (versioning, compatibility, coordination)

**Integration approach**:
1. **Schema registry**: Store JSON Schemas with version info
2. **Pydantic models**: Generate from JSON Schemas or validate against them
3. **FastStream**: Use Pydantic models for message validation
4. **Custom glue**: Map event types to schema versions in registry

**Example flow**:
```python
# 1. Schema registry lookup
schema = registry.get_schema(event_type="user.created", version="2.0.0")

# 2. Validate against JSON Schema
validator.validate(payload, schema)

# 3. FastStream Pydantic validation (optional type safety)
@broker.subscriber("users")
async def handle_user(data: UserV2Pydantic) -> None: ...
```

**Conclusion**: Custom schema registry implementation still needed. FastStream's Pydantic validation is complementary, not a replacement.
