from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.core.events import CleanupEventType
from app.core.storage import ObjectStorage


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
