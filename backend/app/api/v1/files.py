from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.core.storage import ObjectStorage
from app.dependencies.auth import get_current_user
from app.dependencies.storage import get_object_storage
from app.models import ResourceType, User
from app.schemas.file import (
    FileRead,
    UploadFailRequest,
    UploadFinalizeRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from app.schemas.share import ShareRead, ShareUpsertRequest
from app.services.files import (
    delete_file,
    download_file_content,
    fail_upload,
    finalize_upload,
    get_file_for_owner,
    init_upload,
    upload_content,
)
from app.services.shares import create_share, get_share, revoke_share, update_share

router = APIRouter()
db_session_dependency = Depends(get_db_session)
current_user_dependency = Depends(get_current_user)
object_storage_dependency = Depends(get_object_storage)


@router.post("/upload/init", response_model=UploadInitResponse, status_code=status.HTTP_201_CREATED)
def upload_init(
    payload: UploadInitRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> UploadInitResponse:
    upload_session = init_upload(session, current_user, payload)
    return UploadInitResponse(
        session_id=upload_session.id,
        resolved_filename=upload_session.resolved_filename,
        object_key=upload_session.object_key,
        status=upload_session.status,
    )


@router.post("/upload/finalize", response_model=FileRead)
def upload_finalize(
    payload: UploadFinalizeRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> FileRead:
    file = finalize_upload(session, current_user, payload)
    return FileRead.model_validate(file)


@router.post("/upload/{upload_session_id}/content", status_code=status.HTTP_204_NO_CONTENT)
async def upload_content_object(
    upload_session_id: uuid.UUID,
    file: UploadFile,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
) -> Response:
    data = await file.read()
    upload_content(
        session,
        current_user,
        upload_session_id,
        data,
        file.content_type,
        object_storage,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/upload/fail", status_code=status.HTTP_204_NO_CONTENT)
def upload_fail(
    payload: UploadFailRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> Response:
    fail_upload(session, current_user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{file_id}", response_model=FileRead)
def get_file(
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> FileRead:
    file = get_file_for_owner(session, file_id, current_user.id)
    return FileRead.model_validate(file)


@router.get("/{file_id}/download")
def download_file(
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
) -> StreamingResponse:
    file = get_file_for_owner(session, file_id, current_user.id)
    data = download_file_content(object_storage, file)
    return StreamingResponse(
        iter([data]),
        media_type=file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file.stored_filename}"'},
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_file(
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
) -> Response:
    delete_file(session, file_id, current_user.id, object_storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{file_id}/share", response_model=ShareRead)
def get_file_share(
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> ShareRead:
    return get_share(session, current_user, ResourceType.FILE, file_id)


@router.post("/{file_id}/share", response_model=ShareRead, status_code=status.HTTP_201_CREATED)
def create_file_share(
    file_id: uuid.UUID,
    payload: ShareUpsertRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> ShareRead:
    return create_share(session, current_user, ResourceType.FILE, file_id, payload)


@router.patch("/{file_id}/share", response_model=ShareRead)
def update_file_share(
    file_id: uuid.UUID,
    payload: ShareUpsertRequest,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> ShareRead:
    return update_share(session, current_user, ResourceType.FILE, file_id, payload)


@router.delete("/{file_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_share(
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> Response:
    revoke_share(session, current_user, ResourceType.FILE, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
