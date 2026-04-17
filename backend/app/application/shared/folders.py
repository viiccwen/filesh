from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.events import CleanupEventType, EventPublisher, build_cleanup_event
from app.domain import ConflictError, NotFoundError, ValidationError
from app.models import File, Folder
from app.repositories import files as file_repository
from app.repositories import folders as folder_repository
from app.schemas.folder import FolderCreateRequest

ROOT_FOLDER_NAME = "/"
ROOT_FOLDER_PATH = "/"


def create_root_folder(session: Session, owner_id: uuid.UUID) -> Folder:
    root_folder = Folder(
        owner_id=owner_id,
        parent_id=None,
        name=ROOT_FOLDER_NAME,
        path_cache=ROOT_FOLDER_PATH,
    )
    folder_repository.add_folder(session, root_folder)
    session.flush()
    return root_folder


def get_root_folder(session: Session, user_id: uuid.UUID) -> Folder | None:
    return folder_repository.get_root_folder(session, user_id, ROOT_FOLDER_NAME)


def get_or_create_root_folder(session: Session, owner_id: uuid.UUID) -> Folder:
    root_folder = get_root_folder(session, owner_id)
    if root_folder is not None:
        return root_folder

    root_folder = create_root_folder(session, owner_id)
    session.commit()
    session.refresh(root_folder)
    return root_folder


def get_folder_for_owner(session: Session, folder_id: uuid.UUID, owner_id: uuid.UUID) -> Folder:
    folder = folder_repository.get_folder_by_owner(session, folder_id, owner_id)
    if folder is None:
        raise NotFoundError("Folder not found")
    return folder


def build_folder_path(parent: Folder | None, folder_name: str) -> str:
    if parent is None or parent.path_cache in (None, ROOT_FOLDER_PATH):
        return f"/{folder_name}"
    return f"{parent.path_cache}/{folder_name}"


def create_folder(session: Session, owner_id: uuid.UUID, payload: FolderCreateRequest) -> Folder:
    if payload.name == ROOT_FOLDER_NAME:
        raise ValidationError("Folder name is reserved")

    parent = (
        get_folder_for_owner(session, payload.parent_id, owner_id)
        if payload.parent_id is not None
        else get_or_create_root_folder(session, owner_id)
    )

    folder = Folder(
        owner_id=owner_id,
        parent_id=parent.id if parent is not None else None,
        name=payload.name,
        path_cache=build_folder_path(parent, payload.name),
    )
    folder_repository.add_folder(session, folder)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Folder name already exists in this location") from exc

    session.refresh(folder)
    return folder


def list_folder_contents(
    session: Session,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> tuple[Folder, list[Folder], list[File]]:
    folder = folder_repository.get_folder_with_contents_by_owner(session, folder_id, owner_id)
    if folder is None:
        raise NotFoundError("Folder not found")

    child_folders = sorted(folder.children, key=lambda item: item.name.lower())
    files = sorted(folder.files, key=lambda item: item.stored_filename.lower())
    return folder, child_folders, files


def list_descendant_folder_ids(
    session: Session,
    owner_id: uuid.UUID,
    folder: Folder,
) -> list[uuid.UUID]:
    return folder_repository.list_descendant_folder_ids(session, owner_id, folder.path_cache)


def rename_folder(session: Session, folder_id: uuid.UUID, owner_id: uuid.UUID, name: str) -> Folder:
    folder = get_folder_for_owner(session, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise ValidationError("Root folder cannot be renamed")
    if name == ROOT_FOLDER_NAME:
        raise ValidationError("Folder name is reserved")

    parent = get_folder_for_owner(session, folder.parent_id, owner_id) if folder.parent_id else None
    old_path = folder.path_cache or build_folder_path(parent, folder.name)
    new_path = build_folder_path(parent, name)

    descendants = folder_repository.list_descendant_folders(session, owner_id, old_path)
    folder.name = name
    folder.path_cache = new_path
    for descendant in descendants:
        if descendant.id == folder.id:
            continue
        if descendant.path_cache is None:
            continue
        descendant.path_cache = descendant.path_cache.replace(old_path, new_path, 1)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Folder name already exists in this location") from exc

    session.refresh(folder)
    return folder


def move_folder(
    session: Session,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
    target_parent_id: uuid.UUID,
) -> Folder:
    folder = get_folder_for_owner(session, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise ValidationError("Root folder cannot be moved")

    target_parent = get_folder_for_owner(session, target_parent_id, owner_id)
    old_path = folder.path_cache or build_folder_path(None, folder.name)

    if target_parent.id == folder.id:
        raise ValidationError("Folder cannot be moved into itself")
    if target_parent.path_cache and (
        target_parent.path_cache == old_path or target_parent.path_cache.startswith(f"{old_path}/")
    ):
        raise ValidationError("Folder cannot be moved into its descendant")

    new_path = build_folder_path(target_parent, folder.name)
    descendants = folder_repository.list_descendant_folders(session, owner_id, old_path)
    folder.parent_id = target_parent.id
    folder.path_cache = new_path
    for descendant in descendants:
        if descendant.id == folder.id or descendant.path_cache is None:
            continue
        descendant.path_cache = descendant.path_cache.replace(old_path, new_path, 1)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("Folder name already exists in this location") from exc

    session.refresh(folder)
    return folder


def list_descendant_files(session: Session, folder_ids: list[uuid.UUID]) -> list[File]:
    return file_repository.list_files_by_folder_ids(session, folder_ids)


def delete_folder(
    session: Session,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
    event_publisher: EventPublisher,
) -> None:
    folder = get_folder_for_owner(session, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise ValidationError("Root folder cannot be deleted")

    folder_ids = list_descendant_folder_ids(session, owner_id, folder)
    files_to_cleanup = list_descendant_files(session, folder_ids)
    event = build_cleanup_event(
        CleanupEventType.FOLDER_DELETE_REQUESTED,
        resource={"type": "folder", "id": str(folder.id)},
        objects=[
            {"bucket": file.storage_bucket, "object_key": file.object_key}
            for file in files_to_cleanup
        ],
        metadata={"owner_id": str(owner_id)},
    )
    for upload_session in folder_repository.list_upload_sessions_by_folder_ids(session, folder_ids):
        session.delete(upload_session)
    session.delete(folder)
    session.commit()
    event_publisher.publish(settings.kafka_cleanup_topic, str(folder.id), event)
