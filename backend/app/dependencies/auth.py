from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.core.security import decode_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)
db_session_dependency = Depends(get_db_session)
bearer_dependency = Depends(bearer_scheme)


def resolve_current_user(
    session: Session = db_session_dependency,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> User | None:
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, jwt.InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    user = session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def get_current_user(
    session: Session = db_session_dependency,
    credentials: HTTPAuthorizationCredentials | None = bearer_dependency,
) -> User:
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
) -> User | None:
    if credentials is None:
        return None
    return resolve_current_user(session, credentials)
