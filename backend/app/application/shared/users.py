from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import ConflictError
from app.models import User
from app.repositories import users as user_repository
from app.schemas.user import UserUpdateRequest


def update_profile(session: Session, current_user: User, payload: UserUpdateRequest) -> User:
    existing_user = user_repository.get_user_by_username(session, payload.username)
    if existing_user is not None and existing_user.id != current_user.id:
        raise ConflictError("Username taken")

    current_user.username = payload.username
    current_user.nickname = payload.nickname
    session.commit()
    session.refresh(current_user)
    return current_user
