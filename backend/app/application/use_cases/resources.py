from __future__ import annotations

from math import ceil

from app.application.mappers import to_resource_search_response
from app.application.ports import UnitOfWorkPort
from app.application.types import ResourceSearchRow
from app.application.use_cases.base import UseCaseBase
from app.domain.enums import ResourceType
from app.schemas.file import FileSummary
from app.schemas.folder import FolderRead
from app.schemas.resource import (
    FileSearchItem,
    FolderSearchItem,
    ResourceSearchQuery,
    ResourceSearchResponse,
)


def _to_folder_item(row: ResourceSearchRow) -> FolderSearchItem:
    return FolderSearchItem(
        folder=FolderRead(
            id=row.id,
            owner_id=row.owner_id,
            parent_id=row.parent_id,
            name=row.name,
            path_cache=row.path_cache,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    )


def _to_file_item(row: ResourceSearchRow) -> FileSearchItem:
    return FileSearchItem(
        file=FileSummary(
            id=row.id,
            stored_filename=row.name,
            content_type=row.content_type,
            size_bytes=row.size_bytes or 0,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
    )


class ResourceUseCase(UseCaseBase):
    def __init__(self, uow: UnitOfWorkPort) -> None:
        super().__init__(uow)

    def search(self, current_user, query: ResourceSearchQuery) -> ResourceSearchResponse:
        search_page = self.uow.resources.search_folder_contents(
            owner_id=current_user.id,
            parent_id=query.parent_id,
            query=query.q,
            resource_type=query.type,
            sort_by=query.sort_by,
            order=query.order,
            page=query.page,
            page_size=query.page_size,
        )
        total_pages = max(1, ceil(search_page.total_items / query.page_size))

        items: list[FolderSearchItem | FileSearchItem] = []
        for item in search_page.items:
            if item.item_type is ResourceType.FOLDER:
                items.append(_to_folder_item(item))
            else:
                items.append(_to_file_item(item))

        return to_resource_search_response(
            items,
            page=query.page,
            page_size=query.page_size,
            total_items=search_page.total_items,
            total_pages=total_pages,
        )
