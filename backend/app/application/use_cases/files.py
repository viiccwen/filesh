from __future__ import annotations

import uuid

from app.application.mappers import to_upload_init_response
from app.application.ports import EventPublisherPort, ObjectStoragePort, UnitOfWorkPort
from app.application.services import files as file_service
from app.application.services import shares as share_service
from app.application.types import AuthenticatedUser
from app.application.use_cases.base import UseCaseBase
from app.core.config import settings
from app.core.events import CleanupEventType, build_cleanup_event
from app.domain.enums import ResourceType
from app.schemas.file import (
    FileMoveRequest,
    FileRead,
    FileRenameRequest,
    UploadFailRequest,
    UploadFinalizeRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from app.schemas.share import ShareRead, ShareUpsertRequest


class FileUseCase(UseCaseBase):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        object_storage: ObjectStoragePort,
        event_publisher: EventPublisherPort,
    ) -> None:
        super().__init__(uow)
        self.object_storage = object_storage
        self.event_publisher = event_publisher

    def init_upload(
        self,
        current_user: AuthenticatedUser,
        payload: UploadInitRequest,
    ) -> UploadInitResponse:
        upload_session = self.in_transaction(
            lambda: file_service.init_upload(self.uow, current_user.id, payload)
        )
        self.uow.refresh(upload_session)
        return to_upload_init_response(upload_session)

    def finalize_upload(
        self,
        current_user: AuthenticatedUser,
        payload: UploadFinalizeRequest,
    ) -> FileRead:
        file = self.in_transaction(
            lambda: file_service.finalize_upload(self.uow, current_user.id, payload)
        )
        self.uow.refresh(file)
        return FileRead.model_validate(file)

    def upload_content(
        self,
        upload_session_id: uuid.UUID,
        current_user: AuthenticatedUser,
        data: bytes,
        content_type: str | None,
    ) -> None:
        self.in_transaction(
            lambda: file_service.upload_content(
                self.uow,
                current_user.id,
                upload_session_id,
                data,
                content_type,
                self.object_storage,
            )
        )

    def fail_upload(self, current_user: AuthenticatedUser, payload: UploadFailRequest) -> None:
        def operation():
            upload_session = file_service.fail_upload(self.uow, current_user.id, payload)
            event = build_cleanup_event(
                CleanupEventType.UPLOAD_FAILED,
                resource={"type": "upload_session", "id": str(upload_session.id)},
                objects=[
                    {
                        "bucket": settings.minio_bucket,
                        "object_key": upload_session.object_key,
                    }
                ],
                metadata={"owner_id": str(upload_session.owner_id)},
            )
            return upload_session, event

        upload_session, event = self.in_transaction(operation)
        self.event_publisher.publish(settings.kafka_cleanup_topic, str(upload_session.id), event)

    def get(self, file_id: uuid.UUID, current_user: AuthenticatedUser) -> FileRead:
        file = file_service.get_file_for_owner(self.uow, file_id, current_user.id)
        return FileRead.model_validate(file)

    def download(
        self,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> tuple[bytes, str, str]:
        file = file_service.get_file_for_owner(self.uow, file_id, current_user.id)
        data = file_service.download_file_content(self.object_storage, file)
        return data, (file.content_type or "application/octet-stream"), file.stored_filename

    def delete(self, file_id: uuid.UUID, current_user: AuthenticatedUser) -> None:
        def operation():
            file = file_service.prepare_file_delete(self.uow, file_id, current_user.id)
            event = build_cleanup_event(
                CleanupEventType.FILE_DELETE_REQUESTED,
                resource={"type": "file", "id": str(file.id)},
                objects=[{"bucket": file.storage_bucket, "object_key": file.object_key}],
                metadata={"owner_id": str(current_user.id)},
            )
            file_service.delete_file_record(self.uow, file)
            return file.id, event

        file_id_value, event = self.in_transaction(operation)
        self.event_publisher.publish(settings.kafka_cleanup_topic, str(file_id_value), event)

    def rename(
        self,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: FileRenameRequest,
    ) -> FileRead:
        file = self.in_transaction(
            lambda: file_service.rename_file(self.uow, file_id, current_user.id, payload.filename)
        )
        self.uow.refresh(file)
        return FileRead.model_validate(file)

    def move(
        self,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: FileMoveRequest,
    ) -> FileRead:
        file = self.in_transaction(
            lambda: file_service.move_file(
                self.uow, file_id, current_user.id, payload.target_folder_id
            )
        )
        self.uow.refresh(file)
        return FileRead.model_validate(file)

    def get_share(self, file_id: uuid.UUID, current_user: AuthenticatedUser) -> ShareRead:
        return share_service.get_share(self.uow, current_user, ResourceType.FILE, file_id)

    def create_share(
        self,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return self.in_transaction(
            lambda: share_service.create_share(
                self.uow, current_user, ResourceType.FILE, file_id, payload
            )
        )

    def update_share(
        self,
        file_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return self.in_transaction(
            lambda: share_service.update_share(
                self.uow, current_user, ResourceType.FILE, file_id, payload
            )
        )

    def revoke_share(self, file_id: uuid.UUID, current_user: AuthenticatedUser) -> None:
        self.in_transaction(
            lambda: share_service.revoke_share(self.uow, current_user, ResourceType.FILE, file_id)
        )
