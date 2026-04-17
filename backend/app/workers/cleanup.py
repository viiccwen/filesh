from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.core.events import CleanupEventType, EventPublisher, KafkaEventPublisher
from app.core.observability import (
    configure_logging,
    current_time,
    observe_cleanup_consumer_position,
    observe_cleanup_event,
    request_log_extra,
    start_metrics_server,
)
from app.core.storage import MinioObjectStorage, ObjectStorage
from app.core.tracing import (
    WORKER_SPAN_KIND,
    configure_tracing,
    extract_trace_context,
    get_tracer,
    record_span_exception,
    set_span_attributes,
)

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


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


def build_dlq_replay_consumer(*, consumer_timeout_ms: int = 1000):
    from kafka import KafkaConsumer

    return KafkaConsumer(
        settings.kafka_cleanup_dlq_topic,
        bootstrap_servers=settings.kafka_broker,
        client_id=f"{settings.kafka_client_id}-dlq-replay",
        group_id=settings.kafka_cleanup_replay_group_id,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        consumer_timeout_ms=consumer_timeout_ms,
    )


def observe_consumer_position(consumer, message) -> None:
    topic = getattr(message, "topic", None)
    partition = getattr(message, "partition", None)
    offset = getattr(message, "offset", None)
    if topic is None or partition is None or offset is None:
        return
    if not hasattr(consumer, "end_offsets"):
        return
    from kafka.structs import TopicPartition

    topic_partition = TopicPartition(str(topic), int(partition))
    end_offsets = consumer.end_offsets([topic_partition])
    end_offset = end_offsets.get(topic_partition)
    if end_offset is None:
        return
    observe_cleanup_consumer_position(
        topic=str(topic),
        partition=int(partition),
        group_id=settings.kafka_cleanup_group_id,
        current_offset=int(offset) + 1,
        end_offset=int(end_offset),
    )


def process_cleanup_message(
    consumer,
    message,
    storage: ObjectStorage,
    publisher: EventPublisher,
) -> None:
    event = message.value
    started_at = current_time()
    topic = getattr(message, "topic", settings.kafka_cleanup_topic)
    event_type = str(event.get("event_type"))
    observe_consumer_position(consumer, message)
    wait_until_scheduled(event)
    parent_context = extract_trace_context(event.get("metadata"))
    with tracer.start_as_current_span(
        f"cleanup {event_type}",
        context=parent_context,
        kind=WORKER_SPAN_KIND,
    ) as span:
        set_span_attributes(
            span,
            {
                "messaging.system": "kafka",
                "messaging.destination.name": topic,
                "messaging.kafka.offset": getattr(message, "offset", None),
                "messaging.kafka.partition": getattr(message, "partition", None),
                "cleanup.event_type": event_type,
                "cleanup.attempt": get_event_attempt(event),
                "cleanup.correlation_id": event.get("metadata", {}).get("correlation_id"),
            },
        )
        try:
            logger.info(
                "processing cleanup event",
                extra=request_log_extra(
                    event_type=event_type,
                    attempt=get_event_attempt(event),
                    topic=topic,
                ),
            )
            handle_cleanup_event(event, storage)
            observe_cleanup_event(
                event_type=event_type,
                topic=topic,
                outcome="processed",
                duration=current_time() - started_at,
            )
        except Exception as exc:
            record_span_exception(span, exc)
            if get_event_attempt(event) >= get_event_max_retries(event):
                publisher.publish(
                    settings.kafka_cleanup_dlq_topic,
                    get_event_key(event, str(getattr(message, "offset", "dlq"))),
                    build_dlq_event(event, exc),
                )
                observe_cleanup_event(
                    event_type=event_type,
                    topic=topic,
                    outcome="dlq",
                    duration=current_time() - started_at,
                )
                logger.exception(
                    "cleanup event sent to dlq",
                    extra=request_log_extra(event_type=event_type, topic=topic),
                )
            else:
                retry_event = schedule_retry_event(event, exc)
                publisher.publish(
                    settings.kafka_cleanup_retry_topic,
                    get_event_key(retry_event, str(getattr(message, "offset", "retry"))),
                    retry_event,
                )
                observe_cleanup_event(
                    event_type=event_type,
                    topic=topic,
                    outcome="retry",
                    duration=current_time() - started_at,
                )
                logger.warning(
                    "cleanup event scheduled for retry",
                    extra=request_log_extra(
                        event_type=event_type,
                        attempt=get_event_attempt(retry_event),
                        topic=topic,
                    ),
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


def reset_event_for_replay(event: dict[str, Any]) -> dict[str, Any]:
    replay_event = json.loads(json.dumps(event))
    delivery = get_delivery_metadata(replay_event)
    delivery["attempt"] = 0
    delivery["scheduled_at"] = datetime.now(UTC).isoformat()
    delivery.pop("failed_at", None)
    delivery.pop("last_error", None)
    metadata = replay_event.setdefault("metadata", {})
    metadata["replayed_from_dlq_at"] = datetime.now(UTC).isoformat()
    metadata["replayed_from_topic"] = settings.kafka_cleanup_dlq_topic
    metadata["replay_count"] = int(metadata.get("replay_count", 0)) + 1
    return replay_event


def replay_dlq_events(
    consumer,
    publisher: EventPublisher,
    *,
    limit: int,
    dry_run: bool = False,
) -> int:
    replayed = 0
    for message in consumer:
        event = message.value
        replay_event = reset_event_for_replay(event)
        if not dry_run:
            publisher.publish(
                settings.kafka_cleanup_topic,
                get_event_key(replay_event, str(getattr(message, "offset", "replay"))),
                replay_event,
            )
        consumer.commit()
        replayed += 1
        logger.info(
            "replayed cleanup dlq event",
            extra=request_log_extra(
                event_type=str(event.get("event_type")),
                original_topic=getattr(message, "topic", settings.kafka_cleanup_dlq_topic),
                replayed_to=settings.kafka_cleanup_topic,
                dry_run=dry_run,
            ),
        )
        if replayed >= limit:
            break
    return replayed


def run_cleanup_worker() -> None:
    configure_logging()
    configure_tracing(service_name="filesh-cleanup-worker")
    start_metrics_server(settings.worker_metrics_port)
    ensure_cleanup_topics()
    storage = MinioObjectStorage()
    publisher = KafkaEventPublisher()
    consumer = build_cleanup_consumer()
    try:
        consume_cleanup_events(consumer, storage, publisher)
    finally:
        consumer.close()


def run_cleanup_dlq_replay(*, limit: int, dry_run: bool) -> int:
    configure_logging()
    configure_tracing(service_name="filesh-cleanup-dlq-replay")
    publisher = KafkaEventPublisher()
    consumer = build_dlq_replay_consumer()
    try:
        return replay_dlq_events(consumer, publisher, limit=limit, dry_run=dry_run)
    finally:
        consumer.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run cleanup worker utilities.")
    parser.add_argument(
        "--replay-dlq",
        action="store_true",
        help="Replay cleanup events from the DLQ back into the primary cleanup topic.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=settings.kafka_cleanup_dlq_replay_limit,
        help="Maximum number of DLQ events to replay in one run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect DLQ messages without publishing them back to the cleanup topic.",
    )
    args = parser.parse_args()

    if args.replay_dlq:
        run_cleanup_dlq_replay(limit=args.limit, dry_run=args.dry_run)
        return
    run_cleanup_worker()


if __name__ == "__main__":
    main()
