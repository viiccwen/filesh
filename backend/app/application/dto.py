from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.domain.enums import (
    FileStatus,
    PermissionLevel,
    ResourceType,
    ShareMode,
    UploadSessionStatus,
)


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    nickname: str
    is_active: bool


class UserDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    nickname: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class FileSummaryDTO(BaseModel):
    id: uuid.UUID
    stored_filename: str
    content_type: str | None
    size_bytes: int
    status: FileStatus
    created_at: datetime
    updated_at: datetime


class FileDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class FolderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path_cache: str | None
    created_at: datetime
    updated_at: datetime


class FolderContentsDTO(BaseModel):
    folder: FolderDTO
    folders: list[FolderDTO]
    files: list[FileSummaryDTO]


class ResourceSearchPaginationDTO(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class FolderSearchItemDTO(BaseModel):
    item_type: str = "FOLDER"
    folder: FolderDTO


class FileSearchItemDTO(BaseModel):
    item_type: str = "FILE"
    file: FileSummaryDTO


class ResourceSearchResponseDTO(BaseModel):
    items: list[FolderSearchItemDTO | FileSearchItemDTO]
    pagination: ResourceSearchPaginationDTO


class UploadInitDTO(BaseModel):
    session_id: uuid.UUID
    resolved_filename: str
    object_key: str
    status: UploadSessionStatus


class ShareReadDTO(BaseModel):
    id: uuid.UUID
    resource_type: ResourceType
    resource_id: uuid.UUID
    share_mode: ShareMode
    permission_level: PermissionLevel
    expires_at: datetime | None
    is_revoked: bool
    invitation_emails: list[EmailStr]
    share_url: str


class ShareAccessDTO(BaseModel):
    resource_type: ResourceType
    share_mode: ShareMode
    permission_level: PermissionLevel
    expires_at: datetime | None
    folder: FolderDTO | None = None
    file: FileDTO | None = None


class SharedFolderContentsDTO(BaseModel):
    folder: FolderDTO
    folders: list[FolderDTO]
    files: list[FileSummaryDTO]
    permission_level: PermissionLevel


class AccessTokenDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserDTO


class MessageDTO(BaseModel):
    message: str
