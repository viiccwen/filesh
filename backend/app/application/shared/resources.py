from __future__ import annotations

import uuid
from math import ceil

from sqlalchemy.orm import Session

from app.application.dto import FileSearchItemDTO, FolderDTO, FolderSearchItemDTO
from app.application.shared.folders import get_folder_for_owner
from app.application.shared.presenters import to_file_summary
from app.domain.enums import ResourceType
from app.persistence.models import File, Folder
from app.repositories import folders as folder_repository
from app.schemas.resource import ResourceSearchQuery


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


def search_resources(
    session: Session,
    owner_id: uuid.UUID,
    query: ResourceSearchQuery,
) -> tuple[list[FolderSearchItemDTO | FileSearchItemDTO], int, int]:
    folder = get_folder_for_owner(session, query.parent_id, owner_id)
    folder_with_contents = folder_repository.get_folder_with_contents_by_owner(
        session, folder.id, owner_id
    )
    if folder_with_contents is None:
        return [], 0, 1

    normalized_query = query.q.strip().lower()
    combined_items: list[tuple[ResourceType, Folder | File]] = []

    if query.type in (None, ResourceType.FOLDER):
        for child_folder in folder_with_contents.children:
            if normalized_query and not _matches_query(child_folder.name, normalized_query):
                continue
            combined_items.append((ResourceType.FOLDER, child_folder))

    if query.type in (None, ResourceType.FILE):
        for child_file in folder_with_contents.files:
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

    items: list[FolderSearchItemDTO | FileSearchItemDTO] = []
    for item_type, item in paginated_items:
        if item_type is ResourceType.FOLDER:
            items.append(FolderSearchItemDTO(folder=FolderDTO.model_validate(item)))
        else:
            items.append(FileSearchItemDTO(file=to_file_summary(item)))

    return items, total_items, total_pages
