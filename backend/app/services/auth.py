from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserRead


def register_user(session: Session, payload: RegisterRequest) -> User:
    existing_user = session.scalar(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
    )
    if existing_user is not None:
        detail = (
            "Email already registered" if existing_user.email == payload.email else "Username taken"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    user = User(
        email=str(payload.email),
        username=payload.username,
        nickname=payload.nickname,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, payload: LoginRequest) -> User:
    user = session.scalar(
        select(User).where(
            or_(User.email == payload.identifier, User.username == payload.identifier)
        )
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return user


def build_auth_response(user: User) -> tuple[AccessTokenResponse, str]:
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return (
        AccessTokenResponse(access_token=access_token, user=UserRead.model_validate(user)),
        refresh_token,
    )
