# Python mock decorator parameter ordering bug

**[Bug](#bug)** • **[Root cause](#root-cause)** • **[Fix](#fix)** • **[Prevention](#prevention)**

## Bug

Unit tests in `tests/unit/test_initialization_unit.py` failed with assertion errors:

```python
AssertionError: assert <KafkaBroker object> is <Mock name='create_kafka_broker()'>
AssertionError: Expected 'create_rabbit_broker' to have been called once. Called 0 times.
AttributeError: 'NoneType' object has no attribute 'kwargs'
```

## Root cause

Python `@patch` decorators apply bottom-to-top but parameters received top-to-bottom.

**Wrong code** (lines 47-50, 65-68, 90-93):
```python
@patch("messaging.infrastructure.pubsub.rabbit_broker_config.create_rabbit_broker")  # 2nd
@patch("messaging.infrastructure.create_kafka_broker")  # 1st
def test_passes_settings_to_kafka_broker(
    self, mock_create_rabbit, mock_create_kafka  # WRONG ORDER
) -> None:
```

**What happened**:
1. `@patch` for `create_kafka_broker` applied first (bottom decorator)
2. `@patch` for `create_rabbit_broker` applied second (top decorator)
3. Parameters received in application order: (self, kafka_mock, rabbit_mock)
4. But parameter names were: (self, mock_create_rabbit, mock_create_kafka)
5. Variable names swapped: `mock_create_kafka` held rabbit mock, vice versa

## Fix

Swap parameter names to match decorator application order:

```python
@patch("messaging.infrastructure.pubsub.rabbit_broker_config.create_rabbit_broker")
@patch("messaging.infrastructure.create_kafka_broker")
def test_passes_settings_to_kafka_broker(
    self, mock_create_kafka, mock_create_rabbit  # CORRECT ORDER
) -> None:
```

**Fixed locations**:
- Line 50: `test_passes_settings_to_kafka_broker`
- Line 68: `test_passes_rate_limiter_settings`  
- Line 93: `test_rabbit_publisher_uses_correct_exchange`

## Prevention

**Rule**: Parameter names must match decorator application order (bottom-to-top).

**Pattern**:
```python
@patch("path.to.second_function")  # 2nd decorator
@patch("path.to.first_function")   # 1st decorator  
def test_something(
    self,
    mock_first,   # Matches 1st decorator
    mock_second   # Matches 2nd decorator
):
    pass
```

**Verification**:
```python
# Always verify mocks were called
mock_first.assert_called_once()
assert mock_first.call_args is not None  # Catches wrong parameter

# Check return values are used correctly
result = function_under_test()
assert result is mock_first.return_value  # Not mock_second
```

## Lessons learned

1. **Visual alignment misleading**: Reading decorators top-to-bottom does NOT match parameter order
2. **Test failures cryptic**: "NoneType has no attribute" means mock wasn't set up (wrong variable)
3. **Always verify explicitly**: Add assertions that mocks were called, not just return values
4. **Naming convention helps**: Use descriptive names that can't be easily confused (e.g., `mock_kafka_broker`, `mock_rabbit_broker`)

## Related issues

- 6 unit tests failed initially
- All fixed by correcting parameter order to match decorator application order
- No code changes needed to production code
