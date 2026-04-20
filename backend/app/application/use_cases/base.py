from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.application.ports import UnitOfWorkPort

T = TypeVar("T")


class UseCaseBase:
    def __init__(self, uow: UnitOfWorkPort) -> None:
        self.uow = uow

    def in_transaction(self, operation: Callable[[], T], *, refresh: object | None = None) -> T:
        try:
            result = operation()
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            raise

        if refresh is not None:
            self.uow.refresh(refresh)
        return result
