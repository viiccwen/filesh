from __future__ import annotations

import uuid

from sqlalchemy import not_, select
from sqlalchemy.orm import Session

from app.models import File, UploadSession, UploadSessionStatus


def list_filenames_in_folder(session: Session, folder_id: uuid.UUID) -> set[str]:
    return {
        row[0]
        for row in session.execute(select(File.stored_filename).where(File.folder_id == folder_id))
    }


def list_reserved_filenames_in_folder(session: Session, folder_id: uuid.UUID) -> set[str]:
    return {
        row[0]
        for row in session.execute(
            select(UploadSession.resolved_filename).where(
                UploadSession.folder_id == folder_id,
                not_(UploadSession.status.in_([UploadSessionStatus.FAILED])),
            )
        )
    }


def add_upload_session(session: Session, upload_session: UploadSession) -> None:
    session.add(upload_session)


def get_upload_session_by_owner(
    session: Session,
    upload_session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> UploadSession | None:
    return session.scalar(
        select(UploadSession).where(
            UploadSession.id == upload_session_id,
            UploadSession.owner_id == owner_id,
        )
    )


def add_file(session: Session, file: File) -> None:
    session.add(file)


def get_file_by_owner(session: Session, file_id: uuid.UUID, owner_id: uuid.UUID) -> File | None:
    return session.scalar(select(File).where(File.id == file_id, File.owner_id == owner_id))


def get_file_by_id(session: Session, file_id: uuid.UUID) -> File | None:
    return session.scalar(select(File).where(File.id == file_id))


def list_files_by_folder_ids(session: Session, folder_ids: list[uuid.UUID]) -> list[File]:
    if not folder_ids:
        return []
    return list(session.scalars(select(File).where(File.folder_id.in_(folder_ids))))
