from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.errors import to_http_exception
from app.application.dto import AuthenticatedUser
from app.application.use_cases.resources import ResourceUseCase
from app.dependencies.auth import get_current_user
from app.dependencies.use_cases import get_resource_use_case
from app.domain import AppError, ResourceType
from app.schemas.resource import ResourceSearchQuery, ResourceSearchResponse

router = APIRouter()
current_user_dependency = Depends(get_current_user)
resource_use_case_dependency = Depends(get_resource_use_case)
search_query_dependency = Query(default="", max_length=255)
resource_type_dependency = Query(default=None)
sort_by_dependency = Query(default="name", pattern="^(name|updated_at|size|type)$")
order_dependency = Query(default="asc", pattern="^(asc|desc)$")
page_dependency = Query(default=1, ge=1)
page_size_dependency = Query(default=8, ge=1, le=100)


@router.get("/search", response_model=ResourceSearchResponse)
def search_resources(
    parent_id: uuid.UUID,
    q: str = search_query_dependency,
    type: ResourceType | None = resource_type_dependency,
    sort_by: str = sort_by_dependency,
    order: str = order_dependency,
    page: int = page_dependency,
    page_size: int = page_size_dependency,
    current_user: AuthenticatedUser = current_user_dependency,
    use_case: ResourceUseCase = resource_use_case_dependency,
) -> ResourceSearchResponse:
    try:
        query = ResourceSearchQuery(
            parent_id=parent_id,
            q=q,
            type=type,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )
        return use_case.search(current_user, query)
    except AppError as exc:
        raise to_http_exception(exc) from exc
