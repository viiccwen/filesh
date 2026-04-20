from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.application.ports import UsersRepositoryPort
from app.persistence.models import User


class SqlAlchemyUsersRepository(UsersRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: User) -> None:
        self.session.add(user)

    def get_by_email_or_username(self, *, email: str, username: str) -> User | None:
        return self.session.scalar(
            select(User).where(or_(User.email == email, User.username == username))
        )

    def get_by_identifier(self, identifier: str) -> User | None:
        return self.session.scalar(
            select(User).where(or_(User.email == identifier, User.username == identifier))
        )

    def get_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
