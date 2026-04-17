from __future__ import annotations

import uuid

from app.application.shared.files import (
    delete_file,
    download_file_content,
    fail_upload,
    finalize_upload,
    get_file_for_owner,
    init_upload,
    move_file,
    rename_file,
    upload_content,
)
from app.application.shared.presenters import to_upload_init_response
from app.application.shared.shares import create_share, get_share, revoke_share, update_share
from app.core.events import EventPublisher
from app.core.storage import ObjectStorage
from app.models import ResourceType, User
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


class FileUseCase:
    def __init__(
        self,
        session,
        object_storage: ObjectStorage,
        event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.object_storage = object_storage
        self.event_publisher = event_publisher

    def init_upload(self, current_user: User, payload: UploadInitRequest) -> UploadInitResponse:
        upload_session = init_upload(self.session, current_user, payload)
        return to_upload_init_response(upload_session)

    def finalize_upload(self, current_user: User, payload: UploadFinalizeRequest) -> FileRead:
        file = finalize_upload(self.session, current_user, payload)
        return FileRead.model_validate(file)

    def upload_content(
        self,
        upload_session_id: uuid.UUID,
        current_user: User,
        data: bytes,
        content_type: str | None,
    ) -> None:
        upload_content(
            self.session,
            current_user,
            upload_session_id,
            data,
            content_type,
            self.object_storage,
        )

    def fail_upload(self, current_user: User, payload: UploadFailRequest) -> None:
        fail_upload(self.session, current_user, payload, self.event_publisher)

    def get(self, file_id: uuid.UUID, current_user: User) -> FileRead:
        file = get_file_for_owner(self.session, file_id, current_user.id)
        return FileRead.model_validate(file)

    def download(self, file_id: uuid.UUID, current_user: User) -> tuple[bytes, str, str]:
        file = get_file_for_owner(self.session, file_id, current_user.id)
        data = download_file_content(self.object_storage, file)
        return data, (file.content_type or "application/octet-stream"), file.stored_filename

    def delete(self, file_id: uuid.UUID, current_user: User) -> None:
        delete_file(self.session, file_id, current_user.id, self.event_publisher)

    def rename(
        self,
        file_id: uuid.UUID,
        current_user: User,
        payload: FileRenameRequest,
    ) -> FileRead:
        file = rename_file(self.session, file_id, current_user.id, payload.filename)
        return FileRead.model_validate(file)

    def move(
        self,
        file_id: uuid.UUID,
        current_user: User,
        payload: FileMoveRequest,
    ) -> FileRead:
        file = move_file(self.session, file_id, current_user.id, payload.target_folder_id)
        return FileRead.model_validate(file)

    def get_share(self, file_id: uuid.UUID, current_user: User) -> ShareRead:
        return get_share(self.session, current_user, ResourceType.FILE, file_id)

    def create_share(
        self,
        file_id: uuid.UUID,
        current_user: User,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return create_share(self.session, current_user, ResourceType.FILE, file_id, payload)

    def update_share(
        self,
        file_id: uuid.UUID,
        current_user: User,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return update_share(self.session, current_user, ResourceType.FILE, file_id, payload)

    def revoke_share(self, file_id: uuid.UUID, current_user: User) -> None:
        revoke_share(self.session, current_user, ResourceType.FILE, file_id)
