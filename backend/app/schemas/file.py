from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FileStatus, UploadSessionStatus


class FileSummary(BaseModel):
    id: uuid.UUID
    stored_filename: str
    content_type: str | None
    size_bytes: int
    status: FileStatus


class FileRead(BaseModel):
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


class FileRenameRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)


class FileMoveRequest(BaseModel):
    target_folder_id: uuid.UUID


class UploadInitRequest(BaseModel):
    folder_id: uuid.UUID
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=255)
    expected_size: int = Field(ge=1, le=50 * 1024 * 1024)


class UploadInitResponse(BaseModel):
    session_id: uuid.UUID
    resolved_filename: str
    object_key: str
    status: UploadSessionStatus


class UploadFinalizeRequest(BaseModel):
    upload_session_id: uuid.UUID
    size_bytes: int = Field(ge=1, le=50 * 1024 * 1024)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class UploadFailRequest(BaseModel):
    upload_session_id: uuid.UUID
    failure_reason: str = Field(min_length=1, max_length=1000)
