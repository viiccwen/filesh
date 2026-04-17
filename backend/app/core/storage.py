from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


@dataclass
class StoredObject:
    data: bytes
    content_type: str | None


class ObjectStorage(Protocol):
    def put_object(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str | None,
    ) -> None: ...

    def get_object(self, bucket: str, object_key: str) -> StoredObject: ...

    def delete_object(self, bucket: str, object_key: str) -> None: ...

    def object_exists(self, bucket: str, object_key: str) -> bool: ...


class MinioObjectStorage:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )

    def put_object(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str | None,
    ) -> None:
        self.client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get_object(self, bucket: str, object_key: str) -> StoredObject:
        response = self.client.get_object(bucket, object_key)
        try:
            return StoredObject(
                data=response.read(),
                content_type=response.headers.get("Content-Type"),
            )
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, bucket: str, object_key: str) -> None:
        try:
            self.client.remove_object(bucket, object_key)
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise

    def object_exists(self, bucket: str, object_key: str) -> bool:
        try:
            self.client.stat_object(bucket, object_key)
            return True
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return False
            raise
