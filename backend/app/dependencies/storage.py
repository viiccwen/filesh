from __future__ import annotations

from app.core.storage import MinioObjectStorage, ObjectStorage


def get_object_storage() -> ObjectStorage:
    return MinioObjectStorage()
