from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, EmailStr

from app.domain.enums import (
    FileStatus,
    PermissionLevel,
    ResourceType,
    ShareMode,
    UploadSessionStatus,
)


@dataclass
class StoredObject:
    data: bytes
    content_type: str | None


class FileRecord(Protocol):
    id: uuid.UUID
    owner_id: uuid.UUID
    folder_id: uuid.UUID
    original_filename: str
    stored_filename: str
    extension: str | None
    content_type: str | None
    size_bytes: int
    checksum_sha256: str | None
    object_key: str
    storage_bucket: str
    status: FileStatus
    uploaded_by: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class UploadSessionRecord(Protocol):
    id: uuid.UUID
    owner_id: uuid.UUID
    folder_id: uuid.UUID
    original_filename: str
    resolved_filename: str
    object_key: str
    content_type: str | None
    expected_size: int
    status: UploadSessionStatus
    failure_reason: str | None
    finalized_at: datetime | None
    file: FileRecord | None


class FolderRecord(Protocol):
    id: uuid.UUID
    owner_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path_cache: str | None
    created_at: datetime
    updated_at: datetime
    children: list[FolderRecord]
    files: list[FileRecord]


class ShareInvitationRecord(Protocol):
    invited_email: str


class ShareLinkRecord(Protocol):
    id: uuid.UUID
    resource_type: ResourceType
    resource_id: uuid.UUID
    owner_id: uuid.UUID
    share_mode: ShareMode
    permission_level: PermissionLevel
    token_hash: str
    token_ciphertext: str | None
    expires_at: datetime | None
    is_revoked: bool
    invitations: list[ShareInvitationRecord]


class UserRecord(Protocol):
    id: uuid.UUID
    email: str
    username: str
    nickname: str
    password_hash: str
    is_active: bool
    files: list[FileRecord]


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    nickname: str
    is_active: bool
