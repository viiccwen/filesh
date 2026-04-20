from __future__ import annotations

import uuid

from app.application.mappers import to_folder_contents_response
from app.application.ports import EventPublisherPort, UnitOfWorkPort
from app.application.services import folders as folder_service
from app.application.services import shares as share_service
from app.application.types import AuthenticatedUser
from app.application.use_cases.base import UseCaseBase
from app.core.config import settings
from app.core.events import CleanupEventType, build_cleanup_event
from app.domain.enums import ResourceType
from app.schemas.folder import (
    FolderContentsResponse,
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRead,
    FolderRenameRequest,
)
from app.schemas.share import ShareRead, ShareUpsertRequest


class FolderUseCase(UseCaseBase):
    def __init__(self, uow: UnitOfWorkPort, event_publisher: EventPublisherPort) -> None:
        super().__init__(uow)
        self.event_publisher = event_publisher

    def get_root(self, current_user: AuthenticatedUser) -> FolderRead:
        folder, created = folder_service.get_or_create_root_folder(self.uow, current_user.id)
        if created:
            self.in_transaction(lambda: None)
            self.uow.refresh(folder)
        return FolderRead.model_validate(folder)

    def create(self, current_user: AuthenticatedUser, payload: FolderCreateRequest) -> FolderRead:
        folder = self.in_transaction(
            lambda: folder_service.create_folder(self.uow, current_user.id, payload)
        )
        self.uow.refresh(folder)
        return FolderRead.model_validate(folder)

    def get(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> FolderRead:
        folder = folder_service.get_folder_for_owner(self.uow, folder_id, current_user.id)
        return FolderRead.model_validate(folder)

    def contents(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> FolderContentsResponse:
        folder, folders, files = folder_service.list_folder_contents(
            self.uow,
            folder_id,
            current_user.id,
        )
        return to_folder_contents_response(folder, folders, files)

    def delete(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> None:
        def operation():
            folder, files_to_cleanup, folder_ids = folder_service.prepare_folder_delete(
                self.uow,
                folder_id,
                current_user.id,
            )
            event = build_cleanup_event(
                CleanupEventType.FOLDER_DELETE_REQUESTED,
                resource={"type": "folder", "id": str(folder.id)},
                objects=[
                    {"bucket": file.storage_bucket, "object_key": file.object_key}
                    for file in files_to_cleanup
                ],
                metadata={"owner_id": str(current_user.id)},
            )
            folder_service.delete_folder_tree(self.uow, folder, folder_ids)
            return folder.id, event

        folder_id_value, event = self.in_transaction(operation)
        self.event_publisher.publish(settings.kafka_cleanup_topic, str(folder_id_value), event)

    def rename(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: FolderRenameRequest,
    ) -> FolderRead:
        folder = self.in_transaction(
            lambda: folder_service.rename_folder(self.uow, folder_id, current_user.id, payload.name)
        )
        self.uow.refresh(folder)
        return FolderRead.model_validate(folder)

    def move(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: FolderMoveRequest,
    ) -> FolderRead:
        folder = self.in_transaction(
            lambda: folder_service.move_folder(
                self.uow,
                folder_id,
                current_user.id,
                payload.target_parent_id,
            )
        )
        self.uow.refresh(folder)
        return FolderRead.model_validate(folder)

    def get_share(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> ShareRead:
        return share_service.get_share(self.uow, current_user, ResourceType.FOLDER, folder_id)

    def create_share(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return self.in_transaction(
            lambda: share_service.create_share(
                self.uow,
                current_user,
                ResourceType.FOLDER,
                folder_id,
                payload,
            )
        )

    def update_share(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return self.in_transaction(
            lambda: share_service.update_share(
                self.uow,
                current_user,
                ResourceType.FOLDER,
                folder_id,
                payload,
            )
        )

    def revoke_share(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> None:
        self.in_transaction(
            lambda: share_service.revoke_share(
                self.uow,
                current_user,
                ResourceType.FOLDER,
                folder_id,
            )
        )
