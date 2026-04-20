from __future__ import annotations

import uuid

from sqlalchemy import case, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.application.ports import ResourcesRepositoryPort
from app.application.types import ResourceSearchPage, ResourceSearchRow
from app.domain.enums import ResourceType
from app.persistence.models import File, Folder


class SqlAlchemyResourcesRepository(ResourcesRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_folder_contents(
        self,
        *,
        owner_id: uuid.UUID,
        parent_id: uuid.UUID,
        query: str,
        resource_type: ResourceType | None,
        sort_by: str,
        order: str,
        page: int,
        page_size: int,
    ) -> ResourceSearchPage:
        normalized_query = query.strip()
        folder_select = self._build_folder_select(owner_id, parent_id, normalized_query)
        file_select = self._build_file_select(owner_id, parent_id, normalized_query)

        if resource_type is ResourceType.FOLDER:
            base_query = folder_select
        elif resource_type is ResourceType.FILE:
            base_query = file_select
        else:
            base_query = union_all(folder_select, file_select)

        search_subquery = base_query.subquery()
        total_items = self.session.scalar(select(func.count()).select_from(search_subquery)) or 0

        ordered_query = (
            select(search_subquery)
            .order_by(*self._build_order_by(search_subquery, sort_by, order))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = self.session.execute(ordered_query).mappings().all()
        items = [
            ResourceSearchRow(
                id=row["id"],
                item_type=ResourceType(row["item_type"]),
                owner_id=row["owner_id"],
                parent_id=row["parent_id"],
                folder_id=row["folder_id"],
                name=row["name"],
                path_cache=row["path_cache"],
                content_type=row["content_type"],
                size_bytes=row["size_bytes"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
        return ResourceSearchPage(items=items, total_items=total_items)

    @staticmethod
    def _build_folder_select(owner_id: uuid.UUID, parent_id: uuid.UUID, query: str):
        statement = select(
            Folder.id.label("id"),
            literal(ResourceType.FOLDER.value).label("item_type"),
            Folder.owner_id.label("owner_id"),
            Folder.parent_id.label("parent_id"),
            cast(None, Folder.id.type).label("folder_id"),
            Folder.name.label("name"),
            Folder.path_cache.label("path_cache"),
            cast(None, File.content_type.type).label("content_type"),
            cast(None, File.size_bytes.type).label("size_bytes"),
            cast(None, File.status.type).label("status"),
            Folder.created_at.label("created_at"),
            Folder.updated_at.label("updated_at"),
        ).where(
            Folder.owner_id == owner_id,
            Folder.parent_id == parent_id,
        )
        if query:
            statement = statement.where(Folder.name.ilike(f"%{query}%"))
        return statement

    @staticmethod
    def _build_file_select(owner_id: uuid.UUID, parent_id: uuid.UUID, query: str):
        statement = select(
            File.id.label("id"),
            literal(ResourceType.FILE.value).label("item_type"),
            File.owner_id.label("owner_id"),
            cast(None, Folder.parent_id.type).label("parent_id"),
            File.folder_id.label("folder_id"),
            File.stored_filename.label("name"),
            cast(None, Folder.path_cache.type).label("path_cache"),
            File.content_type.label("content_type"),
            File.size_bytes.label("size_bytes"),
            File.status.label("status"),
            File.created_at.label("created_at"),
            File.updated_at.label("updated_at"),
        ).where(
            File.owner_id == owner_id,
            File.folder_id == parent_id,
        )
        if query:
            statement = statement.where(File.stored_filename.ilike(f"%{query}%"))
        return statement

    @staticmethod
    def _build_order_by(search_subquery, sort_by: str, order: str):
        def direction(expr):
            return expr.desc() if order == "desc" else expr.asc()

        item_type_expr = search_subquery.c.item_type
        name_expr = search_subquery.c.name

        if sort_by == "updated_at":
            return [direction(search_subquery.c.updated_at), direction(name_expr)]
        if sort_by == "size":
            size_expr = case(
                (item_type_expr == ResourceType.FOLDER.value, -1),
                else_=search_subquery.c.size_bytes,
            )
            return [direction(size_expr), direction(name_expr)]
        if sort_by == "type":
            return [direction(item_type_expr), direction(name_expr)]
        return [direction(name_expr), direction(item_type_expr)]
