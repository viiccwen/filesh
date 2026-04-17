from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import User


def add_user(session: Session, user: User) -> None:
    session.add(user)


def get_user_by_email_or_username(
    session: Session,
    email: str,
    username: str,
) -> User | None:
    return session.scalar(select(User).where(or_(User.email == email, User.username == username)))


def get_user_by_identifier(session: Session, identifier: str) -> User | None:
    return session.scalar(
        select(User).where(or_(User.email == identifier, User.username == identifier))
    )


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def get_active_user_by_id(session: Session, user_id) -> User | None:
    return session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
