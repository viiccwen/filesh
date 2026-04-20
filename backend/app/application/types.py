from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    nickname: str
    is_active: bool
