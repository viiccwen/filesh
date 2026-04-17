from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.core.events import EventPublisher
from app.dependencies.auth import get_current_user
from app.dependencies.events import get_event_publisher
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

router = APIRouter()
db_session_dependency = Depends(get_db_session)
current_user_dependency = Depends(get_current_user)
event_publisher_dependency = Depends(get_event_publisher)


@router.get("/root", response_model=FolderRead)
def get_root(
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> FolderRead:
    folder = get_or_create_root_folder(session, current_user)
    return FolderRead.model_validate(folder)


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: FolderCreateRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> FolderRead:
    folder = create_folder(session, current_user, payload)
    return FolderRead.model_validate(folder)


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> FolderRead:
    folder = get_folder_for_owner(session, folder_id, current_user.id)
    return FolderRead.model_validate(folder)


@router.get("/{folder_id}/contents", response_model=FolderContentsResponse)
def get_contents(
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> FolderContentsResponse:
    folder, folders, files = list_folder_contents(session, folder_id, current_user.id)
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


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_folder(
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> Response:
    delete_folder(session, folder_id, current_user.id, event_publisher)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{folder_id}/share", response_model=ShareRead)
def get_folder_share(
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> ShareRead:
    return get_share(session, current_user, ResourceType.FOLDER, folder_id)


@router.post("/{folder_id}/share", response_model=ShareRead, status_code=status.HTTP_201_CREATED)
def create_folder_share(
    folder_id: uuid.UUID,
    payload: ShareUpsertRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> ShareRead:
    return create_share(session, current_user, ResourceType.FOLDER, folder_id, payload)


@router.patch("/{folder_id}/share", response_model=ShareRead)
def update_folder_share(
    folder_id: uuid.UUID,
    payload: ShareUpsertRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> ShareRead:
    return update_share(session, current_user, ResourceType.FOLDER, folder_id, payload)


@router.delete("/{folder_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder_share(
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> Response:
    revoke_share(session, current_user, ResourceType.FOLDER, folder_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
