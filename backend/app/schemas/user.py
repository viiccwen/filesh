from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserUpdateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    nickname: str = Field(min_length=1, max_length=100)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    nickname: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
