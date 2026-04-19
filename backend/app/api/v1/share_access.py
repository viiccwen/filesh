from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.errors import to_http_exception
from app.application.dto import AuthenticatedUser
from app.application.use_cases.share_access import ShareAccessUseCase
from app.dependencies.auth import get_optional_current_user
from app.dependencies.use_cases import get_share_access_use_case
from app.domain import AppError
from app.schemas.file import FileRead
from app.schemas.folder import FolderCreateRequest, FolderRead
from app.schemas.share import ShareAccessResponse, SharedFolderContentsResponse

router = APIRouter()
optional_user_dependency = Depends(get_optional_current_user)
share_access_use_case_dependency = Depends(get_share_access_use_case)
shared_upload_file_dependency = File(...)
shared_upload_folder_dependency = Form()


@router.get("/s/{token}", response_model=ShareAccessResponse)
def access_share(
    token: str,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> ShareAccessResponse:
    try:
        return use_case.access_share(token, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/s/{token}/contents", response_model=SharedFolderContentsResponse)
def access_shared_folder_contents(
    token: str,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> SharedFolderContentsResponse:
    try:
        return use_case.shared_folder_contents(token, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/s/{token}/download")
def download_shared_file(
    token: str,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> StreamingResponse:
    try:
        data, media_type, filename = use_case.download_shared_file(token, current_user)
        return StreamingResponse(
            iter([data]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/s/{token}/folders/{folder_id}/contents", response_model=SharedFolderContentsResponse)
def access_nested_shared_folder_contents(
    token: str,
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> SharedFolderContentsResponse:
    try:
        return use_case.nested_folder_contents(token, folder_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/s/{token}/folders", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_shared_folder(
    token: str,
    payload: FolderCreateRequest,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> FolderRead:
    try:
        return use_case.create_shared_folder(token, payload, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/s/{token}/files", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def upload_shared_file(
    token: str,
    file: Annotated[UploadFile, shared_upload_file_dependency],
    folder_id: Annotated[uuid.UUID | None, shared_upload_folder_dependency] = None,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> FileRead:
    data = await file.read()
    try:
        return use_case.upload_shared_file(
            token,
            file.filename or "upload.bin",
            data,
            file.content_type,
            current_user,
            folder_id,
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/s/{token}/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shared_folder(
    token: str,
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> Response:
    try:
        use_case.delete_shared_folder(token, folder_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/s/{token}/files/{file_id}", response_model=FileRead)
def access_shared_file_metadata(
    token: str,
    file_id: uuid.UUID,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> FileRead:
    try:
        return use_case.shared_file_metadata(token, file_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/s/{token}/files/{file_id}/download")
def download_shared_file_from_folder(
    token: str,
    file_id: uuid.UUID,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> StreamingResponse:
    try:
        data, media_type, filename = use_case.download_shared_file_from_folder(
            token,
            file_id,
            current_user,
        )
        return StreamingResponse(
            iter([data]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/s/{token}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_shared_file(
    token: str,
    file_id: uuid.UUID,
    current_user: AuthenticatedUser | None = optional_user_dependency,
    use_case: ShareAccessUseCase = share_access_use_case_dependency,
) -> Response:
    try:
        use_case.delete_shared_file(token, file_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc
