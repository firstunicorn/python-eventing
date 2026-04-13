"""Test disjoint partition consumption."""

import asyncio

import pytest


@pytest.mark.integration
class TestDisjointPartitions:
    """Test partition distribution across consumers."""

    @pytest.mark.asyncio
    async def test_two_consumers_consume_disjoint_partitions(self, kafka_with_partitions) -> None:
        """Two consumers with same group.id consume disjoint partition sets."""
        from confluent_kafka import Consumer

        consumer_config = {
            "bootstrap.servers": kafka_with_partitions,
            "group.id": "disjoint-test-group",
            "auto.offset.reset": "earliest",
            "partition.assignment.strategy": "cooperative-sticky",
        }

        consumer1 = Consumer({**consumer_config, "client.id": "consumer-1"})
        consumer2 = Consumer({**consumer_config, "client.id": "consumer-2"})

        consumer1.subscribe(["multi-partition-topic"])
        consumer2.subscribe(["multi-partition-topic"])

        consumer1.poll(timeout=2.0)
        consumer2.poll(timeout=2.0)

        await asyncio.sleep(1)

        assignment1 = {p.partition for p in consumer1.assignment()}
        assignment2 = {p.partition for p in consumer2.assignment()}

        assert len(assignment1.intersection(assignment2)) == 0
        assert len(assignment1) + len(assignment2) <= 4

        consumer1.close()
        consumer2.close()
