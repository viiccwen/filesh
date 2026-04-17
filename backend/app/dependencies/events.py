from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.events import EventPublisher, KafkaEventPublisher, NoopEventPublisher


@lru_cache(maxsize=1)
def _build_event_publisher() -> EventPublisher:
    if settings.kafka_publisher_enabled:
        return KafkaEventPublisher()
    return NoopEventPublisher()


def get_event_publisher() -> EventPublisher:
    return _build_event_publisher()
