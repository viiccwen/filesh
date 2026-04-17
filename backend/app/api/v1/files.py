from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.file import (
    FileRead,
    UploadFailRequest,
    UploadFinalizeRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services.files import (
    delete_file,
    fail_upload,
    finalize_upload,
    get_file_for_owner,
    init_upload,
)

router = APIRouter()
db_session_dependency = Depends(get_db_session)
current_user_dependency = Depends(get_current_user)


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


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_file(
    file_id: uuid.UUID,
    session: Session = db_session_dependency,
    current_user: User = current_user_dependency,
) -> Response:
    delete_file(session, file_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
