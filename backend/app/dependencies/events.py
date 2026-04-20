from __future__ import annotations

from functools import lru_cache

from app.application.ports import EventPublisherPort
from app.core.config import settings
from app.core.events import KafkaEventPublisher, NoopEventPublisher


@lru_cache(maxsize=1)
def _build_event_publisher() -> EventPublisherPort:
    if settings.kafka_publisher_enabled:
        return KafkaEventPublisher()
    return NoopEventPublisher()


def get_event_publisher() -> EventPublisherPort:
    return _build_event_publisher()
