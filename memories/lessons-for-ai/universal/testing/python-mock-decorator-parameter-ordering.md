# Python mock decorator parameter ordering

**[Rule](#rule)** • **[Example](#example)** • **[Prevention](#prevention)**

## Rule

Python `@patch` decorators apply bottom-to-top but function parameters received top-to-bottom.

**Required format**:
```python
@patch("module.second_function")  # Applied 2nd → param 2
@patch("module.first_function")   # Applied 1st → param 1
def test_something(
    self,
    mock_first,   # Matches 1st applied (bottom decorator)
    mock_second   # Matches 2nd applied (top decorator)
):
    pass
```

## Example

**Wrong** (causes test failures):
```python
@patch("infrastructure.create_rabbit_broker")  # 2nd
@patch("infrastructure.create_kafka_broker")   # 1st
def test_brokers(
    self, mock_rabbit, mock_kafka  # WRONG ORDER
) -> None:
    # mock_rabbit actually holds kafka mock
    # mock_kafka actually holds rabbit mock
    mock_kafka.assert_called_once()  # FAILS - wrong variable
```

**Correct**:
```python
@patch("infrastructure.create_rabbit_broker")  # 2nd
@patch("infrastructure.create_kafka_broker")   # 1st
def test_brokers(
    self, mock_kafka, mock_rabbit  # CORRECT ORDER
) -> None:
    # Variables match decorator application order
    mock_kafka.assert_called_once()  # Works correctly
```

## Prevention

**Visual pattern**: Read decorators bottom-to-top, write params top-to-bottom.

```python
@patch("path.to.third")   # 3rd ──┐
@patch("path.to.second")  # 2nd ──┤
@patch("path.to.first")   # 1st ──┤
def test(                 #       │
    self,                 #       │
    mock_first,    # ─────────────┘ (1st)
    mock_second,   # ─────────────┐ (2nd)
    mock_third     # ─────────────┘ (3rd)
):
```

**Always verify**:
```python
# After mocking, verify it was called
mock_first.assert_called_once()

# Check return value used correctly  
result = function_under_test()
assert result is mock_first.return_value
```

**Error symptoms**:
- `AttributeError: 'NoneType' object has no attribute 'kwargs'`
- `AssertionError: assert <RealObject> is <Mock>`
- `AssertionError: Expected X to be called once. Called 0 times.`

These indicate mock variables are swapped.
