from __future__ import annotations

import uuid

import jwt
from sqlalchemy.orm import Session

from app.application.shared.auth import (
    authenticate_user,
    build_auth_response,
    delete_user_account,
    register_user,
)
from app.core.events import EventPublisher
from app.core.security import clear_refresh_cookie, decode_token, set_refresh_cookie
from app.domain import AuthenticationError
from app.models import User
from app.repositories import users as user_repository
from app.schemas.auth import (
    AccessTokenResponse,
    DeleteAccountResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
)
from app.schemas.user import UserRead


class AuthUseCase:
    def __init__(self, session: Session, event_publisher: EventPublisher) -> None:
        self.session = session
        self.event_publisher = event_publisher

    def register(self, payload: RegisterRequest) -> UserRead:
        user = register_user(self.session, payload)
        return UserRead.model_validate(user)

    def login(self, payload: LoginRequest) -> tuple[AccessTokenResponse, str]:
        user = authenticate_user(self.session, payload)
        return build_auth_response(user)

    def refresh_access_token(self, refresh_token: str | None) -> tuple[AccessTokenResponse, str]:
        if refresh_token is None:
            raise AuthenticationError("Refresh token missing")
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid refresh token") from exc

        user_id = uuid.UUID(payload["sub"])
        user = user_repository.get_active_user_by_id(self.session, user_id)
        if user is None:
            raise AuthenticationError("User not found")
        return build_auth_response(user)

    def logout(self) -> LogoutResponse:
        return LogoutResponse(message="Logged out")

    def delete_account(self, current_user: User) -> DeleteAccountResponse:
        delete_user_account(self.session, current_user, self.event_publisher)
        return DeleteAccountResponse(message="Account deleted")

    @staticmethod
    def set_refresh_cookie(response, refresh_token: str) -> None:
        set_refresh_cookie(response, refresh_token)

    @staticmethod
    def clear_refresh_cookie(response) -> None:
        clear_refresh_cookie(response)
