from __future__ import annotations

import uuid

from app.application.dto import AuthenticatedUser, FolderContentsDTO, FolderDTO, ShareReadDTO
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
from app.domain.enums import ResourceType
from app.schemas.folder import (
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRenameRequest,
)
from app.schemas.share import ShareUpsertRequest


class FolderUseCase:
    def __init__(self, session, event_publisher: EventPublisher) -> None:
        self.session = session
        self.event_publisher = event_publisher

    def get_root(self, current_user: AuthenticatedUser) -> FolderDTO:
        folder = get_or_create_root_folder(self.session, current_user.id)
        return FolderDTO.model_validate(folder)

    def create(self, current_user: AuthenticatedUser, payload: FolderCreateRequest) -> FolderDTO:
        folder = create_folder(self.session, current_user.id, payload)
        return FolderDTO.model_validate(folder)

    def get(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> FolderDTO:
        folder = get_folder_for_owner(self.session, folder_id, current_user.id)
        return FolderDTO.model_validate(folder)

    def contents(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> FolderContentsDTO:
        folder, folders, files = list_folder_contents(self.session, folder_id, current_user.id)
        return to_folder_contents_response(folder, folders, files)

    def delete(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> None:
        delete_folder(self.session, folder_id, current_user.id, self.event_publisher)

    def rename(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: FolderRenameRequest,
    ) -> FolderDTO:
        folder = rename_folder(self.session, folder_id, current_user.id, payload.name)
        return FolderDTO.model_validate(folder)

    def move(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: FolderMoveRequest,
    ) -> FolderDTO:
        folder = move_folder(self.session, folder_id, current_user.id, payload.target_parent_id)
        return FolderDTO.model_validate(folder)

    def get_share(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> ShareReadDTO:
        return get_share(self.session, current_user, ResourceType.FOLDER, folder_id)

    def create_share(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: ShareUpsertRequest,
    ) -> ShareReadDTO:
        return create_share(self.session, current_user, ResourceType.FOLDER, folder_id, payload)

    def update_share(
        self,
        folder_id: uuid.UUID,
        current_user: AuthenticatedUser,
        payload: ShareUpsertRequest,
    ) -> ShareReadDTO:
        return update_share(self.session, current_user, ResourceType.FOLDER, folder_id, payload)

    def revoke_share(self, folder_id: uuid.UUID, current_user: AuthenticatedUser) -> None:
        revoke_share(self.session, current_user, ResourceType.FOLDER, folder_id)
