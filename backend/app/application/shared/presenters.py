from __future__ import annotations

from app.application.dto import (
    FileDTO,
    FileSearchItemDTO,
    FileSummaryDTO,
    FolderContentsDTO,
    FolderDTO,
    FolderSearchItemDTO,
    ResourceSearchPaginationDTO,
    ResourceSearchResponseDTO,
    ShareAccessDTO,
    SharedFolderContentsDTO,
    UploadInitDTO,
)
from app.persistence.models import File, Folder, ShareLink


def to_upload_init_response(upload_session) -> UploadInitDTO:
    return UploadInitDTO(
        session_id=upload_session.id,
        resolved_filename=upload_session.resolved_filename,
        object_key=upload_session.object_key,
        status=upload_session.status,
    )


def to_file_summary(file: File) -> FileSummaryDTO:
    return FileSummaryDTO(
        id=file.id,
        stored_filename=file.stored_filename,
        content_type=file.content_type,
        size_bytes=file.size_bytes,
        status=file.status,
        created_at=file.created_at,
        updated_at=file.updated_at,
    )


def to_folder_contents_response(
    folder: Folder,
    folders: list[Folder],
    files: list[File],
) -> FolderContentsDTO:
    return FolderContentsDTO(
        folder=FolderDTO.model_validate(folder),
        folders=[FolderDTO.model_validate(item) for item in folders],
        files=[to_file_summary(item) for item in files],
    )


def to_shared_folder_contents_response(
    folder: Folder,
    folders: list[Folder],
    files: list[File],
    permission_level,
) -> SharedFolderContentsDTO:
    return SharedFolderContentsDTO(
        folder=FolderDTO.model_validate(folder),
        folders=[FolderDTO.model_validate(item) for item in folders],
        files=[to_file_summary(item) for item in files],
        permission_level=permission_level,
    )


def to_resource_search_response(
    items: list[FolderSearchItemDTO | FileSearchItemDTO],
    *,
    page: int,
    page_size: int,
    total_items: int,
    total_pages: int,
) -> ResourceSearchResponseDTO:
    return ResourceSearchResponseDTO(
        items=items,
        pagination=ResourceSearchPaginationDTO(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        ),
    )


def to_share_access_response(
    share_link: ShareLink,
    resource: File | Folder,
) -> ShareAccessDTO:
    if share_link.resource_type.name == "FILE":
        return ShareAccessDTO(
            resource_type=share_link.resource_type,
            share_mode=share_link.share_mode,
            permission_level=share_link.permission_level,
            expires_at=share_link.expires_at,
            file=FileDTO.model_validate(resource),
        )
    return ShareAccessDTO(
        resource_type=share_link.resource_type,
        share_mode=share_link.share_mode,
        permission_level=share_link.permission_level,
        expires_at=share_link.expires_at,
        folder=FolderDTO.model_validate(resource),
    )
