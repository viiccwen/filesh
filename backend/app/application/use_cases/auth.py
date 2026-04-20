from __future__ import annotations

from fastapi import Response

from app.application.ports import EventPublisherPort, UnitOfWorkPort
from app.application.services import identity
from app.application.services.folders import create_root_folder
from app.application.types import AuthenticatedUser
from app.application.use_cases.base import UseCaseBase
from app.core.config import settings
from app.core.events import CleanupEventType, build_cleanup_event
from app.core.security import clear_refresh_cookie, set_refresh_cookie
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteAccountResponse,
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
)
from app.schemas.user import UserRead


class AuthUseCase(UseCaseBase):
    def __init__(self, uow: UnitOfWorkPort, event_publisher: EventPublisherPort) -> None:
        super().__init__(uow)
        self.event_publisher = event_publisher

    def register(self, payload: RegisterRequest) -> UserRead:
        def operation():
            user = identity.register_user(self.uow, payload)
            create_root_folder(self.uow, user.id)
            return user

        user = self.in_transaction(operation, refresh=None)
        self.uow.refresh(user)
        return identity.to_user_read(user)

    def login(self, payload: LoginRequest) -> tuple[AccessTokenResponse, str]:
        user = identity.authenticate_user(self.uow, payload.identifier, payload.password)
        access_token, refresh_token = identity.build_auth_tokens(user)
        return (
            AccessTokenResponse(
                access_token=access_token,
                user=identity.to_user_read(user),
            ),
            refresh_token,
        )

    def refresh_access_token(self, refresh_token: str | None) -> tuple[AccessTokenResponse, str]:
        user = identity.resolve_refresh_user(self.uow, refresh_token)
        access_token, next_refresh_token = identity.build_auth_tokens(user)
        return (
            AccessTokenResponse(access_token=access_token, user=identity.to_user_read(user)),
            next_refresh_token,
        )

    def logout(self) -> LogoutResponse:
        return LogoutResponse(message="Logged out")

    def change_password(
        self,
        current_user: AuthenticatedUser,
        payload: ChangePasswordRequest,
    ) -> ChangePasswordResponse:
        def operation():
            user = identity.require_active_user(self.uow, current_user.id)
            identity.change_user_password(user, payload)
            return user

        self.in_transaction(operation)
        return ChangePasswordResponse(message="Password updated")

    def delete_account(self, current_user: AuthenticatedUser) -> DeleteAccountResponse:
        def operation():
            user = identity.get_active_user(self.uow, current_user.id)
            objects = [
                {"bucket": file.storage_bucket, "object_key": file.object_key}
                for file in user.files
            ]
            event = build_cleanup_event(
                CleanupEventType.ACCOUNT_DELETE_REQUESTED,
                resource={"type": "user", "id": str(user.id)},
                objects=objects,
                metadata={"email": user.email, "username": user.username},
            )
            self.uow.delete(user)
            return event, str(user.id)

        event, event_key = self.in_transaction(operation)
        self.event_publisher.publish(settings.kafka_cleanup_topic, event_key, event)
        return DeleteAccountResponse(message="Account deleted")

    @staticmethod
    def set_refresh_cookie(response: Response, refresh_token: str) -> None:
        set_refresh_cookie(response, refresh_token)

    @staticmethod
    def clear_refresh_cookie(response: Response) -> None:
        clear_refresh_cookie(response)
