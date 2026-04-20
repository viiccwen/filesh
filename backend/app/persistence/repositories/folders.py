from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.application.ports import FoldersRepositoryPort
from app.persistence.models import Folder, UploadSession


class SqlAlchemyFoldersRepository(FoldersRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, folder: Folder) -> None:
        self.session.add(folder)

    def get_root(self, user_id: uuid.UUID, root_folder_name: str) -> Folder | None:
        return self.session.scalar(
            select(Folder).where(
                Folder.owner_id == user_id,
                Folder.parent_id.is_(None),
                Folder.name == root_folder_name,
            )
        )

    def get_by_owner(self, folder_id: uuid.UUID, owner_id: uuid.UUID) -> Folder | None:
        return self.session.scalar(
            select(Folder).where(Folder.id == folder_id, Folder.owner_id == owner_id)
        )

    def get_by_id(self, folder_id: uuid.UUID) -> Folder | None:
        return self.session.scalar(select(Folder).where(Folder.id == folder_id))

    def get_with_contents_by_owner(
        self,
        folder_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Folder | None:
        return self.session.scalar(
            select(Folder)
            .options(selectinload(Folder.children), selectinload(Folder.files))
            .where(Folder.id == folder_id, Folder.owner_id == owner_id)
        )

    def list_descendant_folder_ids(
        self,
        owner_id: uuid.UUID,
        path_prefix: str,
    ) -> list[uuid.UUID]:
        return list(
            self.session.scalars(
                select(Folder.id).where(
                    Folder.owner_id == owner_id,
                    (
                        (Folder.path_cache == path_prefix)
                        | Folder.path_cache.startswith(f"{path_prefix}/")
                    ),
                )
            )
        )

    def list_descendant_folders(
        self,
        owner_id: uuid.UUID,
        path_prefix: str,
    ) -> list[Folder]:
        return list(
            self.session.scalars(
                select(Folder).where(
                    Folder.owner_id == owner_id,
                    (
                        (Folder.path_cache == path_prefix)
                        | Folder.path_cache.startswith(f"{path_prefix}/")
                    ),
                )
            )
        )

    def list_upload_sessions_by_folder_ids(
        self,
        folder_ids: list[uuid.UUID],
    ) -> list[UploadSession]:
        if not folder_ids:
            return []
        return list(
            self.session.scalars(
                select(UploadSession).where(UploadSession.folder_id.in_(folder_ids))
            )
        )
