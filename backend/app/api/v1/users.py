from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.user import UserRead

router = APIRouter()
current_user_dependency = Depends(get_current_user)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = current_user_dependency) -> UserRead:
    return UserRead.model_validate(current_user)
