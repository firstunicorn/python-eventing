"""Message verification helpers for restart test."""

import asyncio

from confluent_kafka import Consumer, KafkaException, Producer


async def produce_and_verify_message_after_restart(
    producer: Producer,
    consumer: Consumer,
    topic: str,
) -> None:
    """Produce a message and verify it's consumed after Kafka restart.

    Args:
        producer: Kafka producer instance
        consumer: Kafka consumer instance
        topic: Topic to use

    Raises:
        AssertionError: If message not received
    """
    await asyncio.sleep(10)

    producer.produce(topic, value=b"recovered")
    producer.flush(timeout=60)

    start_time = asyncio.get_event_loop().time()
    message_received = False

    while (asyncio.get_event_loop().time() - start_time) < 60:
        msg = consumer.poll(timeout=2.0)
        if msg is None:
            await asyncio.sleep(0.5)
            continue
        if msg.error():
            raise KafkaException(msg.error())

        assert msg.value() == b"recovered"
        message_received = True
        break

    assert message_received, "Message not received after Kafka restart"
