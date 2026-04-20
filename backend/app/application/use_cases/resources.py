from __future__ import annotations

from math import ceil

from app.application.mappers import to_file_summary
from app.application.ports import UnitOfWorkPort
from app.application.use_cases.base import UseCaseBase
from app.domain.enums import ResourceType
from app.persistence.models import File, Folder
from app.schemas.folder import FolderRead
from app.schemas.resource import (
    FileSearchItem,
    FolderSearchItem,
    ResourceSearchPagination,
    ResourceSearchQuery,
    ResourceSearchResponse,
)


def _matches_query(value: str, query: str) -> bool:
    return query in value.lower()


def _name_for_item(item: Folder | File, item_type: ResourceType) -> str:
    return item.name.lower() if item_type is ResourceType.FOLDER else item.stored_filename.lower()


def _sort_value(item: Folder | File, item_type: ResourceType, sort_by: str):
    item_name = _name_for_item(item, item_type)
    if sort_by == "updated_at":
        return (item.updated_at, item_name)
    if sort_by == "size":
        return (-1 if item_type is ResourceType.FOLDER else item.size_bytes, item_name)
    if sort_by == "type":
        return (item_type.value, item_name)
    return (item_name, item_type.value)


class ResourceUseCase(UseCaseBase):
    def __init__(self, uow: UnitOfWorkPort) -> None:
        super().__init__(uow)

    def search(self, current_user, query: ResourceSearchQuery) -> ResourceSearchResponse:
        folder = self.uow.folders.get_with_contents_by_owner(query.parent_id, current_user.id)
        if folder is None:
            return ResourceSearchResponse(
                items=[],
                pagination=ResourceSearchPagination(
                    page=query.page,
                    page_size=query.page_size,
                    total_items=0,
                    total_pages=1,
                ),
            )

        normalized_query = query.q.strip().lower()
        combined_items: list[tuple[ResourceType, Folder | File]] = []

        if query.type in (None, ResourceType.FOLDER):
            for child_folder in folder.children:
                if normalized_query and not _matches_query(child_folder.name, normalized_query):
                    continue
                combined_items.append((ResourceType.FOLDER, child_folder))

        if query.type in (None, ResourceType.FILE):
            for child_file in folder.files:
                if normalized_query and not _matches_query(
                    child_file.stored_filename, normalized_query
                ):
                    continue
                combined_items.append((ResourceType.FILE, child_file))

        reverse = query.order == "desc"
        combined_items.sort(
            key=lambda item: _sort_value(item[1], item[0], query.sort_by),
            reverse=reverse,
        )

        total_items = len(combined_items)
        total_pages = max(1, ceil(total_items / query.page_size))
        start_index = (query.page - 1) * query.page_size
        end_index = start_index + query.page_size
        paginated_items = combined_items[start_index:end_index]

        items: list[FolderSearchItem | FileSearchItem] = []
        for item_type, item in paginated_items:
            if item_type is ResourceType.FOLDER:
                items.append(FolderSearchItem(folder=FolderRead.model_validate(item)))
            else:
                items.append(FileSearchItem(file=to_file_summary(item)))

        return ResourceSearchResponse(
            items=items,
            pagination=ResourceSearchPagination(
                page=query.page,
                page_size=query.page_size,
                total_items=total_items,
                total_pages=total_pages,
            ),
        )
