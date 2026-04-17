from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.enums import ResourceType
from app.schemas.file import FileSummary
from app.schemas.folder import FolderRead


class ResourceSearchQuery(BaseModel):
    parent_id: uuid.UUID
    q: str = Field(default="", max_length=255)
    type: ResourceType | None = None
    sort_by: Literal["name", "updated_at", "size", "type"] = "name"
    order: Literal["asc", "desc"] = "asc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=8, ge=1, le=100)


class ResourceSearchPagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class FolderSearchItem(BaseModel):
    item_type: Literal["FOLDER"] = "FOLDER"
    folder: FolderRead


class FileSearchItem(BaseModel):
    item_type: Literal["FILE"] = "FILE"
    file: FileSummary


class ResourceSearchResponse(BaseModel):
    items: list[FolderSearchItem | FileSearchItem]
    pagination: ResourceSearchPagination
