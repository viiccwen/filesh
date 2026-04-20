from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.errors import to_http_exception
from app.application.types import AuthenticatedUser
from app.application.use_cases.files import FileUseCase
from app.dependencies.auth import get_current_user
from app.dependencies.use_cases import get_file_use_case
from app.domain import AppError
from app.schemas.file import (
    FileMoveRequest,
    FileRead,
    FileRenameRequest,
    UploadFailRequest,
    UploadFinalizeRequest,
    UploadInitRequest,
    UploadInitResponse,
)
from app.schemas.share import ShareRead, ShareUpsertRequest

router = APIRouter()
current_user_dependency = Depends(get_current_user)
file_use_case_dependency = Depends(get_file_use_case)


@router.post("/upload/init", response_model=UploadInitResponse, status_code=status.HTTP_201_CREATED)
def upload_init(
    payload: UploadInitRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> UploadInitResponse:
    try:
        return use_case.init_upload(current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/upload/finalize", response_model=FileRead)
def upload_finalize(
    payload: UploadFinalizeRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> FileRead:
    try:
        return use_case.finalize_upload(current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/upload/{upload_session_id}/content", status_code=status.HTTP_204_NO_CONTENT)
async def upload_content_object(
    upload_session_id: uuid.UUID,
    file: UploadFile,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> Response:
    data = await file.read()
    try:
        use_case.upload_content(upload_session_id, current_user, data, file.content_type)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/upload/fail", status_code=status.HTTP_204_NO_CONTENT)
def upload_fail(
    payload: UploadFailRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> Response:
    try:
        use_case.fail_upload(current_user, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{file_id}", response_model=FileRead)
def get_file(
    file_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> FileRead:
    try:
        return use_case.get(file_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{file_id}/download")
def download_file(
    file_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> StreamingResponse:
    try:
        data, media_type, filename = use_case.download(file_id, current_user)
        return StreamingResponse(
            iter([data]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_file(
    file_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> Response:
    try:
        use_case.delete(file_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{file_id}", response_model=FileRead)
def rename_file(
    file_id: uuid.UUID,
    payload: FileRenameRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> FileRead:
    try:
        return use_case.rename(file_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{file_id}/move", response_model=FileRead)
def move_file(
    file_id: uuid.UUID,
    payload: FileMoveRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> FileRead:
    try:
        return use_case.move(file_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{file_id}/share", response_model=ShareRead)
def get_file_share(
    file_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> ShareRead:
    try:
        return use_case.get_share(file_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/{file_id}/share", response_model=ShareRead, status_code=status.HTTP_201_CREATED)
def create_file_share(
    file_id: uuid.UUID,
    payload: ShareUpsertRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> ShareRead:
    try:
        return use_case.create_share(file_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{file_id}/share", response_model=ShareRead)
def update_file_share(
    file_id: uuid.UUID,
    payload: ShareUpsertRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> ShareRead:
    try:
        return use_case.update_share(file_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/{file_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_share(
    file_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FileUseCase = file_use_case_dependency,
) -> Response:
    try:
        use_case.revoke_share(file_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc
