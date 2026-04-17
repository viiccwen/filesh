from __future__ import annotations

import uuid

from app.application.shared.files import delete_file, download_file_content
from app.application.shared.folders import delete_folder
from app.application.shared.presenters import (
    to_folder_contents_response,
    to_share_access_response,
    to_shared_folder_contents_response,
)
from app.application.shared.shares import (
    authorize_share_permission,
    create_shared_file,
    create_shared_subfolder,
    get_shared_folder_contents_for_target,
    get_shared_folder_target,
    get_shared_resource,
    resolve_share_by_token,
    resolve_shared_file_action,
)
from app.core.events import EventPublisher
from app.core.storage import ObjectStorage
from app.models import PermissionLevel, ResourceType, User
from app.schemas.file import FileRead
from app.schemas.folder import FolderContentsResponse, FolderCreateRequest, FolderRead
from app.schemas.share import ShareAccessResponse, SharedFolderContentsResponse


class ShareAccessUseCase:
    def __init__(
        self,
        session,
        object_storage: ObjectStorage,
        event_publisher: EventPublisher,
    ) -> None:
        self.session = session
        self.object_storage = object_storage
        self.event_publisher = event_publisher

    def access_share(self, token: str, current_user: User | None) -> ShareAccessResponse:
        share_link = resolve_share_by_token(self.session, token)
        authorize_share_permission(share_link, current_user, PermissionLevel.VIEW_DOWNLOAD)
        resource = get_shared_resource(self.session, share_link)
        return to_share_access_response(share_link, resource)

    def shared_folder_contents(
        self,
        token: str,
        current_user: User | None,
    ) -> SharedFolderContentsResponse:
        share_link = resolve_share_by_token(self.session, token)
        folder, folders, files = get_shared_folder_contents_for_target(
            self.session,
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
        current_user: User | None,
    ) -> tuple[bytes, str, str]:
        share_link = resolve_share_by_token(self.session, token)
        authorize_share_permission(share_link, current_user, PermissionLevel.VIEW_DOWNLOAD)
        if share_link.resource_type is not ResourceType.FILE:
            from app.domain import ValidationError

            raise ValidationError("Direct download is only available for file shares")
        file = get_shared_resource(self.session, share_link)
        data = download_file_content(self.object_storage, file)
        return data, (file.content_type or "application/octet-stream"), file.stored_filename

    def nested_folder_contents(
        self,
        token: str,
        folder_id: uuid.UUID,
        current_user: User | None,
    ) -> FolderContentsResponse:
        share_link = resolve_share_by_token(self.session, token)
        folder, folders, files = get_shared_folder_contents_for_target(
            self.session,
            share_link,
            current_user,
            folder_id,
        )
        return to_folder_contents_response(folder, folders, files)

    def create_shared_folder(
        self,
        token: str,
        payload: FolderCreateRequest,
        current_user: User | None,
    ) -> FolderRead:
        share_link = resolve_share_by_token(self.session, token)
        folder = create_shared_subfolder(self.session, share_link, current_user, payload)
        return FolderRead.model_validate(folder)

    def upload_shared_file(
        self,
        token: str,
        filename: str,
        data: bytes,
        content_type: str | None,
        current_user: User | None,
        folder_id: uuid.UUID | None = None,
    ) -> FileRead:
        share_link = resolve_share_by_token(self.session, token)
        file = create_shared_file(
            self.session,
            share_link,
            current_user,
            filename,
            data,
            content_type,
            self.object_storage,
            folder_id,
        )
        return FileRead.model_validate(file)

    def delete_shared_folder(
        self,
        token: str,
        folder_id: uuid.UUID,
        current_user: User | None,
    ) -> None:
        share_link = resolve_share_by_token(self.session, token)
        authorize_share_permission(share_link, current_user, PermissionLevel.DELETE)
        delete_target = get_shared_folder_target(self.session, share_link, folder_id)
        delete_folder(self.session, delete_target.id, share_link.owner_id, self.event_publisher)

    def shared_file_metadata(
        self,
        token: str,
        file_id: uuid.UUID,
        current_user: User | None,
    ) -> FileRead:
        share_link = resolve_share_by_token(self.session, token)
        file, _ = resolve_shared_file_action(
            self.session,
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
        current_user: User | None,
    ) -> tuple[bytes, str, str]:
        share_link = resolve_share_by_token(self.session, token)
        file, _ = resolve_shared_file_action(
            self.session,
            share_link,
            file_id,
            current_user,
            PermissionLevel.VIEW_DOWNLOAD,
        )
        data = download_file_content(self.object_storage, file)
        return data, (file.content_type or "application/octet-stream"), file.stored_filename

    def delete_shared_file(
        self,
        token: str,
        file_id: uuid.UUID,
        current_user: User | None,
    ) -> None:
        share_link = resolve_share_by_token(self.session, token)
        file, _ = resolve_shared_file_action(
            self.session,
            share_link,
            file_id,
            current_user,
            PermissionLevel.DELETE,
        )
        delete_file(self.session, file.id, file.owner_id, self.event_publisher)
