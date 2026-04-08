"""Test same-group consumers distribute messages without duplicates."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from confluent_kafka import Consumer, Producer, KafkaException
from testcontainers.kafka import KafkaContainer


@pytest.mark.asyncio
@pytest.mark.timeout(1800)
@pytest.mark.integration
async def test_same_group_distributes_messages(
    docker_or_skip: None,
) -> None:
    """Test that same consumer group distributes messages without duplicates."""
    del docker_or_skip
    
    # Add delay to prevent Docker daemon overload from previous test
    await asyncio.sleep(10)
    
    kafka = KafkaContainer("confluentinc/cp-kafka:7.6.1")
    
    try:
        kafka.start(timeout=300)
    except RuntimeError as e:
        if "exited" in str(e):
            pytest.skip(f"Docker resource exhaustion: {e}")
        raise
    
    bootstrap = kafka.get_bootstrap_server()
    topic = f"test-group-{uuid4()}"
    group = f"group-shared-{uuid4()}"
    
    # Create topic first by producing initial message
    producer_setup = Producer({
        'bootstrap.servers': bootstrap,
        'client.id': 'setup-producer',
    })
    producer_setup.produce(topic, value=b"setup")
    producer_setup.flush(timeout=10)
    
    # Wait for topic creation to propagate
    await asyncio.sleep(5)
    
    consumer1 = Consumer({
        'bootstrap.servers': bootstrap,
        'group.id': group,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True,
    })
    consumer1.subscribe([topic])
    
    consumer2 = Consumer({
        'bootstrap.servers': bootstrap,
        'group.id': group,
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True,
    })
    consumer2.subscribe([topic])
    
    await asyncio.sleep(5)  # Let consumers join group
    
    producer = Producer({
        'bootstrap.servers': bootstrap,
        'client.id': 'test-producer',
    })
    
    try:
        # Produce all 20 messages first (batched)
        for i in range(20):
            producer.produce(
                topic,
                value=f"evt-{i}".encode(),
                key=f"key-{i % 2}".encode()
            )
        producer.flush(timeout=10)
        
        # Give consumers time to process
        await asyncio.sleep(10)
        
        seen1: set[str] = set()
        seen2: set[str] = set()
        
        # Poll both consumers with reasonable timeout
        max_polls = 60  # 30 seconds total (60 × 0.5s)
        for poll_attempt in range(max_polls):
            # Poll consumer1
            msg1 = consumer1.poll(timeout=0.5)
            if msg1 is not None and not msg1.error():
                value = msg1.value()
                if value is not None:
                    seen1.add(value.decode())
            
            # Poll consumer2
            msg2 = consumer2.poll(timeout=0.5)
            if msg2 is not None and not msg2.error():
                value = msg2.value()
                if value is not None:
                    seen2.add(value.decode())
            
            # Break early if we got all messages (excluding setup message)
            if len(seen1) + len(seen2) >= 20:
                break
        
        total = len(seen1) + len(seen2)
        assert total >= 19, f"Expected at least 19 messages, got {total} (c1={len(seen1)}, c2={len(seen2)})"
        assert not (seen1 & seen2), f"Same-group consumers got {len(seen1 & seen2)} duplicates"
        
    finally:
        consumer1.close()
        consumer2.close()
        try:
            kafka.stop()
        except Exception:
            pass  # Container already removed
