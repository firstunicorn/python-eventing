"""Build RabbitMQ routing keys from event data."""


def build_routing_key(template: str, event: dict[str, str]) -> str:
    """Build RabbitMQ routing key from event data using template.

    Args:
        template: Routing key template with placeholders (e.g., "{event_type}")
        event: Event dictionary with fields to substitute

    Returns:
        Formatted routing key with dots replacing underscores in field names

    Example:
        >>> build_routing_key("{event_type}", {"event_type": "user.created"})
        'user.created'
    """
    # Replace dots with underscores in keys for safe formatting
    safe_event = {k.replace(".", "_"): v for k, v in event.items()}
    return template.format(**safe_event)
