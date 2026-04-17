from __future__ import annotations

import uuid

from app.application.shared.folders import (
    create_folder,
    delete_folder,
    get_folder_for_owner,
    get_or_create_root_folder,
    list_folder_contents,
    move_folder,
    rename_folder,
)
from app.application.shared.presenters import to_folder_contents_response
from app.application.shared.shares import create_share, get_share, revoke_share, update_share
from app.core.events import EventPublisher
from app.models import ResourceType, User
from app.schemas.folder import (
    FolderContentsResponse,
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRead,
    FolderRenameRequest,
)
from app.schemas.share import ShareRead, ShareUpsertRequest


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
        return to_folder_contents_response(folder, folders, files)

    def delete(self, folder_id: uuid.UUID, current_user: User) -> None:
        delete_folder(self.session, folder_id, current_user.id, self.event_publisher)

    def rename(
        self,
        folder_id: uuid.UUID,
        current_user: User,
        payload: FolderRenameRequest,
    ) -> FolderRead:
        folder = rename_folder(self.session, folder_id, current_user.id, payload.name)
        return FolderRead.model_validate(folder)

    def move(
        self,
        folder_id: uuid.UUID,
        current_user: User,
        payload: FolderMoveRequest,
    ) -> FolderRead:
        folder = move_folder(self.session, folder_id, current_user.id, payload.target_parent_id)
        return FolderRead.model_validate(folder)

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
