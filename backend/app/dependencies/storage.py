from __future__ import annotations

from app.application.ports import ObjectStoragePort
from app.core.storage import MinioObjectStorage


def get_object_storage() -> ObjectStoragePort:
    return MinioObjectStorage()
