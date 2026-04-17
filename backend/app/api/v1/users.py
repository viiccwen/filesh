from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.errors import to_http_exception
from app.application.use_cases.users import UserUseCase
from app.dependencies.auth import get_current_user
from app.dependencies.use_cases import get_user_use_case
from app.domain import AppError
from app.models import User
from app.schemas.user import UserRead, UserUpdateRequest

router = APIRouter()
current_user_dependency = Depends(get_current_user)
user_use_case_dependency = Depends(get_user_use_case)


@router.get("/me", response_model=UserRead)
def get_me(
    current_user: User = current_user_dependency,
    use_case: UserUseCase = user_use_case_dependency,
) -> UserRead:
    try:
        return use_case.get_me(current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdateRequest,
    current_user: User = current_user_dependency,
    use_case: UserUseCase = user_use_case_dependency,
) -> UserRead:
    try:
        return use_case.update_me(current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc
