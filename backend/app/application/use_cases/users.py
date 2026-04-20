from __future__ import annotations

from app.application.ports import UnitOfWorkPort
from app.application.services import identity
from app.application.types import AuthenticatedUser
from app.application.use_cases.base import UseCaseBase
from app.schemas.user import UserRead, UserUpdateRequest


class UserUseCase(UseCaseBase):
    def __init__(self, uow: UnitOfWorkPort) -> None:
        super().__init__(uow)

    def get_me(self, current_user: AuthenticatedUser) -> UserRead:
        user = identity.get_active_user(self.uow, current_user.id)
        return identity.to_user_read(user)

    def update_me(self, current_user: AuthenticatedUser, payload: UserUpdateRequest) -> UserRead:
        user = self.in_transaction(
            lambda: identity.update_profile(
                self.uow,
                current_user,
                payload.username,
                payload.nickname,
            )
        )
        self.uow.refresh(user)
        return identity.to_user_read(user)
