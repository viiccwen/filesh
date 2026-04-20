from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from app.application.ports import UnitOfWorkPort
from app.domain import ConflictError, NotFoundError, ValidationError
from app.persistence.models import File, Folder
from app.schemas.folder import FolderCreateRequest

ROOT_FOLDER_NAME = "/"
ROOT_FOLDER_PATH = "/"


def create_root_folder(uow: UnitOfWorkPort, owner_id: uuid.UUID) -> Folder:
    root_folder = Folder(
        owner_id=owner_id,
        parent_id=None,
        name=ROOT_FOLDER_NAME,
        path_cache=ROOT_FOLDER_PATH,
    )
    uow.folders.add(root_folder)
    uow.flush()
    return root_folder


def get_root_folder(uow: UnitOfWorkPort, user_id: uuid.UUID) -> Folder | None:
    return uow.folders.get_root(user_id, ROOT_FOLDER_NAME)


def get_or_create_root_folder(uow: UnitOfWorkPort, owner_id: uuid.UUID) -> tuple[Folder, bool]:
    root_folder = get_root_folder(uow, owner_id)
    if root_folder is not None:
        return root_folder, False
    return create_root_folder(uow, owner_id), True


def get_folder_for_owner(uow: UnitOfWorkPort, folder_id: uuid.UUID, owner_id: uuid.UUID) -> Folder:
    folder = uow.folders.get_by_owner(folder_id, owner_id)
    if folder is None:
        raise NotFoundError("Folder not found")
    return folder


def build_folder_path(parent: Folder | None, folder_name: str) -> str:
    if parent is None or parent.path_cache in (None, ROOT_FOLDER_PATH):
        return f"/{folder_name}"
    return f"{parent.path_cache}/{folder_name}"


def create_folder(uow: UnitOfWorkPort, owner_id: uuid.UUID, payload: FolderCreateRequest) -> Folder:
    if payload.name == ROOT_FOLDER_NAME:
        raise ValidationError("Folder name is reserved")

    parent = (
        get_folder_for_owner(uow, payload.parent_id, owner_id)
        if payload.parent_id is not None
        else get_or_create_root_folder(uow, owner_id)[0]
    )

    folder = Folder(
        owner_id=owner_id,
        parent_id=parent.id if parent is not None else None,
        name=payload.name,
        path_cache=build_folder_path(parent, payload.name),
    )
    uow.folders.add(folder)
    ensure_folder_write_succeeds(uow, "Folder name already exists in this location")
    return folder


def ensure_folder_write_succeeds(uow: UnitOfWorkPort, conflict_message: str) -> None:
    try:
        uow.flush()
    except IntegrityError as exc:
        raise ConflictError(conflict_message) from exc


def list_folder_contents(
    uow: UnitOfWorkPort,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> tuple[Folder, list[Folder], list[File]]:
    folder = uow.folders.get_with_contents_by_owner(folder_id, owner_id)
    if folder is None:
        raise NotFoundError("Folder not found")

    child_folders = sorted(folder.children, key=lambda item: item.name.lower())
    files = sorted(folder.files, key=lambda item: item.stored_filename.lower())
    return folder, child_folders, files


def list_descendant_folder_ids(
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    folder: Folder,
) -> list[uuid.UUID]:
    return uow.folders.list_descendant_folder_ids(owner_id, folder.path_cache)


def rename_folder(
    uow: UnitOfWorkPort,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
    name: str,
) -> Folder:
    folder = get_folder_for_owner(uow, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise ValidationError("Root folder cannot be renamed")
    if name == ROOT_FOLDER_NAME:
        raise ValidationError("Folder name is reserved")

    parent = get_folder_for_owner(uow, folder.parent_id, owner_id) if folder.parent_id else None
    old_path = folder.path_cache or build_folder_path(parent, folder.name)
    new_path = build_folder_path(parent, name)

    descendants = uow.folders.list_descendant_folders(owner_id, old_path)
    folder.name = name
    folder.path_cache = new_path
    for descendant in descendants:
        if descendant.id == folder.id or descendant.path_cache is None:
            continue
        descendant.path_cache = descendant.path_cache.replace(old_path, new_path, 1)
    ensure_folder_write_succeeds(uow, "Folder name already exists in this location")
    return folder


def move_folder(
    uow: UnitOfWorkPort,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
    target_parent_id: uuid.UUID,
) -> Folder:
    folder = get_folder_for_owner(uow, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise ValidationError("Root folder cannot be moved")

    target_parent = get_folder_for_owner(uow, target_parent_id, owner_id)
    old_path = folder.path_cache or build_folder_path(None, folder.name)

    if target_parent.id == folder.id:
        raise ValidationError("Folder cannot be moved into itself")
    if target_parent.path_cache and (
        target_parent.path_cache == old_path or target_parent.path_cache.startswith(f"{old_path}/")
    ):
        raise ValidationError("Folder cannot be moved into its descendant")

    new_path = build_folder_path(target_parent, folder.name)
    descendants = uow.folders.list_descendant_folders(owner_id, old_path)
    folder.parent_id = target_parent.id
    folder.path_cache = new_path
    for descendant in descendants:
        if descendant.id == folder.id or descendant.path_cache is None:
            continue
        descendant.path_cache = descendant.path_cache.replace(old_path, new_path, 1)
    ensure_folder_write_succeeds(uow, "Folder name already exists in this location")
    return folder


def list_descendant_files(uow: UnitOfWorkPort, folder_ids: list[uuid.UUID]) -> list[File]:
    return uow.files.list_by_folder_ids(folder_ids)


def prepare_folder_delete(
    uow: UnitOfWorkPort,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> tuple[Folder, list[File], list[uuid.UUID]]:
    folder = get_folder_for_owner(uow, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise ValidationError("Root folder cannot be deleted")

    folder_ids = list_descendant_folder_ids(uow, owner_id, folder)
    files_to_cleanup = list_descendant_files(uow, folder_ids)
    return folder, files_to_cleanup, folder_ids


def delete_folder_tree(uow: UnitOfWorkPort, folder: Folder, folder_ids: list[uuid.UUID]) -> None:
    for upload_session in uow.folders.list_upload_sessions_by_folder_ids(folder_ids):
        uow.delete(upload_session)
    uow.delete(folder)
