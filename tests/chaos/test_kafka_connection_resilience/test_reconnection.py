"""Test publisher works after Kafka container restart."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from confluent_kafka import Consumer, Producer, KafkaException
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(600)
@pytest.mark.chaos
async def test_publisher_works_after_kafka_restart(
    docker_or_skip: None,
) -> None:
    """Test that producer/consumer work after Kafka restart (chaos resilience)."""
    del docker_or_skip
    
    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    kafka.start(timeout=300)
    
    bootstrap1 = kafka.get_bootstrap_server()
    topic = f"pub-recon-{uuid4()}"
    
    consumer = Consumer({
        'bootstrap.servers': bootstrap1,
        'group.id': f"c-pub-recon-{uuid4()}",
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    })
    consumer.subscribe([topic])
    
    # Stop Kafka
    kafka.stop()
    await asyncio.sleep(5)
    
    # Restart Kafka
    kafka.start(timeout=300)
    await asyncio.sleep(10)  # Extra stabilization time
    
    consumer.close()
    
    # Create new consumer and producer with restarted Kafka
    bootstrap2 = kafka.get_bootstrap_server()
    
    consumer2 = Consumer({
        'bootstrap.servers': bootstrap2,
        'group.id': f"c-pub-recon2-{uuid4()}",
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
    })
    consumer2.subscribe([topic])
    
    producer = Producer({
        'bootstrap.servers': bootstrap2,
        'client.id': 'chaos-test-producer',
    })
    
    try:
        # Produce message
        producer.produce(topic, value=b"recovered")
        producer.flush(timeout=30)
        
        # Consume message with timeout
        start_time = asyncio.get_event_loop().time()
        message_received = False
        
        while (asyncio.get_event_loop().time() - start_time) < 30:
            msg = consumer2.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            if msg.error():
                raise KafkaException(msg.error())
            
            assert msg.value() == b"recovered"
            message_received = True
            break
        
        assert message_received, "Message not received after Kafka restart"
        
    finally:
        consumer2.close()
        kafka.stop()

