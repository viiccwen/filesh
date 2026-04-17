from __future__ import annotations

from app.application.dto import ResourceSearchResponseDTO
from app.application.shared.presenters import to_resource_search_response
from app.application.shared.resources import search_resources
from app.schemas.resource import ResourceSearchQuery


class ResourceUseCase:
    def __init__(self, session) -> None:
        self.session = session

    def search(self, current_user, query: ResourceSearchQuery) -> ResourceSearchResponseDTO:
        items, total_items, total_pages = search_resources(self.session, current_user.id, query)
        return to_resource_search_response(
            items,
            page=query.page,
            page_size=query.page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
