from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto import AuthenticatedUser
from app.domain import ConflictError, NotFoundError
from app.models import User
from app.repositories import users as user_repository
from app.schemas.user import UserUpdateRequest


def update_profile(
    session: Session,
    current_user: AuthenticatedUser,
    payload: UserUpdateRequest,
) -> User:
    user = user_repository.get_active_user_by_id(session, current_user.id)
    if user is None:
        raise NotFoundError("User not found")

    existing_user = user_repository.get_user_by_username(session, payload.username)
    if existing_user is not None and existing_user.id != user.id:
        raise ConflictError("Username taken")

    user.username = payload.username
    user.nickname = payload.nickname
    session.commit()
    session.refresh(user)
    return user
