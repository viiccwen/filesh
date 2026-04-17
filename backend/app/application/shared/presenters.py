from __future__ import annotations

from app.models import File, Folder, ShareLink
from app.schemas.file import FileRead, FileSummary, UploadInitResponse
from app.schemas.folder import FolderContentsResponse, FolderRead
from app.schemas.share import (
    ShareAccessResponse,
    SharedFolderContentsResponse,
)


def to_upload_init_response(upload_session) -> UploadInitResponse:
    return UploadInitResponse(
        session_id=upload_session.id,
        resolved_filename=upload_session.resolved_filename,
        object_key=upload_session.object_key,
        status=upload_session.status,
    )


def to_file_summary(file: File) -> FileSummary:
    return FileSummary(
        id=file.id,
        stored_filename=file.stored_filename,
        content_type=file.content_type,
        size_bytes=file.size_bytes,
        status=file.status,
    )


def to_folder_contents_response(
    folder: Folder,
    folders: list[Folder],
    files: list[File],
) -> FolderContentsResponse:
    return FolderContentsResponse(
        folder=FolderRead.model_validate(folder),
        folders=[FolderRead.model_validate(item) for item in folders],
        files=[to_file_summary(item) for item in files],
    )


def to_shared_folder_contents_response(
    folder: Folder,
    folders: list[Folder],
    files: list[File],
    permission_level,
) -> SharedFolderContentsResponse:
    return SharedFolderContentsResponse(
        folder=FolderRead.model_validate(folder),
        folders=[FolderRead.model_validate(item) for item in folders],
        files=[to_file_summary(item) for item in files],
        permission_level=permission_level,
    )


def to_share_access_response(
    share_link: ShareLink,
    resource: File | Folder,
) -> ShareAccessResponse:
    if share_link.resource_type.name == "FILE":
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
