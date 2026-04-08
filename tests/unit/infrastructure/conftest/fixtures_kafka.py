"""Kafka-specific test fixtures."""

from __future__ import annotations


class FakeKafkaBroker:
    """Broker fake that records publish arguments.

    Signature sourced from FastStream official documentation:
    https://faststream.ag2.ai/latest/api/faststream/kafka/broker/KafkaBroker/

    This fake is intentionally NOT copied from the real KafkaBroker import.
    Instead, it's implemented based on official docs, then validated against
    the real implementation by test_fake_broker_contract.py runtime inspection.

    This approach ensures:
    - We follow documented API (source of truth for users)
    - Contract test catches doc vs. implementation drift
    - No circular validation (fake copies real, test checks fake matches real)
    """

    def __init__(self) -> None:
        self.published: list[dict[str, object]] = []

    async def publish(
        self,
        message: dict[str, object],
        *,
        topic: str,
        key: bytes | None = None,
        partition: int | None = None,
        timestamp_ms: int | None = None,
        headers: dict[str, str] | None = None,
        correlation_id: str | None = None,
        reply_to: str = "",
        no_confirm: bool = False,
    ) -> None:
        """Record all publish calls with full parameter set.

        Parameters match FastStream KafkaBroker.publish() as documented at:
        https://faststream.ag2.ai/latest/api/faststream/kafka/broker/KafkaBroker/

        Note: We intentionally use dict[str, object] instead of SendableMessage
        for message parameter as it's more explicit for test purposes.
        """
        self.published.append({
            "message": message,
            "topic": topic,
            "key": key,
            "partition": partition,
            "timestamp_ms": timestamp_ms,
            "headers": headers,
            "correlation_id": correlation_id,
            "reply_to": reply_to,
            "no_confirm": no_confirm,
        })
