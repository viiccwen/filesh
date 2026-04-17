from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import not_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import ObjectStorage
from app.models import File, FileStatus, UploadSession, UploadSessionStatus, User
from app.schemas.file import UploadFailRequest, UploadFinalizeRequest, UploadInitRequest
from app.services.folders import get_folder_for_owner


def split_filename(filename: str) -> tuple[str, str]:
    stem, extension = os.path.splitext(filename)
    return stem or filename, extension


def normalize_filename(filename: str) -> str:
    return os.path.basename(filename.strip())


def resolve_filename_collision(session: Session, folder_id: uuid.UUID, filename: str) -> str:
    normalized = normalize_filename(filename)
    stem, extension = split_filename(normalized)

    existing_filenames = {
        row[0]
        for row in session.execute(select(File.stored_filename).where(File.folder_id == folder_id))
    }
    reserved_filenames = {
        row[0]
        for row in session.execute(
            select(UploadSession.resolved_filename).where(
                UploadSession.folder_id == folder_id,
                not_(UploadSession.status.in_([UploadSessionStatus.FAILED])),
            )
        )
    }
    occupied = existing_filenames | reserved_filenames

    if normalized not in occupied:
        return normalized

    index = 1
    while True:
        candidate = f"{stem} ({index}){extension}"
        if candidate not in occupied:
            return candidate
        index += 1


def build_object_key(
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    session_id: uuid.UUID,
    filename: str,
) -> str:
    return f"{owner_id}/{folder_id}/{session_id}/{filename}"


def init_upload(session: Session, owner: User, payload: UploadInitRequest) -> UploadSession:
    folder = get_folder_for_owner(session, payload.folder_id, owner.id)
    resolved_filename = resolve_filename_collision(session, folder.id, payload.filename)
    upload_session = UploadSession(
        owner_id=owner.id,
        folder_id=folder.id,
        original_filename=payload.filename,
        resolved_filename=resolved_filename,
        object_key=build_object_key(owner.id, folder.id, uuid.uuid4(), resolved_filename),
        content_type=payload.content_type,
        expected_size=payload.expected_size,
        status=UploadSessionStatus.PENDING,
    )
    session.add(upload_session)
    session.flush()
    upload_session.object_key = build_object_key(
        owner.id,
        folder.id,
        upload_session.id,
        resolved_filename,
    )
    session.commit()
    session.refresh(upload_session)
    return upload_session


def get_upload_session_for_owner(
    session: Session,
    upload_session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> UploadSession:
    upload_session = session.scalar(
        select(UploadSession).where(
            UploadSession.id == upload_session_id,
            UploadSession.owner_id == owner_id,
        )
    )
    if upload_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found",
        )
    return upload_session


def finalize_upload(session: Session, owner: User, payload: UploadFinalizeRequest) -> File:
    upload_session = get_upload_session_for_owner(session, payload.upload_session_id, owner.id)
    if upload_session.status is UploadSessionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload session already failed",
        )
    if upload_session.status is UploadSessionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload content not received",
        )
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload session already finalized",
        )

    extension = split_filename(upload_session.resolved_filename)[1].lstrip(".") or None
    file = File(
        owner_id=owner.id,
        folder_id=upload_session.folder_id,
        original_filename=upload_session.original_filename,
        stored_filename=upload_session.resolved_filename,
        extension=extension,
        content_type=upload_session.content_type,
        size_bytes=payload.size_bytes,
        checksum_sha256=payload.checksum_sha256,
        object_key=upload_session.object_key,
        storage_bucket=settings.minio_bucket,
        status=FileStatus.ACTIVE,
        uploaded_by=owner.id,
    )
    session.add(file)

    upload_session.file = file
    upload_session.status = UploadSessionStatus.FINALIZED
    upload_session.finalized_at = datetime.now(UTC)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File name already exists in this location",
        ) from exc

    session.refresh(file)
    return file


def upload_content(
    session: Session,
    owner: User,
    upload_session_id: uuid.UUID,
    data: bytes,
    content_type: str | None,
    storage: ObjectStorage,
) -> UploadSession:
    upload_session = get_upload_session_for_owner(session, upload_session_id, owner.id)
    if upload_session.status is UploadSessionStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload session already failed",
        )
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload session already finalized",
        )
    if len(data) > upload_session.expected_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded content exceeds expected size",
        )

    storage.put_object(
        bucket=settings.minio_bucket,
        object_key=upload_session.object_key,
        data=data,
        content_type=content_type or upload_session.content_type,
    )
    upload_session.content_type = content_type or upload_session.content_type
    upload_session.expected_size = len(data)
    upload_session.status = UploadSessionStatus.ACTIVE
    session.commit()
    session.refresh(upload_session)
    return upload_session


def fail_upload(session: Session, owner: User, payload: UploadFailRequest) -> UploadSession:
    upload_session = get_upload_session_for_owner(session, payload.upload_session_id, owner.id)
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload session already finalized",
        )

    upload_session.status = UploadSessionStatus.FAILED
    upload_session.failure_reason = payload.failure_reason
    session.commit()
    session.refresh(upload_session)
    return upload_session


def get_file_for_owner(session: Session, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
    file = session.scalar(select(File).where(File.id == file_id, File.owner_id == owner_id))
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file


def download_file_content(storage: ObjectStorage, file: File) -> bytes:
    stored_object = storage.get_object(file.storage_bucket, file.object_key)
    return stored_object.data


def delete_file(
    session: Session,
    file_id: uuid.UUID,
    owner_id: uuid.UUID,
    storage: ObjectStorage,
) -> None:
    file = get_file_for_owner(session, file_id, owner_id)
    storage.delete_object(file.storage_bucket, file.object_key)
    session.delete(file)
    session.commit()
