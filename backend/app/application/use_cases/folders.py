from __future__ import annotations

import uuid

from app.core.events import EventPublisher
from app.models import ResourceType, User
from app.schemas.file import FileSummary
from app.schemas.folder import FolderContentsResponse, FolderCreateRequest, FolderRead
from app.schemas.share import ShareRead, ShareUpsertRequest
from app.services.folders import (
    create_folder,
    delete_folder,
    get_folder_for_owner,
    get_or_create_root_folder,
    list_folder_contents,
)
from app.services.shares import create_share, get_share, revoke_share, update_share


class FolderUseCase:
    def __init__(self, session, event_publisher: EventPublisher) -> None:
        self.session = session
        self.event_publisher = event_publisher

    def get_root(self, current_user: User) -> FolderRead:
        folder = get_or_create_root_folder(self.session, current_user)
        return FolderRead.model_validate(folder)

    def create(self, current_user: User, payload: FolderCreateRequest) -> FolderRead:
        folder = create_folder(self.session, current_user, payload)
        return FolderRead.model_validate(folder)

    def get(self, folder_id: uuid.UUID, current_user: User) -> FolderRead:
        folder = get_folder_for_owner(self.session, folder_id, current_user.id)
        return FolderRead.model_validate(folder)

    def contents(self, folder_id: uuid.UUID, current_user: User) -> FolderContentsResponse:
        folder, folders, files = list_folder_contents(self.session, folder_id, current_user.id)
        return FolderContentsResponse(
            folder=FolderRead.model_validate(folder),
            folders=[FolderRead.model_validate(item) for item in folders],
            files=[
                FileSummary(
                    id=item.id,
                    stored_filename=item.stored_filename,
                    content_type=item.content_type,
                    size_bytes=item.size_bytes,
                    status=item.status,
                )
                for item in files
            ],
        )

    def delete(self, folder_id: uuid.UUID, current_user: User) -> None:
        delete_folder(self.session, folder_id, current_user.id, self.event_publisher)

    def get_share(self, folder_id: uuid.UUID, current_user: User) -> ShareRead:
        return get_share(self.session, current_user, ResourceType.FOLDER, folder_id)

    def create_share(
        self,
        folder_id: uuid.UUID,
        current_user: User,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return create_share(self.session, current_user, ResourceType.FOLDER, folder_id, payload)

    def update_share(
        self,
        folder_id: uuid.UUID,
        current_user: User,
        payload: ShareUpsertRequest,
    ) -> ShareRead:
        return update_share(self.session, current_user, ResourceType.FOLDER, folder_id, payload)

    def revoke_share(self, folder_id: uuid.UUID, current_user: User) -> None:
        revoke_share(self.session, current_user, ResourceType.FOLDER, folder_id)
