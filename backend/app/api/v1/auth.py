from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db_session
from app.core.security import clear_refresh_cookie, decode_token, set_refresh_cookie
from app.models import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, LogoutResponse, RegisterRequest
from app.schemas.user import UserRead
from app.services.auth import authenticate_user, build_auth_response, register_user

router = APIRouter()
db_session_dependency = Depends(get_db_session)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = db_session_dependency) -> UserRead:
    user = register_user(session, payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=AccessTokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = db_session_dependency,
) -> AccessTokenResponse:
    user = authenticate_user(session, payload)
    auth_response, refresh_token = build_auth_response(user)
    set_refresh_cookie(response, refresh_token)
    return auth_response


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_access_token(
    response: Response,
    session: Session = db_session_dependency,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_token_cookie_name),
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    user_id = uuid.UUID(payload["sub"])
    user = session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    auth_response, next_refresh_token = build_auth_response(user)
    set_refresh_cookie(response, next_refresh_token)
    return auth_response


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    clear_refresh_cookie(response)
    return LogoutResponse(message="Logged out")
