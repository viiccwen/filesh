from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.errors import to_http_exception
from app.application.dto import AuthenticatedUser
from app.application.use_cases.folders import FolderUseCase
from app.dependencies.auth import get_current_user
from app.dependencies.use_cases import get_folder_use_case
from app.domain import AppError
from app.schemas.folder import (
    FolderContentsResponse,
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRead,
    FolderRenameRequest,
)
from app.schemas.share import ShareRead, ShareUpsertRequest

router = APIRouter()
current_user_dependency = Depends(get_current_user)
folder_use_case_dependency = Depends(get_folder_use_case)


@router.get("/root", response_model=FolderRead)
def get_root(
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> FolderRead:
    try:
        return use_case.get_root(current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: FolderCreateRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> FolderRead:
    try:
        return use_case.create(current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> FolderRead:
    try:
        return use_case.get(folder_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{folder_id}/contents", response_model=FolderContentsResponse)
def get_contents(
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> FolderContentsResponse:
    try:
        return use_case.contents(folder_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_folder(
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> Response:
    try:
        use_case.delete(folder_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{folder_id}", response_model=FolderRead)
def rename(
    folder_id: uuid.UUID,
    payload: FolderRenameRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> FolderRead:
    try:
        return use_case.rename(folder_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{folder_id}/move", response_model=FolderRead)
def move(
    folder_id: uuid.UUID,
    payload: FolderMoveRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> FolderRead:
    try:
        return use_case.move(folder_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.get("/{folder_id}/share", response_model=ShareRead)
def get_folder_share(
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> ShareRead:
    try:
        return use_case.get_share(folder_id, current_user)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.post("/{folder_id}/share", response_model=ShareRead, status_code=status.HTTP_201_CREATED)
def create_folder_share(
    folder_id: uuid.UUID,
    payload: ShareUpsertRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> ShareRead:
    try:
        return use_case.create_share(folder_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.patch("/{folder_id}/share", response_model=ShareRead)
def update_folder_share(
    folder_id: uuid.UUID,
    payload: ShareUpsertRequest,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> ShareRead:
    try:
        return use_case.update_share(folder_id, current_user, payload)
    except AppError as exc:
        raise to_http_exception(exc) from exc


@router.delete("/{folder_id}/share", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder_share(
    folder_id: uuid.UUID,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: FolderUseCase = folder_use_case_dependency,
) -> Response:
    try:
        use_case.revoke_share(folder_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AppError as exc:
        raise to_http_exception(exc) from exc
