from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.services import identity
from app.application.types import AuthenticatedUser
from app.core.db import get_db_session
from app.domain import AuthenticationError
from app.persistence.uow import SqlAlchemyUnitOfWork

bearer_scheme = HTTPBearer(auto_error=False)
db_session_dependency = Depends(get_db_session)
bearer_dependency = Depends(bearer_scheme)


def resolve_current_user(
    session: Session = db_session_dependency,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> AuthenticatedUser | None:
    if credentials is None:
        return None

    try:
        return identity.resolve_access_user(
            SqlAlchemyUnitOfWork(session),
            credentials.credentials,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_current_user(
    session: Session = db_session_dependency,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> AuthenticatedUser:
    user = resolve_current_user(session, credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def get_optional_current_user(
    session: Session = db_session_dependency,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> AuthenticatedUser | None:
    if credentials is None:
        return None
    return resolve_current_user(session, credentials)
