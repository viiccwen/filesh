from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.folder import FolderContentsResponse, FolderCreateRequest, FolderRead
from app.services.folders import (
    create_folder,
    delete_folder,
    get_folder_for_owner,
    get_or_create_root_folder,
    list_folder_contents,
)

router = APIRouter()
db_session_dependency = Depends(get_db_session)
current_user_dependency = Depends(get_current_user)


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
            {
                "id": item.id,
                "stored_filename": item.stored_filename,
                "content_type": item.content_type,
                "size_bytes": item.size_bytes,
                "status": item.status,
            }
            for item in files
        ],
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_folder(
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> Response:
    delete_folder(session, folder_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
