from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.events import CleanupEventType, EventPublisher, build_cleanup_event
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domain import AuthenticationError, AuthorizationError, ConflictError
from app.models import User
from app.schemas.auth import AccessTokenResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserRead
from app.services.folders import create_root_folder


def register_user(session: Session, payload: RegisterRequest) -> User:
    existing_user = session.scalar(
        select(User).where(or_(User.email == payload.email, User.username == payload.username))
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
    session.add(user)
    session.flush()
    create_root_folder(session, user)
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
        raise AuthenticationError("Invalid credentials")

    if not user.is_active:
        raise AuthorizationError("User is inactive")

    return user


def build_auth_response(user: User) -> tuple[AccessTokenResponse, str]:
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return (
        AccessTokenResponse(access_token=access_token, user=UserRead.model_validate(user)),
        refresh_token,
    )


def delete_user_account(session: Session, user: User, event_publisher: EventPublisher) -> None:
    objects = [
        {"bucket": file.storage_bucket, "object_key": file.object_key} for file in user.files
    ]
    event = build_cleanup_event(
        CleanupEventType.ACCOUNT_DELETE_REQUESTED,
        resource={"type": "user", "id": str(user.id)},
        objects=objects,
        metadata={"email": user.email, "username": user.username},
    )
    session.delete(user)
    session.commit()
    event_publisher.publish(settings.kafka_cleanup_topic, str(user.id), event)
