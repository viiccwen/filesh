from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.auth import AuthUseCase
from app.application.use_cases.files import FileUseCase
from app.application.use_cases.folders import FolderUseCase
from app.application.use_cases.share_access import ShareAccessUseCase
from app.application.use_cases.users import UserUseCase
from app.core.db import get_db_session
from app.core.events import EventPublisher
from app.core.storage import ObjectStorage
from app.dependencies.events import get_event_publisher
from app.dependencies.storage import get_object_storage

db_session_dependency = Depends(get_db_session)
object_storage_dependency = Depends(get_object_storage)
event_publisher_dependency = Depends(get_event_publisher)


def get_auth_use_case(
    session: Session = db_session_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> AuthUseCase:
    return AuthUseCase(session, event_publisher)


def get_folder_use_case(
    session: Session = db_session_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> FolderUseCase:
    return FolderUseCase(session, event_publisher)


def get_file_use_case(
    session: Session = db_session_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> FileUseCase:
    return FileUseCase(session, object_storage, event_publisher)


def get_share_access_use_case(
    session: Session = db_session_dependency,
    object_storage: ObjectStorage = object_storage_dependency,
    event_publisher: EventPublisher = event_publisher_dependency,
) -> ShareAccessUseCase:
    return ShareAccessUseCase(session, object_storage, event_publisher)


def get_user_use_case(
    session: Session = db_session_dependency,
) -> UserUseCase:
    return UserUseCase(session)
