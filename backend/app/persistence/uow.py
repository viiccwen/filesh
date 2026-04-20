from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.ports import UnitOfWorkPort
from app.persistence.repositories import (
    SqlAlchemyFilesRepository,
    SqlAlchemyFoldersRepository,
    SqlAlchemyResourcesRepository,
    SqlAlchemySharesRepository,
    SqlAlchemyUsersRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = SqlAlchemyUsersRepository(session)
        self.files = SqlAlchemyFilesRepository(session)
        self.folders = SqlAlchemyFoldersRepository(session)
        self.shares = SqlAlchemySharesRepository(session)
        self.resources = SqlAlchemyResourcesRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def refresh(self, instance: object) -> None:
        self.session.refresh(instance)

    def flush(self) -> None:
        self.session.flush()

    def add(self, instance: object) -> None:
        self.session.add(instance)

    def delete(self, instance: object) -> None:
        self.session.delete(instance)
