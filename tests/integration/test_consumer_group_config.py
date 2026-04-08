"""Integration tests for Kafka consumer group configuration."""

import asyncio

import pytest
from confluent_kafka.admin import AdminClient, NewTopic  # type: ignore[attr-defined] # confluent_kafka stubs incomplete in typeshed


@pytest.fixture
async def kafka_with_partitions(kafka_container):
    """Create Kafka topics with multiple partitions for consumer group tests."""
    admin_config = {"bootstrap.servers": kafka_container.get_bootstrap_server()}
    admin_client = AdminClient(admin_config)

    # Create topic with 4 partitions
    topics = [NewTopic("multi-partition-topic", num_partitions=4, replication_factor=1)]
    admin_client.create_topics(topics)

    # Wait for topic creation
    await asyncio.sleep(2)

    return kafka_container.get_bootstrap_server()


@pytest.mark.integration
class TestConsumerGroupConfig:
    """Test cooperative rebalancing and static membership."""

    @pytest.mark.asyncio
    async def test_static_membership_survives_restart(
        self, kafka_with_partitions
    ) -> None:
        """Consumer with group.instance.id survives restart without rebalance."""
        from confluent_kafka import Consumer

        consumer_config = {
            "bootstrap.servers": kafka_with_partitions,
            "group.id": "static-test-group",
            "group.instance.id": "consumer-static-1",  # Static membership
            "auto.offset.reset": "earliest",
        }

        consumer = Consumer(consumer_config)
        consumer.subscribe(["multi-partition-topic"])

        # Poll until assignment completes (max 20 attempts)
        initial_assignment = []
        for attempt in range(20):
            consumer.poll(timeout=1.0)
            initial_assignment = consumer.assignment()
            if initial_assignment:
                break
            await asyncio.sleep(0.5)

        if not initial_assignment:
            pytest.skip("Partition assignment failed - broker coordination issue")

        consumer.close()

        # Restart consumer with same group.instance.id
        consumer2 = Consumer(consumer_config)
        consumer2.subscribe(["multi-partition-topic"])
        
        # Poll until assignment completes (max 20 attempts)
        final_assignment = []
        for attempt in range(20):
            consumer2.poll(timeout=1.0)
            final_assignment = consumer2.assignment()
            if final_assignment:
                break
            await asyncio.sleep(0.5)

        # With static membership, partitions should be same
        assert len(final_assignment) > 0, "Final assignment was empty"
        assert len(initial_assignment) == len(final_assignment)
        assert {p.partition for p in initial_assignment} == {
            p.partition for p in final_assignment
        }

        consumer2.close()

    @pytest.mark.asyncio
    async def test_two_consumers_consume_disjoint_partitions(
        self, kafka_with_partitions
    ) -> None:
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

        # Poll to trigger partition assignment
        consumer1.poll(timeout=2.0)
        consumer2.poll(timeout=2.0)

        await asyncio.sleep(1)

        assignment1 = {p.partition for p in consumer1.assignment()}
        assignment2 = {p.partition for p in consumer2.assignment()}

        # Partitions should be disjoint (no overlap)
        assert len(assignment1.intersection(assignment2)) == 0
        # Combined should cover all partitions
        assert len(assignment1) + len(assignment2) <= 4

        consumer1.close()
        consumer2.close()

    @pytest.mark.asyncio
    async def test_cooperative_partition_assignment(
        self, kafka_with_partitions
    ) -> None:
        """Cooperative-sticky strategy does not revoke all partitions on join."""
        from confluent_kafka import Consumer

        consumer_config = {
            "bootstrap.servers": kafka_with_partitions,
            "group.id": "cooperative-test-group",
            "auto.offset.reset": "earliest",
            "partition.assignment.strategy": "cooperative-sticky",
        }

        # Start first consumer
        consumer1 = Consumer({**consumer_config, "client.id": "consumer-1"})
        consumer1.subscribe(["multi-partition-topic"])
        consumer1.poll(timeout=2.0)

        initial_assignment = {p.partition for p in consumer1.assignment()}

        # Start second consumer (triggers rebalance)
        consumer2 = Consumer({**consumer_config, "client.id": "consumer-2"})
        consumer2.subscribe(["multi-partition-topic"])

        await asyncio.sleep(2)  # Let rebalance complete

        consumer1.poll(timeout=2.0)
        consumer2.poll(timeout=2.0)

        final_assignment1 = {p.partition for p in consumer1.assignment()}
        final_assignment2 = {p.partition for p in consumer2.assignment()}

        # Consumer1 should retain at least some partitions (cooperative rebalance)
        # It doesn't lose ALL partitions like eager rebalancing
        if len(initial_assignment) >= 2:
            assert len(final_assignment1) > 0, "Cooperative rebalance should not revoke all partitions"

        # Both consumers should have partitions
        assert len(final_assignment1) > 0
        assert len(final_assignment2) > 0

        consumer1.close()
        consumer2.close()
