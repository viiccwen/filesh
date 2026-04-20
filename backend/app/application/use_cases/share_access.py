from __future__ import annotations

import uuid

from app.application.mappers import (
    to_share_access_response,
    to_shared_folder_contents_response,
)
from app.application.ports import EventPublisherPort, ObjectStoragePort, UnitOfWorkPort
from app.application.services import files as file_service
from app.application.services import folders as folder_service
from app.application.services import shares as share_service
from app.application.types import AuthenticatedUser
from app.application.use_cases.base import UseCaseBase
from app.core.config import settings
from app.core.events import CleanupEventType, build_cleanup_event
from app.domain.enums import PermissionLevel, ResourceType
from app.schemas.file import FileRead
from app.schemas.folder import FolderCreateRequest, FolderRead
from app.schemas.share import ShareAccessResponse, SharedFolderContentsResponse


class ShareAccessUseCase(UseCaseBase):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        object_storage: ObjectStoragePort,
        event_publisher: EventPublisherPort,
    ) -> None:
        super().__init__(uow)
        self.object_storage = object_storage
        self.event_publisher = event_publisher

    def access_share(
        self,
        token: str,
        current_user: AuthenticatedUser | None,
    ) -> ShareAccessResponse:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        share_service.authorize_share_permission(
            share_link,
            current_user,
            PermissionLevel.VIEW_DOWNLOAD,
        )
        resource = share_service.get_shared_resource(self.uow, share_link)
        return to_share_access_response(share_link, resource)

    def shared_folder_contents(
        self,
        token: str,
        current_user: AuthenticatedUser | None,
    ) -> SharedFolderContentsResponse:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        folder, folders, files = share_service.get_shared_folder_contents_for_target(
            self.uow,
            share_link,
            current_user,
        )
        return to_shared_folder_contents_response(
            folder,
            folders,
            files,
            share_link.permission_level,
        )

    def download_shared_file(
        self,
        token: str,
        current_user: AuthenticatedUser | None,
    ) -> tuple[bytes, str, str]:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        share_service.authorize_share_permission(
            share_link,
            current_user,
            PermissionLevel.VIEW_DOWNLOAD,
        )
        if share_link.resource_type is not ResourceType.FILE:
            from app.domain import ValidationError

            raise ValidationError("Direct download is only available for file shares")
        file = share_service.get_shared_resource(self.uow, share_link)
        data = file_service.download_file_content(self.object_storage, file)
        return data, (file.content_type or "application/octet-stream"), file.stored_filename

    def nested_folder_contents(
        self,
        token: str,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser | None,
    ) -> SharedFolderContentsResponse:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        folder, folders, files = share_service.get_shared_folder_contents_for_target(
            self.uow,
            share_link,
            current_user,
            folder_id,
        )
        return to_shared_folder_contents_response(
            folder,
            folders,
            files,
            share_link.permission_level,
        )

    def create_shared_folder(
        self,
        token: str,
        payload: FolderCreateRequest,
        current_user: AuthenticatedUser | None,
    ) -> FolderRead:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        folder = self.in_transaction(
            lambda: share_service.create_shared_subfolder(
                self.uow,
                share_link,
                current_user,
                payload,
            )
        )
        self.uow.refresh(folder)
        return FolderRead.model_validate(folder)

    def upload_shared_file(
        self,
        token: str,
        filename: str,
        data: bytes,
        content_type: str | None,
        current_user: AuthenticatedUser | None,
        folder_id: uuid.UUID | None = None,
    ) -> FileRead:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        file = self.in_transaction(
            lambda: share_service.create_shared_file(
                self.uow,
                share_link,
                current_user,
                filename,
                data,
                content_type,
                self.object_storage,
                folder_id,
            )
        )
        self.uow.refresh(file)
        return FileRead.model_validate(file)

    def delete_shared_folder(
        self,
        token: str,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser | None,
    ) -> None:
        share_link = share_service.resolve_share_by_token(self.uow, token)

        def operation():
            share_service.authorize_share_permission(
                share_link,
                current_user,
                PermissionLevel.DELETE,
            )
            delete_target = share_service.get_shared_folder_target(
                self.uow,
                share_link,
                folder_id,
            )
            folder, files_to_cleanup, folder_ids = folder_service.prepare_folder_delete(
                self.uow,
                delete_target.id,
                share_link.owner_id,
            )
            event = build_cleanup_event(
                CleanupEventType.FOLDER_DELETE_REQUESTED,
                resource={"type": "folder", "id": str(folder.id)},
                objects=[
                    {"bucket": file.storage_bucket, "object_key": file.object_key}
                    for file in files_to_cleanup
                ],
                metadata={"owner_id": str(share_link.owner_id)},
            )
            folder_service.delete_folder_tree(self.uow, folder, folder_ids)
            return folder.id, event

        folder_id_value, event = self.in_transaction(operation)
        self.event_publisher.publish(settings.kafka_cleanup_topic, str(folder_id_value), event)

    def shared_file_metadata(
        self,
        token: str,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser | None,
    ) -> FileRead:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        file, _ = share_service.resolve_shared_file_action(
            self.uow,
            share_link,
            file_id,
            current_user,
            PermissionLevel.VIEW_DOWNLOAD,
        )
        return FileRead.model_validate(file)

    def download_shared_file_from_folder(
        self,
        token: str,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser | None,
    ) -> tuple[bytes, str, str]:
        share_link = share_service.resolve_share_by_token(self.uow, token)
        file, _ = share_service.resolve_shared_file_action(
            self.uow,
            share_link,
            file_id,
            current_user,
            PermissionLevel.VIEW_DOWNLOAD,
        )
        data = file_service.download_file_content(self.object_storage, file)
        return data, (file.content_type or "application/octet-stream"), file.stored_filename

    def delete_shared_file(
        self,
        token: str,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser | None,
    ) -> None:
        share_link = share_service.resolve_share_by_token(self.uow, token)

        def operation():
            file, _ = share_service.resolve_shared_file_action(
                self.uow,
                share_link,
                file_id,
                current_user,
                PermissionLevel.DELETE,
            )
            event = build_cleanup_event(
                CleanupEventType.FILE_DELETE_REQUESTED,
                resource={"type": "file", "id": str(file.id)},
                objects=[{"bucket": file.storage_bucket, "object_key": file.object_key}],
                metadata={"owner_id": str(file.owner_id)},
            )
            file_service.delete_file_record(self.uow, file)
            return file.id, event

        file_id_value, event = self.in_transaction(operation)
        self.event_publisher.publish(settings.kafka_cleanup_topic, str(file_id_value), event)
