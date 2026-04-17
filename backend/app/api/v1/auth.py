from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.api.errors import to_http_exception
from app.application.use_cases.auth import AuthUseCase
from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.dependencies.use_cases import get_auth_use_case
from app.domain import AppError
from app.models import User
from app.schemas.auth import (
    AccessTokenResponse,
    DeleteAccountResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
)
from app.schemas.user import UserRead

router = APIRouter()
current_user_dependency = Depends(get_current_user)
auth_use_case_dependency = Depends(get_auth_use_case)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    use_case: AuthUseCase = auth_use_case_dependency,
) -> UserRead:
    try:
        return use_case.register(payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    use_case: AuthUseCase = auth_use_case_dependency,
) -> AccessTokenResponse:
    try:
        auth_response, refresh_token = use_case.login(payload)
        use_case.set_refresh_cookie(response, refresh_token)
        return auth_response
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_token_cookie_name),
    use_case: AuthUseCase = auth_use_case_dependency,
) -> AccessTokenResponse:
    try:
        auth_response, next_refresh_token = use_case.refresh_access_token(refresh_token)
        use_case.set_refresh_cookie(response, next_refresh_token)
        return auth_response
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response, use_case: AuthUseCase = auth_use_case_dependency) -> LogoutResponse:
    use_case.clear_refresh_cookie(response)
    return use_case.logout()


@router.delete("/me", response_model=DeleteAccountResponse)
def delete_account(
    response: Response,
    current_user: User = current_user_dependency,
    use_case: AuthUseCase = auth_use_case_dependency,
) -> DeleteAccountResponse:
    try:
        delete_response = use_case.delete_account(current_user)
        use_case.clear_refresh_cookie(response)
        return delete_response
    except AppError as exc:
        raise to_http_exception(exc) from exc
