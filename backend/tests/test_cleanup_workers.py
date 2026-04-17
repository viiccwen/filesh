from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.events import InMemoryEventPublisher
from app.persistence.models import File, UploadSession
from app.workers.cleanup import (
    build_dlq_event,
    compute_retry_delay_seconds,
    consume_cleanup_events,
    handle_cleanup_event,
    process_cleanup_message,
    replay_dlq_events,
    reset_event_for_replay,
    schedule_retry_event,
)
from tests_helpers import register_and_login


def test_upload_failed_event_is_cleaned_by_worker(
    client,
    session,
    object_storage,
    event_publisher,
) -> None:
    headers = register_and_login(client, "cleanup-upload@example.com", "cleanup-upload-user")
    root_response = client.get("/api/folders/root", headers=headers)
    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": root_response.json()["id"],
            "filename": "temp.txt",
            "expected_size": 4,
        },
    )
    upload_session_id = init_response.json()["session_id"]
    client.post(
        f"/api/files/upload/{upload_session_id}/content",
        headers=headers,
        files={"file": ("temp.txt", b"temp", "text/plain")},
    )

    upload_session = session.scalar(
        select(UploadSession).where(UploadSession.id == uuid.UUID(upload_session_id))
    )
    assert upload_session is not None
    assert object_storage.object_exists("files", upload_session.object_key)

    fail_response = client.post(
        "/api/files/upload/fail",
        headers=headers,
        json={
            "upload_session_id": upload_session_id,
            "failure_reason": "cancelled",
        },
    )

    assert fail_response.status_code == 204
    assert event_publisher.events[-1].payload["event_type"] == "upload.failed"

    handle_cleanup_event(event_publisher.events[-1].payload, object_storage)

    assert not object_storage.object_exists("files", upload_session.object_key)


def test_folder_delete_event_cleans_nested_objects(
    client,
    session,
    object_storage,
    event_publisher,
) -> None:
    headers = register_and_login(client, "cleanup-folder@example.com", "cleanup-folder-user")
    folder_response = client.post("/api/folders", headers=headers, json={"name": "trash"})

    init_response = client.post(
        "/api/files/upload/init",
        headers=headers,
        json={
            "folder_id": folder_response.json()["id"],
            "filename": "trash.txt",
            "expected_size": 5,
        },
    )
    client.post(
        f"/api/files/upload/{init_response.json()['session_id']}/content",
        headers=headers,
        files={"file": ("trash.txt", b"trash", "text/plain")},
    )
    finalize_response = client.post(
        "/api/files/upload/finalize",
        headers=headers,
        json={"upload_session_id": init_response.json()["session_id"], "size_bytes": 5},
    )

    file = session.scalar(select(File).where(File.id == uuid.UUID(finalize_response.json()["id"])))
    assert file is not None
    assert object_storage.object_exists(file.storage_bucket, file.object_key)

    delete_response = client.delete(f"/api/folders/{folder_response.json()['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert event_publisher.events[-1].payload["event_type"] == "folder.delete_requested"

    handle_cleanup_event(event_publisher.events[-1].payload, object_storage)

    assert not object_storage.object_exists(file.storage_bucket, file.object_key)


def test_consume_cleanup_events_processes_kafka_messages(object_storage) -> None:
    object_storage.put_object("files", "cleanup/test.txt", b"payload", "text/plain")

    class FakeMessage:
        def __init__(self, value) -> None:
            self.value = value

    class FakeConsumer:
        def __init__(self, messages) -> None:
            self._messages = iter(messages)
            self.committed = 0

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._messages)

        def commit(self) -> None:
            self.committed += 1

    consumer = FakeConsumer(
        [
            FakeMessage(
                {
                    "event_type": "file.delete_requested",
                    "objects": [{"bucket": "files", "object_key": "cleanup/test.txt"}],
                }
            )
        ]
    )

    consume_cleanup_events(consumer, object_storage, InMemoryEventPublisher())

    assert not object_storage.object_exists("files", "cleanup/test.txt")
    assert consumer.committed == 1


def test_process_cleanup_message_schedules_retry_on_failure(object_storage) -> None:
    class FakeConsumer:
        def __init__(self) -> None:
            self.committed = 0

        def commit(self) -> None:
            self.committed += 1

    class FakeMessage:
        topic = "filesh.cleanup"
        offset = 1

        def __init__(self, value) -> None:
            self.value = value

    publisher = InMemoryEventPublisher()
    consumer = FakeConsumer()
    message = FakeMessage({"event_type": "unsupported.event", "objects": []})

    process_cleanup_message(consumer, message, object_storage, publisher)

    assert consumer.committed == 1
    assert publisher.events[-1].topic == "filesh.cleanup.retry"
    assert publisher.events[-1].payload["delivery"]["attempt"] == 1
    assert "last_error" in publisher.events[-1].payload["delivery"]


def test_process_cleanup_message_sends_dlq_after_max_retries(object_storage) -> None:
    class FakeConsumer:
        def __init__(self) -> None:
            self.committed = 0

        def commit(self) -> None:
            self.committed += 1

    class FakeMessage:
        topic = "filesh.cleanup.retry"
        offset = 2

        def __init__(self, value) -> None:
            self.value = value

    publisher = InMemoryEventPublisher()
    consumer = FakeConsumer()
    message = FakeMessage(
        {
            "event_type": "unsupported.event",
            "objects": [],
            "delivery": {
                "attempt": 5,
                "max_retries": 5,
                "scheduled_at": datetime.now(UTC).isoformat(),
            },
        }
    )

    process_cleanup_message(consumer, message, object_storage, publisher)

    assert consumer.committed == 1
    assert publisher.events[-1].topic == "filesh.cleanup.dlq"
    assert "dlq_reason" in publisher.events[-1].payload["metadata"]


def test_retry_delay_uses_exponential_backoff() -> None:
    assert compute_retry_delay_seconds(1) < compute_retry_delay_seconds(2)
    assert compute_retry_delay_seconds(2) < compute_retry_delay_seconds(3)


def test_schedule_retry_event_sets_future_schedule() -> None:
    event = {
        "event_type": "file.delete_requested",
        "objects": [],
        "delivery": {
            "attempt": 0,
            "max_retries": 5,
            "scheduled_at": datetime.now(UTC).isoformat(),
        },
        "metadata": {},
    }

    retry_event = schedule_retry_event(event, ValueError("boom"))

    scheduled_at = datetime.fromisoformat(retry_event["delivery"]["scheduled_at"])
    assert retry_event["delivery"]["attempt"] == 1
    assert scheduled_at > datetime.now(UTC) - timedelta(seconds=1)


def test_build_dlq_event_adds_failure_metadata() -> None:
    event = {
        "event_type": "file.delete_requested",
        "objects": [],
        "delivery": {
            "attempt": 5,
            "max_retries": 5,
            "scheduled_at": datetime.now(UTC).isoformat(),
        },
        "metadata": {},
    }

    dlq_event = build_dlq_event(event, RuntimeError("fatal"))

    assert dlq_event["metadata"]["dlq_reason"] == "fatal"
    assert "failed_at" in dlq_event["delivery"]


def test_reset_event_for_replay_resets_delivery_state() -> None:
    event = {
        "event_type": "file.delete_requested",
        "objects": [],
        "delivery": {
            "attempt": 5,
            "max_retries": 5,
            "scheduled_at": datetime.now(UTC).isoformat(),
            "failed_at": datetime.now(UTC).isoformat(),
            "last_error": "fatal",
        },
        "metadata": {"replay_count": 1},
    }

    replay_event = reset_event_for_replay(event)

    assert replay_event["delivery"]["attempt"] == 0
    assert "failed_at" not in replay_event["delivery"]
    assert "last_error" not in replay_event["delivery"]
    assert replay_event["metadata"]["replay_count"] == 2
    assert replay_event["metadata"]["replayed_from_topic"] == "filesh.cleanup.dlq"


def test_replay_dlq_events_republishes_to_cleanup_topic() -> None:
    class FakeMessage:
        topic = "filesh.cleanup.dlq"
        offset = 7

        def __init__(self, value) -> None:
            self.value = value

    class FakeConsumer:
        def __init__(self, messages) -> None:
            self._messages = iter(messages)
            self.committed = 0

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._messages)

        def commit(self) -> None:
            self.committed += 1

    consumer = FakeConsumer(
        [
            FakeMessage(
                {
                    "event_type": "file.delete_requested",
                    "objects": [],
                    "metadata": {},
                    "delivery": {
                        "attempt": 5,
                        "max_retries": 5,
                        "scheduled_at": datetime.now(UTC).isoformat(),
                    },
                }
            )
        ]
    )
    publisher = InMemoryEventPublisher()

    replayed = replay_dlq_events(consumer, publisher, limit=10)

    assert replayed == 1
    assert consumer.committed == 1
    assert publisher.events[-1].topic == "filesh.cleanup"
    assert publisher.events[-1].payload["delivery"]["attempt"] == 0
