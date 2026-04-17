from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.core.events import CleanupEventType, EventPublisher, KafkaEventPublisher
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


def compute_retry_delay_seconds(attempt: int) -> int:
    exponent = max(attempt - 1, 0)
    delay = settings.kafka_cleanup_retry_base_seconds * (2**exponent)
    return min(delay, settings.kafka_cleanup_retry_max_seconds)


def get_delivery_metadata(event: dict[str, Any]) -> dict[str, Any]:
    delivery = event.setdefault("delivery", {})
    delivery.setdefault("attempt", 0)
    delivery.setdefault("max_retries", settings.kafka_cleanup_max_retries)
    delivery.setdefault("scheduled_at", datetime.now(UTC).isoformat())
    return delivery


def get_event_attempt(event: dict[str, Any]) -> int:
    delivery = get_delivery_metadata(event)
    return int(delivery["attempt"])


def get_event_max_retries(event: dict[str, Any]) -> int:
    delivery = get_delivery_metadata(event)
    return int(delivery["max_retries"])


def get_event_key(event: dict[str, Any], fallback: str) -> str:
    resource_id = event.get("resource", {}).get("id")
    return str(resource_id or fallback)


def schedule_retry_event(event: dict[str, Any], error: Exception) -> dict[str, Any]:
    next_event = json.loads(json.dumps(event))
    delivery = get_delivery_metadata(next_event)
    next_attempt = int(delivery["attempt"]) + 1
    delay_seconds = compute_retry_delay_seconds(next_attempt)
    scheduled_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
    delivery["attempt"] = next_attempt
    delivery["scheduled_at"] = scheduled_at.isoformat()
    delivery["last_error"] = str(error)
    metadata = next_event.setdefault("metadata", {})
    retry_history = list(metadata.get("retry_history", []))
    retry_history.append(
        {
            "attempt": next_attempt,
            "scheduled_at": delivery["scheduled_at"],
            "error": str(error),
        }
    )
    metadata["retry_history"] = retry_history
    return next_event


def build_dlq_event(event: dict[str, Any], error: Exception) -> dict[str, Any]:
    dlq_event = json.loads(json.dumps(event))
    delivery = get_delivery_metadata(dlq_event)
    delivery["failed_at"] = datetime.now(UTC).isoformat()
    delivery["last_error"] = str(error)
    metadata = dlq_event.setdefault("metadata", {})
    metadata["dlq_reason"] = str(error)
    metadata["source_topic"] = settings.kafka_cleanup_topic
    return dlq_event


def wait_until_scheduled(event: dict[str, Any]) -> None:
    scheduled_at = get_delivery_metadata(event)["scheduled_at"]
    scheduled_at_dt = datetime.fromisoformat(str(scheduled_at))
    if scheduled_at_dt.tzinfo is None:
        scheduled_at_dt = scheduled_at_dt.replace(tzinfo=UTC)
    remaining = (scheduled_at_dt - datetime.now(UTC)).total_seconds()
    if remaining > 0:
        time.sleep(remaining)


def ensure_cleanup_topics() -> None:
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError

    admin = KafkaAdminClient(
        bootstrap_servers=settings.kafka_broker,
        client_id=f"{settings.kafka_client_id}-cleanup-admin",
    )
    topics = [
        NewTopic(
            name=settings.kafka_cleanup_topic,
            num_partitions=settings.kafka_cleanup_topic_partitions,
            replication_factor=settings.kafka_cleanup_replication_factor,
        ),
        NewTopic(
            name=settings.kafka_cleanup_retry_topic,
            num_partitions=settings.kafka_cleanup_retry_topic_partitions,
            replication_factor=settings.kafka_cleanup_replication_factor,
        ),
        NewTopic(
            name=settings.kafka_cleanup_dlq_topic,
            num_partitions=settings.kafka_cleanup_dlq_topic_partitions,
            replication_factor=settings.kafka_cleanup_replication_factor,
        ),
    ]
    try:
        admin.create_topics(topics, validate_only=False)
    except TopicAlreadyExistsError:
        pass
    finally:
        admin.close()


def build_cleanup_consumer():
    from kafka import KafkaConsumer

    return KafkaConsumer(
        settings.kafka_cleanup_topic,
        settings.kafka_cleanup_retry_topic,
        bootstrap_servers=settings.kafka_broker,
        client_id=settings.kafka_client_id,
        group_id=settings.kafka_cleanup_group_id,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )


def process_cleanup_message(
    consumer,
    message,
    storage: ObjectStorage,
    publisher: EventPublisher,
) -> None:
    event = message.value
    wait_until_scheduled(event)
    try:
        logger.info(
            "processing cleanup event",
            extra={
                "event_type": event.get("event_type"),
                "attempt": get_event_attempt(event),
                "topic": getattr(message, "topic", settings.kafka_cleanup_topic),
            },
        )
        handle_cleanup_event(event, storage)
    except Exception as exc:
        if get_event_attempt(event) >= get_event_max_retries(event):
            publisher.publish(
                settings.kafka_cleanup_dlq_topic,
                get_event_key(event, str(getattr(message, "offset", "dlq"))),
                build_dlq_event(event, exc),
            )
            logger.exception("cleanup event sent to dlq")
        else:
            retry_event = schedule_retry_event(event, exc)
            publisher.publish(
                settings.kafka_cleanup_retry_topic,
                get_event_key(retry_event, str(getattr(message, "offset", "retry"))),
                retry_event,
            )
            logger.warning(
                "cleanup event scheduled for retry",
                extra={
                    "event_type": event.get("event_type"),
                    "attempt": get_event_attempt(retry_event),
                },
            )
    finally:
        consumer.commit()


def consume_cleanup_events(
    consumer,
    storage: ObjectStorage,
    publisher: EventPublisher,
) -> None:
    for message in consumer:
        process_cleanup_message(consumer, message, storage, publisher)


def run_cleanup_worker() -> None:
    logging.basicConfig(level=logging.INFO)
    ensure_cleanup_topics()
    storage = MinioObjectStorage()
    publisher = KafkaEventPublisher()
    consumer = build_cleanup_consumer()
    try:
        consume_cleanup_events(consumer, storage, publisher)
    finally:
        consumer.close()


if __name__ == "__main__":
    run_cleanup_worker()
