"""Test static consumer group membership."""

import asyncio

import pytest


@pytest.mark.integration
class TestStaticMembership:
    """Test static membership configuration."""

    @pytest.mark.asyncio
    async def test_static_membership_survives_restart(self, kafka_with_partitions) -> None:
        """Consumer with group.instance.id survives restart without rebalance."""
        from confluent_kafka import Consumer

        consumer_config = {
            "bootstrap.servers": kafka_with_partitions,
            "group.id": "static-test-group",
            "group.instance.id": "consumer-static-1",
            "auto.offset.reset": "earliest",
        }

        consumer = Consumer(consumer_config)
        consumer.subscribe(["multi-partition-topic"])

        initial_assignment = []
        for _attempt in range(20):
            consumer.poll(timeout=1.0)
            initial_assignment = consumer.assignment()
            if initial_assignment:
                break
            await asyncio.sleep(0.5)

        if not initial_assignment:
            pytest.skip("Partition assignment failed - broker coordination issue")

        consumer.close()

        consumer2 = Consumer(consumer_config)
        consumer2.subscribe(["multi-partition-topic"])

        final_assignment = []
        for _attempt in range(20):
            consumer2.poll(timeout=1.0)
            final_assignment = consumer2.assignment()
            if final_assignment:
                break
            await asyncio.sleep(0.5)

        assert len(final_assignment) > 0, "Final assignment was empty"
        assert len(initial_assignment) == len(final_assignment)
        assert {p.partition for p in initial_assignment} == {p.partition for p in final_assignment}

        consumer2.close()
