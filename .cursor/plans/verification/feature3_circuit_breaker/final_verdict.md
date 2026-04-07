# Feature 3: Circuit Breaker - All Sources Summary

## Kafka Native

### Findings
- ✅ **KIP-693**: Client-side circuit breaker for **partition write errors** only
  - Mutes problematic TopicPartitions (disk issues, high latency)
  - Config: `enable.mute.partition`
  - Scope: **Producer-only**, **partition-level**, not general broker failure
- ✅ Resiliency configs: replication factor, acks, min.in.sync.replicas
- ✅ Graceful shutdown: `controlled.shutdown.enable=true`
- ✅ Exactly-once semantics for fault tolerance

### Verdict: **NOT COVERED** for general circuit breaker
- KIP-693 is too specific (partition errors only, not broker-level failures)
- No CLOSED/OPEN/HALF_OPEN state machine for general use
- No consumer-side circuit breaker

## Kafka Plugins

### Findings
- ❌ Kafka Connect: No built-in circuit breaker
- ❌ Kafka Streams: Resiliency configs but no circuit breaker pattern
- ⚠️ **Application-level**: Developers use **Resilience4j** library (not Kafka plugin)

### Verdict: **NOT COVERED** by Kafka ecosystem
- Resilience4j is external library (Java), not Kafka-specific
- Kafka plugins provide retry/backoff but not circuit breaker state machine

## RabbitMQ Native

### Quick check via web search
- ✅ RabbitMQ has **automatic connection recovery** and **health checks**
- ✅ Client libraries reconnect automatically on connection failure
- ❌ No circuit breaker pattern (CLOSED/OPEN/HALF_OPEN states)
- ❌ No failure threshold or reset timeout configuration

### Verdict: **NOT COVERED**
- Connection recovery ≠ circuit breaker
- No protection against repeated failed calls

## RabbitMQ Plugins

### Quick check
- ❌ No official plugins for circuit breaker pattern
- rabbitmq_shovel: Retry/backoff for message transfer, not circuit breaker
- rabbitmq_federation: For multi-cluster routing, not resilience pattern

### Verdict: **NOT COVERED**

## FastStream

### Findings from Context7
- ✅ **BaseMiddleware** pattern: Correct mechanism for implementing circuit breaker
- ✅ FastStream docs mention **RetryMiddleware** pattern with exponential backoff
- ❌ No built-in **CircuitBreaker** middleware
- ❌ No circuit breaker examples in documentation

### Pattern confirmed
```python
# FastStream RetryMiddleware pattern (from docs)
class RetryMiddleware(BaseMiddleware):
    async def consume_scope(self, call_next, msg):
        for attempt in range(max_retries):
            try:
                return await call_next(msg)
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff)
                else:
                    raise
```

### Verdict: **PATTERN CONFIRMED, IMPLEMENTATION NEEDED**
- ✅ FastStream BaseMiddleware is the RIGHT pattern
- ❌ No built-in CircuitBreaker middleware
- ✅ Our custom implementation fits FastStream conventions

## Consolidated Verdict

| Source | Circuit Breaker Support | Notes |
|--------|------------------------|-------|
| Kafka native | ⚠️ Partial (KIP-693 partition-only) | Too specific |
| Kafka plugins | ❌ No | Use external Resilience4j |
| RabbitMQ native | ❌ No | Auto-reconnect only |
| RabbitMQ plugins | ❌ No | No official plugins |
| FastStream | ⚠️ Pattern only | BaseMiddleware confirmed |

## Final Decision: **KEEP CUSTOM IMPLEMENTATION**

### Why Keep
1. **No library provides CLOSED/OPEN/HALF_OPEN state machine** for FastStream
2. **Kafka KIP-693** is partition-specific, not broker-level failure handling
3. **Resilience4j** is Java-only (we're using Python/FastStream)
4. **FastStream BaseMiddleware** is the correct integration pattern - our plan already uses this

### Implementation Approach (Confirmed Correct)

**Our plan** (from main plan document):
```python
class CircuitBreakerMiddleware(BaseMiddleware):
    def __init__(self, failure_threshold: int, reset_timeout: float):
        self._breaker = CircuitBreaker(failure_threshold, reset_timeout)
    
    async def consume_scope(self, call_next, msg: StreamMessage):
        try:
            result = await self._breaker.call(call_next, msg)
            await self._breaker.record_success()
            return result
        except Exception:
            await self._breaker.record_failure()
            raise
```

**This is CORRECT** and follows FastStream conventions.

### What We're Not Duplicating
- ❌ NOT re-implementing Kafka partition-level circuit breaker (KIP-693)
- ❌ NOT re-implementing RabbitMQ auto-reconnect
- ✅ **Implementing** application-level circuit breaker for **broker failures** (both Kafka and RabbitMQ)

### Comparison to Alternatives

**vs. Resilience4j** (Java):
- Resilience4j is for Java/Spring applications
- We're using Python/FastStream
- No Python equivalent with FastStream integration

**vs. KIP-693** (Kafka partition circuit breaker):
- KIP-693: Mutes individual partitions on write errors
- Our circuit breaker: Stops ALL calls to broker when failure threshold reached
- Different scope and use case

### Test Strategy Confirmed
```python
# Unit tests
def test_circuit_opens_after_threshold(): ...
def test_circuit_half_opens_after_timeout(): ...
def test_circuit_closes_on_success(): ...

# Chaos tests
def test_circuit_opens_when_kafka_down(): ...
def test_circuit_recovers_when_kafka_back(): ...
```

## Conclusion

**KEEP** - No library/plugin provides general-purpose async circuit breaker for FastStream + Python. Our custom implementation using `BaseMiddleware` is the correct approach and follows framework conventions.
