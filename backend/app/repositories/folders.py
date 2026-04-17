from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Folder, UploadSession


def add_folder(session: Session, folder: Folder) -> None:
    session.add(folder)


def get_root_folder(session: Session, user_id: uuid.UUID, root_folder_name: str) -> Folder | None:
    return session.scalar(
        select(Folder).where(
            Folder.owner_id == user_id,
            Folder.parent_id.is_(None),
            Folder.name == root_folder_name,
        )
    )


def get_folder_by_owner(
    session: Session, folder_id: uuid.UUID, owner_id: uuid.UUID
) -> Folder | None:
    return session.scalar(select(Folder).where(Folder.id == folder_id, Folder.owner_id == owner_id))


def get_folder_by_id(session: Session, folder_id: uuid.UUID) -> Folder | None:
    return session.scalar(select(Folder).where(Folder.id == folder_id))


def get_folder_with_contents_by_owner(
    session: Session,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Folder | None:
    return session.scalar(
        select(Folder)
        .options(selectinload(Folder.children), selectinload(Folder.files))
        .where(Folder.id == folder_id, Folder.owner_id == owner_id)
    )


def list_descendant_folder_ids(
    session: Session,
    owner_id: uuid.UUID,
    path_prefix: str,
) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(Folder.id).where(
                Folder.owner_id == owner_id,
                (
                    (Folder.path_cache == path_prefix)
                    | Folder.path_cache.startswith(f"{path_prefix}/")
                ),
            )
        )
    )


def list_upload_sessions_by_folder_ids(
    session: Session,
    folder_ids: list[uuid.UUID],
) -> list[UploadSession]:
    if not folder_ids:
        return []
    return list(
        session.scalars(select(UploadSession).where(UploadSession.folder_id.in_(folder_ids)))
    )
