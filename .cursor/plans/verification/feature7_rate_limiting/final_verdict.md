# Feature 7: Rate Limiting - All Sources Summary

## Feature Requirement
Consume-side rate limiting via aiolimiter middleware to prevent flooding Kafka/RabbitMQ

## Kafka Native

### Broker-side Quotas (Producer/Consumer)
- ✅ **Kafka quotas**: Broker can enforce rate limits per client/user/IP
  - Producer quotas: Limit bytes/sec written
  - Consumer quotas: Limit bytes/sec read
  - Request quotas: Limit requests/sec
- ✅ Configuration: `quota.producer.default`, `quota.consumer.default`
- ⚠️ **Broker-side only**: Enforced by Kafka broker, not client-side control
- ⚠️ **Coarse-grained**: Per-client limits, not per-handler/per-topic

### Verdict: **Partial coverage** - Broker quotas exist but NOT client-side rate limiting

## Kafka Plugins

### Kafka Streams
- ❌ No built-in rate limiting
- ❌ No backpressure control beyond consumer polling
- ⚠️ Developers implement custom rate limiting with external libraries

### Verdict: **NOT COVERED**

## RabbitMQ Native

### QoS Prefetch
- ✅ **prefetch_count**: Limit unacked messages per consumer
  ```python
  channel.basic_qos(prefetch_count=10)  # Max 10 unacked messages
  ```
- ✅ **Natural backpressure**: Consumer won't receive more until it acks
- ⚠️ **NOT rate limiting**: Controls concurrency, not rate (messages/sec)
- ⚠️ **Pull-based backpressure**: Different from time-based rate limiting

### Flow Control
- ✅ **Flow control**: RabbitMQ can block publishers when memory/disk pressure
- ⚠️ **Automatic**: Cannot be manually configured per-consumer

### Verdict: **Different mechanism** - QoS provides backpressure but NOT rate limiting

## RabbitMQ Plugins

### Rate Limiting Plugins
- ❌ No official rate limiting plugin for consumers
- ⚠️ **rabbitmq_sharding**: Can distribute load but not rate limit
- ⚠️ Community plugins exist but not officially supported

### Verdict: **NOT COVERED**

## FastStream

### Middleware Pattern
- ✅ **BaseMiddleware** with `consume_scope`: Correct hook for rate limiting
- ❌ No built-in **RateLimiterMiddleware**
- ❌ No rate limiting utilities in FastStream

### Example Pattern (hypothetical)
```python
class RateLimiterMiddleware(BaseMiddleware):
    async def consume_scope(self, call_next, msg: StreamMessage):
        await self._limiter.acquire()  # Wait for rate limiter
        return await call_next(msg)
```

### Verdict: **PATTERN CONFIRMED, IMPLEMENTATION NEEDED**

## Python Ecosystem: aiolimiter

### Library Available
- ✅ **aiolimiter**: Mature async rate limiting library
  ```python
  from aiolimiter import AsyncLimiter
  limiter = AsyncLimiter(max_rate=1000, time_period=60.0)  # 1000/min
  async with limiter:
      await process_message()
  ```
- ✅ **Token bucket algorithm**: Smooth rate limiting with bursts
- ✅ **Async/await**: Works with FastStream async handlers
- ✅ **Lightweight**: No external dependencies

### Verdict: **LIBRARY EXISTS** - aiolimiter is the standard Python solution

## Final Decision: **KEEP with aiolimiter (Already Planned)**

### Why KEEP
1. **Client-side control**: We want to control rate in our application
2. **Per-broker limits**: Different limits for Kafka vs RabbitMQ paths
3. **Application logic**: Rate limiting based on message processing, not just throughput

### Why NOT Kafka Quotas
- Kafka quotas are **broker-side**: Admin must configure
- We want **application-controlled** rate limiting
- Different rate limits for different message types (not supported by Kafka quotas)

### Why NOT RabbitMQ QoS
- QoS controls **concurrency** (max unacked messages)
- Rate limiting controls **throughput** (messages per second)
- Different concerns

### Implementation (Confirmed Correct)

**Our plan** already uses aiolimiter + FastStream middleware:

```python
from aiolimiter import AsyncLimiter
from faststream import BaseMiddleware

class RateLimiterMiddleware(BaseMiddleware):
    def __init__(self, max_rate: int, time_period: float = 1.0):
        self._limiter = AsyncLimiter(max_rate, time_period)
    
    async def consume_scope(self, call_next, msg: StreamMessage):
        async with self._limiter:  # Wait for token
            return await call_next(msg)

# Wire to brokers
kafka_broker = KafkaBroker(..., middlewares=[
    RateLimiterMiddleware(max_rate=1000, time_period=60.0)
])

rabbit_broker = RabbitBroker(..., middlewares=[
    RateLimiterMiddleware(max_rate=500, time_period=60.0)
])
```

### Comparison to Alternatives

**vs. Kafka Quotas**:
- Kafka quotas: Broker-admin configured, coarse-grained
- Our solution: Application-controlled, fine-grained

**vs. RabbitMQ QoS**:
- RabbitMQ QoS: Concurrency control (max N unacked)
- Our solution: Rate control (max N per minute)

**vs. Manual `asyncio.sleep()`**:
- Manual sleep: Inefficient, poor distribution
- aiolimiter: Token bucket, smooth rate, burst handling

### What We're Using (Not Duplicating)
- ✅ **aiolimiter library**: Standard Python async rate limiting
- ✅ **FastStream BaseMiddleware**: Framework integration point
- ✅ **NOT re-implementing**: Token bucket algorithm (aiolimiter provides this)

### Test Strategy
```python
# Unit test
async def test_rate_limiter_respects_limit():
    limiter = AsyncLimiter(max_rate=10, time_period=1.0)
    # Send 15 messages
    # Verify 10 complete immediately, 5 wait ~1 second
    ...

# Integration test
async def test_rate_limiter_middleware():
    middleware = RateLimiterMiddleware(max_rate=10, time_period=1.0)
    # Simulate 15 messages
    # Verify middleware gates message processing
    ...
```

## Conclusion

**KEEP with aiolimiter** - Current plan already uses the correct approach:
1. aiolimiter for rate limiting logic (battle-tested library)
2. FastStream BaseMiddleware for integration (framework pattern)
3. Application-controlled rate limits (not broker quotas)

No further simplification needed.
