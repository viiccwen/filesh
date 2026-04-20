from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.ports import EventPublisherPort, ObjectStoragePort, UnitOfWorkPort
from app.application.use_cases.auth import AuthUseCase
from app.application.use_cases.files import FileUseCase
from app.application.use_cases.folders import FolderUseCase
from app.application.use_cases.resources import ResourceUseCase
from app.application.use_cases.share_access import ShareAccessUseCase
from app.application.use_cases.users import UserUseCase
from app.core.db import get_db_session
from app.dependencies.events import get_event_publisher
from app.dependencies.storage import get_object_storage
from app.persistence.uow import SqlAlchemyUnitOfWork

db_session_dependency = Depends(get_db_session)
object_storage_dependency = Depends(get_object_storage)
event_publisher_dependency = Depends(get_event_publisher)


def get_unit_of_work(session: Session = db_session_dependency) -> UnitOfWorkPort:
    return SqlAlchemyUnitOfWork(session)


uow_dependency = Depends(get_unit_of_work)


def get_auth_use_case(
    uow: UnitOfWorkPort = uow_dependency,
    event_publisher: EventPublisherPort = event_publisher_dependency,
) -> AuthUseCase:
    return AuthUseCase(uow, event_publisher)


def get_folder_use_case(
    uow: UnitOfWorkPort = uow_dependency,
    event_publisher: EventPublisherPort = event_publisher_dependency,
) -> FolderUseCase:
    return FolderUseCase(uow, event_publisher)


def get_file_use_case(
    uow: UnitOfWorkPort = uow_dependency,
    object_storage: ObjectStoragePort = object_storage_dependency,
    event_publisher: EventPublisherPort = event_publisher_dependency,
) -> FileUseCase:
    return FileUseCase(uow, object_storage, event_publisher)


def get_resource_use_case(
    uow: UnitOfWorkPort = uow_dependency,
) -> ResourceUseCase:
    return ResourceUseCase(uow)


def get_share_access_use_case(
    uow: UnitOfWorkPort = uow_dependency,
    object_storage: ObjectStoragePort = object_storage_dependency,
    event_publisher: EventPublisherPort = event_publisher_dependency,
) -> ShareAccessUseCase:
    return ShareAccessUseCase(uow, object_storage, event_publisher)


def get_user_use_case(
    uow: UnitOfWorkPort = uow_dependency,
) -> UserUseCase:
    return UserUseCase(uow)
