from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.models import PermissionLevel, ResourceType, ShareMode
from app.schemas.file import FileRead, FileSummary
from app.schemas.folder import FolderRead

ExpiryOption = Literal["hour", "day", "never"]


class ShareUpsertRequest(BaseModel):
    share_mode: ShareMode
    permission_level: PermissionLevel
    expiry: ExpiryOption = "never"
    invitation_emails: list[EmailStr] = []


class ShareRead(BaseModel):
    id: uuid.UUID
    resource_type: ResourceType
    resource_id: uuid.UUID
    share_mode: ShareMode
    permission_level: PermissionLevel
    expires_at: datetime | None
    is_revoked: bool
    invitation_emails: list[EmailStr]
    share_url: str


class ShareAccessResponse(BaseModel):
    resource_type: ResourceType
    share_mode: ShareMode
    permission_level: PermissionLevel
    expires_at: datetime | None
    folder: FolderRead | None = None
    file: FileRead | None = None


class SharedFolderContentsResponse(BaseModel):
    folder: FolderRead
    folders: list[FolderRead]
    files: list[FileSummary]
    permission_level: PermissionLevel
