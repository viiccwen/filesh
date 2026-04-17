from __future__ import annotations

from fastapi import HTTPException, status

from app.domain import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    GoneError,
    NotFoundError,
    ValidationError,
)


def to_http_exception(error: AppError) -> HTTPException:
    if isinstance(error, AuthenticationError):
        return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error.detail)
    if isinstance(error, AuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.detail)
    if isinstance(error, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.detail)
    if isinstance(error, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail)
    if isinstance(error, GoneError):
        return HTTPException(status_code=status.HTTP_410_GONE, detail=error.detail)
    if isinstance(error, ValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.detail)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error.detail)
