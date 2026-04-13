"""Message consumption and verification helpers."""

import asyncio

from confluent_kafka import Consumer, Producer


async def produce_test_messages(producer: Producer, topic: str, count: int) -> None:
    """Produce a batch of test messages to Kafka.

    Args:
        producer: Kafka producer instance
        topic: Target topic
        count: Number of messages to produce
    """
    for i in range(count):
        producer.produce(topic, value=f"evt-{i}".encode(), key=f"key-{i % 2}".encode())
    producer.flush(timeout=10)

    await asyncio.sleep(10)


async def consume_and_collect_messages(
    consumer1: Consumer,
    consumer2: Consumer,
    max_polls: int = 60,
) -> tuple[set[str], set[str]]:
    """Poll both consumers and collect received messages.

    Args:
        consumer1: First consumer instance
        consumer2: Second consumer instance
        max_polls: Maximum number of poll attempts

    Returns:
        Tuple of (messages_seen_by_consumer1, messages_seen_by_consumer2)
    """
    seen1: set[str] = set()
    seen2: set[str] = set()

    for _poll_attempt in range(max_polls):
        msg1 = consumer1.poll(timeout=0.5)
        if msg1 is not None and not msg1.error():
            value = msg1.value()
            if value is not None:
                seen1.add(value.decode())

        msg2 = consumer2.poll(timeout=0.5)
        if msg2 is not None and not msg2.error():
            value = msg2.value()
            if value is not None:
                seen2.add(value.decode())

        if len(seen1) + len(seen2) >= 20:
            break

    return seen1, seen2


def verify_distribution(seen1: set[str], seen2: set[str], expected_min: int = 19) -> None:
    """Verify message distribution across consumers.

    Args:
        seen1: Messages seen by consumer 1
        seen2: Messages seen by consumer 2
        expected_min: Minimum expected total messages

    Raises:
        AssertionError: If distribution requirements not met
    """
    total = len(seen1) + len(seen2)
    assert (
        total >= expected_min
    ), f"Expected at least {expected_min} messages, got {total} (c1={len(seen1)}, c2={len(seen2)})"
    assert not (seen1 & seen2), f"Same-group consumers got {len(seen1 & seen2)} duplicates"
