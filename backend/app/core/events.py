from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.application.ports import EventPublisherPort
from app.core.config import settings
from app.core.observability import get_request_id
from app.core.tracing import inject_trace_context


class CleanupEventType:
    FILE_DELETE_REQUESTED = "file.delete_requested"
    FOLDER_DELETE_REQUESTED = "folder.delete_requested"
    UPLOAD_FAILED = "upload.failed"
    ACCOUNT_DELETE_REQUESTED = "account.delete_requested"


@dataclass
class PublishedEvent:
    topic: str
    key: str
    payload: dict[str, Any]


@dataclass
class InMemoryEventPublisher(EventPublisherPort):
    events: list[PublishedEvent] = field(default_factory=list)

    def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        self.events.append(PublishedEvent(topic=topic, key=key, payload=payload))


class NoopEventPublisher(EventPublisherPort):
    def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        return None


class KafkaEventPublisher(EventPublisherPort):
    def __init__(self) -> None:
        from kafka import KafkaProducer

        self.producer = KafkaProducer(
            bootstrap_servers=settings.kafka_broker,
            client_id=settings.kafka_client_id,
            key_serializer=lambda value: value.encode("utf-8"),
            value_serializer=lambda value: json.dumps(value, default=str).encode("utf-8"),
        )

    def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None:
        self.producer.send(topic, key=key, value=payload).get(timeout=10)


def build_cleanup_event(
    event_type: str,
    *,
    resource: dict[str, str] | None = None,
    objects: list[dict[str, str]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event_metadata = inject_trace_context(metadata)
    correlation_id = get_request_id()
    if correlation_id and "correlation_id" not in event_metadata:
        event_metadata["correlation_id"] = correlation_id
    return {
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "resource": resource or {},
        "objects": objects or [],
        "metadata": event_metadata,
        "delivery": {
            "attempt": 0,
            "max_retries": settings.kafka_cleanup_max_retries,
            "scheduled_at": datetime.now(UTC).isoformat(),
        },
    }
