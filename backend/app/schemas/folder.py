from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None


class FolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path_cache: str | None
    created_at: datetime
    updated_at: datetime


class FolderContentsResponse(BaseModel):
    folder: FolderRead
    folders: list[FolderRead]
    files: list[dict[str, object]]
