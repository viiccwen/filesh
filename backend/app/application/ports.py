from __future__ import annotations

import uuid
from typing import Any, Protocol

from app.application.types import (
    FileRecord,
    FolderRecord,
    ShareLinkRecord,
    StoredObject,
    UploadSessionRecord,
    UserRecord,
)
from app.domain.enums import ResourceType


class EventPublisherPort(Protocol):
    def publish(self, topic: str, key: str, payload: dict[str, Any]) -> None: ...


class ObjectStoragePort(Protocol):
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


class UsersRepositoryPort(Protocol):
    def add(self, user: UserRecord) -> None: ...

    def get_by_email_or_username(self, *, email: str, username: str) -> UserRecord | None: ...

    def get_by_identifier(self, identifier: str) -> UserRecord | None: ...

    def get_by_username(self, username: str) -> UserRecord | None: ...

    def get_active_by_id(self, user_id: uuid.UUID) -> UserRecord | None: ...


class FilesRepositoryPort(Protocol):
    def list_filenames_in_folder(self, folder_id: uuid.UUID) -> set[str]: ...

    def list_reserved_filenames_in_folder(self, folder_id: uuid.UUID) -> set[str]: ...

    def add_upload_session(self, upload_session: UploadSessionRecord) -> None: ...

    def get_upload_session_by_owner(
        self, upload_session_id: uuid.UUID, owner_id: uuid.UUID
    ) -> UploadSessionRecord | None: ...

    def add_file(self, file: FileRecord) -> None: ...

    def get_by_owner(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> FileRecord | None: ...

    def get_by_id(self, file_id: uuid.UUID) -> FileRecord | None: ...

    def list_by_folder_ids(self, folder_ids: list[uuid.UUID]) -> list[FileRecord]: ...


class FoldersRepositoryPort(Protocol):
    def add(self, folder: FolderRecord) -> None: ...

    def get_root(self, user_id: uuid.UUID, root_folder_name: str) -> FolderRecord | None: ...

    def get_by_owner(self, folder_id: uuid.UUID, owner_id: uuid.UUID) -> FolderRecord | None: ...

    def get_by_id(self, folder_id: uuid.UUID) -> FolderRecord | None: ...

    def get_with_contents_by_owner(
        self,
        folder_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> FolderRecord | None: ...

    def list_descendant_folder_ids(
        self,
        owner_id: uuid.UUID,
        path_prefix: str,
    ) -> list[uuid.UUID]: ...

    def list_descendant_folders(
        self, owner_id: uuid.UUID, path_prefix: str
    ) -> list[FolderRecord]: ...

    def list_upload_sessions_by_folder_ids(
        self,
        folder_ids: list[uuid.UUID],
    ) -> list[UploadSessionRecord]: ...


class SharesRepositoryPort(Protocol):
    def get_active_for_resource(
        self,
        resource_type: ResourceType,
        resource_id: uuid.UUID,
    ) -> ShareLinkRecord | None: ...

    def add_share_link(self, share_link: ShareLinkRecord) -> None: ...

    def get_active_users_by_emails(self, emails: list[str]) -> list[UserRecord]: ...

    def get_by_token_hash(self, token_hash: str) -> ShareLinkRecord | None: ...

    def get_shared_file(self, file_id: uuid.UUID) -> FileRecord | None: ...

    def get_shared_folder(self, folder_id: uuid.UUID) -> FolderRecord | None: ...


class UnitOfWorkPort(Protocol):
    users: UsersRepositoryPort
    files: FilesRepositoryPort
    folders: FoldersRepositoryPort
    shares: SharesRepositoryPort

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def refresh(self, instance: object) -> None: ...

    def flush(self) -> None: ...

    def add(self, instance: object) -> None: ...

    def delete(self, instance: object) -> None: ...
