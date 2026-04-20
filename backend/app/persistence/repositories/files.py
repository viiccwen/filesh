from __future__ import annotations

import uuid

from sqlalchemy import not_, select
from sqlalchemy.orm import Session

from app.application.ports import FilesRepositoryPort
from app.domain.enums import UploadSessionStatus
from app.persistence.models import File, UploadSession


class SqlAlchemyFilesRepository(FilesRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_filenames_in_folder(self, folder_id: uuid.UUID) -> set[str]:
        return {
            row[0]
            for row in self.session.execute(
                select(File.stored_filename).where(File.folder_id == folder_id)
            )
        }

    def list_reserved_filenames_in_folder(self, folder_id: uuid.UUID) -> set[str]:
        return {
            row[0]
            for row in self.session.execute(
                select(UploadSession.resolved_filename).where(
                    UploadSession.folder_id == folder_id,
                    not_(UploadSession.status.in_([UploadSessionStatus.FAILED])),
                )
            )
        }

    def add_upload_session(self, upload_session: UploadSession) -> None:
        self.session.add(upload_session)

    def get_upload_session_by_owner(
        self, upload_session_id: uuid.UUID, owner_id: uuid.UUID
    ) -> UploadSession | None:
        return self.session.scalar(
            select(UploadSession).where(
                UploadSession.id == upload_session_id,
                UploadSession.owner_id == owner_id,
            )
        )

    def add_file(self, file: File) -> None:
        self.session.add(file)

    def get_by_owner(self, file_id: uuid.UUID, owner_id: uuid.UUID) -> File | None:
        return self.session.scalar(
            select(File).where(File.id == file_id, File.owner_id == owner_id)
        )

    def get_by_id(self, file_id: uuid.UUID) -> File | None:
        return self.session.scalar(select(File).where(File.id == file_id))

    def list_by_folder_ids(self, folder_ids: list[uuid.UUID]) -> list[File]:
        if not folder_ids:
            return []
        return list(self.session.scalars(select(File).where(File.folder_id.in_(folder_ids))))
