from __future__ import annotations

import uuid

import jwt

from app.application.ports import UnitOfWorkPort
from app.application.types import AuthenticatedUser
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain import AuthenticationError, AuthorizationError, ConflictError, ValidationError
from app.persistence.models import User
from app.schemas.auth import ChangePasswordRequest, RegisterRequest
from app.schemas.user import UserRead


def register_user(uow: UnitOfWorkPort, payload: RegisterRequest) -> User:
    existing_user = uow.users.get_by_email_or_username(
        email=str(payload.email),
        username=payload.username,
    )
    if existing_user is not None:
        detail = (
            "Email already registered" if existing_user.email == payload.email else "Username taken"
        )
        raise ConflictError(detail)

    user = User(
        email=str(payload.email),
        username=payload.username,
        nickname=payload.nickname,
        password_hash=hash_password(payload.password),
    )
    uow.users.add(user)
    uow.flush()
    return user


def authenticate_user(uow: UnitOfWorkPort, identifier: str, password: str) -> User:
    user = uow.users.get_by_identifier(identifier)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid credentials")
    if not user.is_active:
        raise AuthorizationError("User is inactive")
    return user


def build_auth_tokens(user: User) -> tuple[str, str]:
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return access_token, refresh_token


def resolve_access_user(uow: UnitOfWorkPort, access_token: str) -> AuthenticatedUser:
    try:
        payload = decode_token(access_token, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, jwt.InvalidTokenError) as exc:
        raise AuthenticationError("Invalid access token") from exc

    user = uow.users.get_active_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    return AuthenticatedUser.model_validate(user)


def resolve_refresh_user(uow: UnitOfWorkPort, refresh_token: str | None) -> User:
    if refresh_token is None:
        raise AuthenticationError("Refresh token missing")
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid refresh token") from exc

    user_id = uuid.UUID(payload["sub"])
    user = uow.users.get_active_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    return user


def require_active_user(uow: UnitOfWorkPort, user_id: uuid.UUID) -> User:
    user = uow.users.get_active_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    return user


def get_active_user(uow: UnitOfWorkPort, user_id) -> User:
    user = uow.users.get_active_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    return user


def update_profile(
    uow: UnitOfWorkPort,
    current_user: AuthenticatedUser,
    username: str,
    nickname: str,
) -> User:
    user = get_active_user(uow, current_user.id)

    existing_user = uow.users.get_by_username(username)
    if existing_user is not None and existing_user.id != user.id:
        raise ConflictError("Username taken")

    user.username = username
    user.nickname = nickname
    return user


def change_user_password(user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise ValidationError("New password must be different from current password")

    user.password_hash = hash_password(payload.new_password)


def to_user_read(user: User) -> UserRead:
    return UserRead.model_validate(user)
