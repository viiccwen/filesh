from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.dto import AuthenticatedUser, UserDTO
from app.application.shared.users import update_profile
from app.domain import NotFoundError
from app.repositories import users as user_repository
from app.schemas.user import UserUpdateRequest


class UserUseCase:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_me(self, current_user: AuthenticatedUser) -> UserDTO:
        user = user_repository.get_active_user_by_id(self.session, current_user.id)
        if user is None:
            raise NotFoundError("User not found")
        return UserDTO.model_validate(user)

    def update_me(self, current_user: AuthenticatedUser, payload: UserUpdateRequest) -> UserDTO:
        user = update_profile(self.session, current_user, payload)
        return UserDTO.model_validate(user)
