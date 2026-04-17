from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.dependencies.auth import get_optional_current_user
from app.models import ResourceType, User
from app.schemas.file import FileRead, FileSummary
from app.schemas.folder import FolderRead
from app.schemas.share import ShareAccessResponse, SharedFolderContentsResponse
from app.services.shares import (
    authorize_share_access,
    get_shared_folder_contents,
    get_shared_resource,
    resolve_share_by_token,
)

router = APIRouter()
db_session_dependency = Depends(get_db_session)
optional_user_dependency = Depends(get_optional_current_user)


@router.get("/s/{token}", response_model=ShareAccessResponse)
def access_share(
    token: str,
    session: Session = db_session_dependency,
    current_user: User | None = optional_user_dependency,
) -> ShareAccessResponse:
    share_link = resolve_share_by_token(session, token)
    authorize_share_access(share_link, current_user)
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
    authorize_share_access(share_link, current_user)
    folder, folders, files = get_shared_folder_contents(session, share_link)
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
