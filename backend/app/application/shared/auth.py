from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto import AccessTokenDTO, UserDTO
from app.application.shared.folders import create_root_folder
from app.core.config import settings
from app.core.events import CleanupEventType, EventPublisher, build_cleanup_event
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.domain import AuthenticationError, AuthorizationError, ConflictError, ValidationError
from app.persistence.models import User
from app.repositories import users as user_repository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest


def register_user(session: Session, payload: RegisterRequest) -> User:
    existing_user = user_repository.get_user_by_email_or_username(
        session,
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
    user_repository.add_user(session, user)
    session.flush()
    create_root_folder(session, user.id)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, payload: LoginRequest) -> User:
    user = user_repository.get_user_by_identifier(session, payload.identifier)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Invalid credentials")

    if not user.is_active:
        raise AuthorizationError("User is inactive")

    return user


def build_auth_response(user: User) -> tuple[AccessTokenDTO, str]:
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return (
        AccessTokenDTO(access_token=access_token, user=UserDTO.model_validate(user)),
        refresh_token,
    )


def change_user_password(session: Session, user: User, payload: ChangePasswordRequest) -> User:
    if not verify_password(payload.current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise ValidationError("New password must be different from current password")

    user.password_hash = hash_password(payload.new_password)
    session.commit()
    session.refresh(user)
    return user


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
