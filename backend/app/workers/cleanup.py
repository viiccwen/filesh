from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from app.core.config import settings
from app.core.events import CleanupEventType
from app.core.storage import MinioObjectStorage, ObjectStorage

logger = logging.getLogger(__name__)


def iter_cleanup_objects(event: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for item in event.get("objects", []):
        bucket = item.get("bucket")
        object_key = item.get("object_key")
        if bucket and object_key:
            yield bucket, object_key


def handle_cleanup_event(event: dict[str, Any], storage: ObjectStorage) -> None:
    event_type = event.get("event_type")
    if event_type not in {
        CleanupEventType.FILE_DELETE_REQUESTED,
        CleanupEventType.FOLDER_DELETE_REQUESTED,
        CleanupEventType.UPLOAD_FAILED,
        CleanupEventType.ACCOUNT_DELETE_REQUESTED,
    }:
        raise ValueError(f"Unsupported cleanup event type: {event_type}")

    for bucket, object_key in iter_cleanup_objects(event):
        storage.delete_object(bucket, object_key)


def build_cleanup_consumer():
    from kafka import KafkaConsumer

    return KafkaConsumer(
        settings.kafka_cleanup_topic,
        bootstrap_servers=settings.kafka_broker,
        client_id=settings.kafka_client_id,
        group_id=settings.kafka_cleanup_group_id,
        value_deserializer=lambda value: __import__("json").loads(value.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )


def consume_cleanup_events(consumer, storage: ObjectStorage) -> None:
    for message in consumer:
        event = message.value
        logger.info("processing cleanup event", extra={"event_type": event.get("event_type")})
        handle_cleanup_event(event, storage)


def run_cleanup_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    storage = MinioObjectStorage()
    consumer = build_cleanup_consumer()
    try:
        consume_cleanup_events(consumer, storage)
    finally:
        consumer.close()


if __name__ == "__main__":
    run_cleanup_worker()
