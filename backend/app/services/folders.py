from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import File, Folder, User
from app.schemas.folder import FolderCreateRequest

ROOT_FOLDER_NAME = "/"
ROOT_FOLDER_PATH = "/"


def create_root_folder(session: Session, user: User) -> Folder:
    root_folder = Folder(
        owner_id=user.id,
        parent_id=None,
        name=ROOT_FOLDER_NAME,
        path_cache=ROOT_FOLDER_PATH,
    )
    session.add(root_folder)
    session.flush()
    return root_folder


def get_root_folder(session: Session, user_id: uuid.UUID) -> Folder | None:
    return session.scalar(
        select(Folder).where(
            Folder.owner_id == user_id,
            Folder.parent_id.is_(None),
            Folder.name == ROOT_FOLDER_NAME,
        )
    )


def get_or_create_root_folder(session: Session, user: User) -> Folder:
    root_folder = get_root_folder(session, user.id)
    if root_folder is not None:
        return root_folder

    root_folder = create_root_folder(session, user)
    session.commit()
    session.refresh(root_folder)
    return root_folder


def get_folder_for_owner(session: Session, folder_id: uuid.UUID, owner_id: uuid.UUID) -> Folder:
    folder = session.scalar(
        select(Folder).where(Folder.id == folder_id, Folder.owner_id == owner_id)
    )
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


def build_folder_path(parent: Folder | None, folder_name: str) -> str:
    if parent is None or parent.path_cache in (None, ROOT_FOLDER_PATH):
        return f"/{folder_name}"
    return f"{parent.path_cache}/{folder_name}"


def create_folder(session: Session, owner: User, payload: FolderCreateRequest) -> Folder:
    if payload.name == ROOT_FOLDER_NAME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder name is reserved",
        )

    parent = (
        get_folder_for_owner(session, payload.parent_id, owner.id)
        if payload.parent_id is not None
        else get_or_create_root_folder(session, owner)
    )

    folder = Folder(
        owner_id=owner.id,
        parent_id=parent.id if parent is not None else None,
        name=payload.name,
        path_cache=build_folder_path(parent, payload.name),
    )
    session.add(folder)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder name already exists in this location",
        ) from exc

    session.refresh(folder)
    return folder


def list_folder_contents(
    session: Session,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> tuple[Folder, list[Folder], list[File]]:
    folder = session.scalar(
        select(Folder)
        .options(selectinload(Folder.children), selectinload(Folder.files))
        .where(Folder.id == folder_id, Folder.owner_id == owner_id)
    )
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    child_folders = sorted(folder.children, key=lambda item: item.name.lower())
    files = sorted(folder.files, key=lambda item: item.stored_filename.lower())
    return folder, child_folders, files


def delete_folder(session: Session, folder_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    folder = get_folder_for_owner(session, folder_id, owner_id)
    if folder.parent_id is None and folder.name == ROOT_FOLDER_NAME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Root folder cannot be deleted",
        )

    session.delete(folder)
    session.commit()
