"""Test cooperative partition assignment strategy."""

import asyncio

import pytest


@pytest.mark.integration
class TestCooperativeRebalance:
    """Test cooperative-sticky rebalancing behavior."""

    @pytest.mark.asyncio
    async def test_cooperative_partition_assignment(self, kafka_with_partitions) -> None:
        """Cooperative-sticky strategy does not revoke all partitions on join."""
        from confluent_kafka import Consumer

        consumer_config = {
            "bootstrap.servers": kafka_with_partitions,
            "group.id": "cooperative-test-group",
            "auto.offset.reset": "earliest",
            "partition.assignment.strategy": "cooperative-sticky",
        }

        consumer1 = Consumer({**consumer_config, "client.id": "consumer-1"})
        consumer1.subscribe(["multi-partition-topic"])
        consumer1.poll(timeout=2.0)

        initial_assignment = {p.partition for p in consumer1.assignment()}

        consumer2 = Consumer({**consumer_config, "client.id": "consumer-2"})
        consumer2.subscribe(["multi-partition-topic"])

        await asyncio.sleep(2)

        consumer1.poll(timeout=2.0)
        consumer2.poll(timeout=2.0)

        final_assignment1 = {p.partition for p in consumer1.assignment()}
        final_assignment2 = {p.partition for p in consumer2.assignment()}

        if len(initial_assignment) >= 2:
            assert (
                len(final_assignment1) > 0
            ), "Cooperative rebalance should not revoke all partitions"

        assert len(final_assignment1) > 0
        assert len(final_assignment2) > 0

        consumer1.close()
        consumer2.close()
