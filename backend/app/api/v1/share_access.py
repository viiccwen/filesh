from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.core.events import EventPublisher
from app.core.storage import ObjectStorage
from app.dependencies.auth import get_optional_current_user
from app.dependencies.events import get_event_publisher
from app.dependencies.storage import get_object_storage
from app.models import PermissionLevel, ResourceType, User
from app.schemas.file import FileRead, FileSummary
from app.schemas.folder import FolderContentsResponse, FolderCreateRequest, FolderRead
from app.schemas.share import ShareAccessResponse, SharedFolderContentsResponse
from app.services.files import delete_file, download_file_content
from app.services.folders import delete_folder
from app.services.shares import (
    authorize_share_permission,
    create_shared_subfolder,
    get_shared_folder_contents_for_target,
    get_shared_folder_target,
    get_shared_resource,
    resolve_share_by_token,
    resolve_shared_file_action,
)

router = APIRouter()
db_session_dependency = Depends(get_db_session)
optional_user_dependency = Depends(get_optional_current_user)
object_storage_dependency = Depends(get_object_storage)
event_publisher_dependency = Depends(get_event_publisher)


@router.get("/s/{token}", response_model=ShareAccessResponse)
def access_share(
    token: str,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
) -> ShareAccessResponse:
    share_link = resolve_share_by_token(session, token)
    authorize_share_permission(share_link, current_user, PermissionLevel.VIEW_DOWNLOAD)
    resource = get_shared_resource(session, share_link)

    if share_link.resource_type is ResourceType.FILE:
        return ShareAccessResponse(
            resource_type=share_link.resource_type,
            share_mode=share_link.share_mode,
            permission_level=share_link.permission_level,
            expires_at=share_link.expires_at,
            file=FileRead.model_validate(resource),
        )

    return ShareAccessResponse(
        resource_type=share_link.resource_type,
        share_mode=share_link.share_mode,
        permission_level=share_link.permission_level,
        expires_at=share_link.expires_at,
        folder=FolderRead.model_validate(resource),
    )


@router.get("/s/{token}/contents", response_model=SharedFolderContentsResponse)
def access_shared_folder_contents(
    token: str,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
) -> SharedFolderContentsResponse:
    share_link = resolve_share_by_token(session, token)
    folder, folders, files = get_shared_folder_contents_for_target(
        session,
        share_link,
        current_user,
    )
    return SharedFolderContentsResponse(
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
        permission_level=share_link.permission_level,
    )


@router.get("/s/{token}/download")
def download_shared_file(
    token: str,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
) -> StreamingResponse:
    share_link = resolve_share_by_token(session, token)
    authorize_share_permission(share_link, current_user, PermissionLevel.VIEW_DOWNLOAD)
    if share_link.resource_type is not ResourceType.FILE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct download is only available for file shares",
        )
    file = get_shared_resource(session, share_link)
    data = download_file_content(object_storage, file)
    return StreamingResponse(
        iter([data]),
        media_type=file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.stored_filename}"'},
    )


@router.get("/s/{token}/folders/{folder_id}/contents", response_model=FolderContentsResponse)
def access_nested_shared_folder_contents(
    token: str,
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
) -> FolderContentsResponse:
    share_link = resolve_share_by_token(session, token)
    folder, folders, files = get_shared_folder_contents_for_target(
        session,
        share_link,
        current_user,
        folder_id,
    )
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


@router.post("/s/{token}/folders", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_shared_folder(
    token: str,
    payload: FolderCreateRequest,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
) -> FolderRead:
    share_link = resolve_share_by_token(session, token)
    folder = create_shared_subfolder(session, share_link, current_user, payload)
    return FolderRead.model_validate(folder)


@router.delete("/s/{token}/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shared_folder(
    token: str,
    folder_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> Response:
    share_link = resolve_share_by_token(session, token)
    authorize_share_permission(share_link, current_user, PermissionLevel.DELETE)
    delete_target = get_shared_folder_target(session, share_link, folder_id)
    delete_folder(session, delete_target.id, share_link.owner_id, event_publisher)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/s/{token}/files/{file_id}", response_model=FileRead)
def access_shared_file_metadata(
    token: str,
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
) -> FileRead:
    share_link = resolve_share_by_token(session, token)
    file, _ = resolve_shared_file_action(
        session,
        share_link,
        file_id,
        current_user,
        PermissionLevel.VIEW_DOWNLOAD,
    )
    return FileRead.model_validate(file)


@router.get("/s/{token}/files/{file_id}/download")
def download_shared_file_from_folder(
    token: str,
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
) -> StreamingResponse:
    share_link = resolve_share_by_token(session, token)
    file, _ = resolve_shared_file_action(
        session,
        share_link,
        file_id,
        current_user,
        PermissionLevel.VIEW_DOWNLOAD,
    )
    data = download_file_content(object_storage, file)
    return StreamingResponse(
        iter([data]),
        media_type=file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.stored_filename}"'},
    )


@router.delete("/s/{token}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shared_file(
    token: str,
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> Response:
    share_link = resolve_share_by_token(session, token)
    file, _ = resolve_shared_file_action(
        session,
        share_link,
        file_id,
        current_user,
        PermissionLevel.DELETE,
    )
    delete_file(session, file.id, file.owner_id, event_publisher)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
