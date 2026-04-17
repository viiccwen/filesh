from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.shared.users import update_profile
from app.models import User
from app.schemas.user import UserRead, UserUpdateRequest


class UserUseCase:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_me(self, current_user: User) -> UserRead:
        return UserRead.model_validate(current_user)

    def update_me(self, current_user: User, payload: UserUpdateRequest) -> UserRead:
        user = update_profile(self.session, current_user, payload)
        return UserRead.model_validate(user)
