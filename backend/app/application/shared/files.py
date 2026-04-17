from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.shared.folders import get_folder_for_owner
from app.core.config import settings
from app.core.events import CleanupEventType, EventPublisher, build_cleanup_event
from app.core.storage import ObjectStorage
from app.domain import ConflictError, NotFoundError, ValidationError
from app.models import File, FileStatus, UploadSession, UploadSessionStatus, User
from app.repositories import files as file_repository
from app.schemas.file import UploadFailRequest, UploadFinalizeRequest, UploadInitRequest


def split_filename(filename: str) -> tuple[str, str]:
    stem, extension = os.path.splitext(filename)
    return stem or filename, extension


def normalize_filename(filename: str) -> str:
    return os.path.basename(filename.strip())


def resolve_filename_collision(session: Session, folder_id: uuid.UUID, filename: str) -> str:
    normalized = normalize_filename(filename)
    stem, extension = split_filename(normalized)

    existing_filenames = file_repository.list_filenames_in_folder(session, folder_id)
    reserved_filenames = file_repository.list_reserved_filenames_in_folder(session, folder_id)
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


def create_file_in_folder(
    session: Session,
    owner: User,
    folder_id: uuid.UUID,
    original_filename: str,
    data: bytes,
    content_type: str | None,
    storage: ObjectStorage,
    uploaded_by: uuid.UUID | None = None,
) -> File:
    folder = get_folder_for_owner(session, folder_id, owner.id)
    resolved_filename = resolve_filename_collision(session, folder.id, original_filename)
    object_id = uuid.uuid4()
    object_key = build_object_key(owner.id, folder.id, object_id, resolved_filename)
    extension = split_filename(resolved_filename)[1].lstrip(".") or None

    storage.put_object(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type=content_type,
    )

    file = File(
        owner_id=owner.id,
        folder_id=folder.id,
        original_filename=original_filename,
        stored_filename=resolved_filename,
        extension=extension,
        content_type=content_type,
        size_bytes=len(data),
        checksum_sha256=hashlib.sha256(data).hexdigest(),
        object_key=object_key,
        storage_bucket=settings.minio_bucket,
        status=FileStatus.ACTIVE,
        uploaded_by=uploaded_by or owner.id,
    )
    file_repository.add_file(session, file)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("File name already exists in this location") from exc

    session.refresh(file)
    return file


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
    file_repository.add_upload_session(session, upload_session)
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
    upload_session = file_repository.get_upload_session_by_owner(
        session,
        upload_session_id,
        owner_id,
    )
    if upload_session is None:
        raise NotFoundError("Upload session not found")
    return upload_session


def finalize_upload(session: Session, owner: User, payload: UploadFinalizeRequest) -> File:
    upload_session = get_upload_session_for_owner(session, payload.upload_session_id, owner.id)
    if upload_session.status is UploadSessionStatus.FAILED:
        raise ConflictError("Upload session already failed")
    if upload_session.status is UploadSessionStatus.PENDING:
        raise ConflictError("Upload content not received")
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise ConflictError("Upload session already finalized")

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
    file_repository.add_file(session, file)

    upload_session.file = file
    upload_session.status = UploadSessionStatus.FINALIZED
    upload_session.finalized_at = datetime.now(UTC)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("File name already exists in this location") from exc

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
        raise ConflictError("Upload session already failed")
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise ConflictError("Upload session already finalized")
    if len(data) > upload_session.expected_size:
        raise ValidationError("Uploaded content exceeds expected size")

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


def fail_upload(
    session: Session,
    owner: User,
    payload: UploadFailRequest,
    event_publisher: EventPublisher,
) -> UploadSession:
    upload_session = get_upload_session_for_owner(session, payload.upload_session_id, owner.id)
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise ConflictError("Upload session already finalized")

    upload_session.status = UploadSessionStatus.FAILED
    upload_session.failure_reason = payload.failure_reason
    session.commit()
    session.refresh(upload_session)
    event_publisher.publish(
        settings.kafka_cleanup_topic,
        str(upload_session.id),
        build_cleanup_event(
            CleanupEventType.UPLOAD_FAILED,
            resource={"type": "upload_session", "id": str(upload_session.id)},
            objects=[
                {
                    "bucket": settings.minio_bucket,
                    "object_key": upload_session.object_key,
                }
            ],
            metadata={"owner_id": str(upload_session.owner_id)},
        ),
    )
    return upload_session


def get_file_for_owner(session: Session, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
    file = file_repository.get_file_by_owner(session, file_id, owner_id)
    if file is None:
        raise NotFoundError("File not found")
    return file


def rename_file(session: Session, file_id: uuid.UUID, owner_id: uuid.UUID, filename: str) -> File:
    file = get_file_for_owner(session, file_id, owner_id)
    normalized_filename = normalize_filename(filename)
    sibling_filenames = file_repository.list_filenames_in_folder(session, file.folder_id) - {
        file.stored_filename
    }
    if normalized_filename in sibling_filenames:
        raise ConflictError("File name already exists in this location")

    resolved_filename = normalized_filename
    extension = split_filename(resolved_filename)[1].lstrip(".") or None
    file.original_filename = normalized_filename
    file.stored_filename = resolved_filename
    file.extension = extension
    file.version += 1
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ConflictError("File name already exists in this location") from exc

    session.refresh(file)
    return file


def download_file_content(storage: ObjectStorage, file: File) -> bytes:
    stored_object = storage.get_object(file.storage_bucket, file.object_key)
    return stored_object.data


def delete_file(
    session: Session,
    file_id: uuid.UUID,
    owner_id: uuid.UUID,
    event_publisher: EventPublisher,
) -> None:
    file = get_file_for_owner(session, file_id, owner_id)
    event = build_cleanup_event(
        CleanupEventType.FILE_DELETE_REQUESTED,
        resource={"type": "file", "id": str(file.id)},
        objects=[{"bucket": file.storage_bucket, "object_key": file.object_key}],
        metadata={"owner_id": str(file.owner_id), "folder_id": str(file.folder_id)},
    )
    session.delete(file)
    session.commit()
    event_publisher.publish(settings.kafka_cleanup_topic, str(file.id), event)
