from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.application.ports import ObjectStoragePort, UnitOfWorkPort
from app.application.services.folders import get_folder_for_owner
from app.core.config import settings
from app.domain import ConflictError, NotFoundError, ValidationError
from app.domain.enums import FileStatus, UploadSessionStatus
from app.persistence.models import File, UploadSession
from app.schemas.file import UploadFailRequest, UploadFinalizeRequest, UploadInitRequest


def split_filename(filename: str) -> tuple[str, str]:
    stem, extension = os.path.splitext(filename)
    return stem or filename, extension


def normalize_filename(filename: str) -> str:
    return os.path.basename(filename.strip())


def resolve_filename_collision(uow: UnitOfWorkPort, folder_id: uuid.UUID, filename: str) -> str:
    normalized = normalize_filename(filename)
    stem, extension = split_filename(normalized)

    existing_filenames = uow.files.list_filenames_in_folder(folder_id)
    reserved_filenames = uow.files.list_reserved_filenames_in_folder(folder_id)
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
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    original_filename: str,
    data: bytes,
    content_type: str | None,
    storage: ObjectStoragePort,
    uploaded_by: uuid.UUID | None = None,
) -> File:
    folder = get_folder_for_owner(uow, folder_id, owner_id)
    resolved_filename = resolve_filename_collision(uow, folder.id, original_filename)
    object_id = uuid.uuid4()
    object_key = build_object_key(owner_id, folder.id, object_id, resolved_filename)
    extension = split_filename(resolved_filename)[1].lstrip(".") or None

    storage.put_object(
        bucket=settings.minio_bucket,
        object_key=object_key,
        data=data,
        content_type=content_type,
    )

    file = File(
        owner_id=owner_id,
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
        uploaded_by=uploaded_by or owner_id,
    )
    uow.files.add_file(file)
    try:
        uow.flush()
    except IntegrityError as exc:
        raise ConflictError("File name already exists in this location") from exc
    return file


def init_upload(
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    payload: UploadInitRequest,
) -> UploadSession:
    folder = get_folder_for_owner(uow, payload.folder_id, owner_id)
    resolved_filename = resolve_filename_collision(uow, folder.id, payload.filename)
    upload_session = UploadSession(
        owner_id=owner_id,
        folder_id=folder.id,
        original_filename=payload.filename,
        resolved_filename=resolved_filename,
        object_key=build_object_key(owner_id, folder.id, uuid.uuid4(), resolved_filename),
        content_type=payload.content_type,
        expected_size=payload.expected_size,
        status=UploadSessionStatus.PENDING,
    )
    uow.files.add_upload_session(upload_session)
    uow.flush()
    upload_session.object_key = build_object_key(
        owner_id,
        folder.id,
        upload_session.id,
        resolved_filename,
    )
    return upload_session


def get_upload_session_for_owner(
    uow: UnitOfWorkPort,
    upload_session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> UploadSession:
    upload_session = uow.files.get_upload_session_by_owner(upload_session_id, owner_id)
    if upload_session is None:
        raise NotFoundError("Upload session not found")
    return upload_session


def finalize_upload(
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    payload: UploadFinalizeRequest,
) -> File:
    upload_session = get_upload_session_for_owner(uow, payload.upload_session_id, owner_id)
    if upload_session.status is UploadSessionStatus.FAILED:
        raise ConflictError("Upload session already failed")
    if upload_session.status is UploadSessionStatus.PENDING:
        raise ConflictError("Upload content not received")
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise ConflictError("Upload session already finalized")

    extension = split_filename(upload_session.resolved_filename)[1].lstrip(".") or None
    file = File(
        owner_id=owner_id,
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
        uploaded_by=owner_id,
    )
    uow.files.add_file(file)

    upload_session.file = file
    upload_session.status = UploadSessionStatus.FINALIZED
    upload_session.finalized_at = datetime.now(UTC)

    try:
        uow.flush()
    except IntegrityError as exc:
        raise ConflictError("File name already exists in this location") from exc
    return file


def upload_content(
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    upload_session_id: uuid.UUID,
    data: bytes,
    content_type: str | None,
    storage: ObjectStoragePort,
) -> UploadSession:
    upload_session = get_upload_session_for_owner(uow, upload_session_id, owner_id)
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
    return upload_session


def fail_upload(
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    payload: UploadFailRequest,
) -> UploadSession:
    upload_session = get_upload_session_for_owner(uow, payload.upload_session_id, owner_id)
    if upload_session.status is UploadSessionStatus.FINALIZED:
        raise ConflictError("Upload session already finalized")

    upload_session.status = UploadSessionStatus.FAILED
    upload_session.failure_reason = payload.failure_reason
    return upload_session


def get_file_for_owner(uow: UnitOfWorkPort, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
    file = uow.files.get_by_owner(file_id, owner_id)
    if file is None:
        raise NotFoundError("File not found")
    return file


def rename_file(
    uow: UnitOfWorkPort,
    file_id: uuid.UUID,
    owner_id: uuid.UUID,
    filename: str,
) -> File:
    file = get_file_for_owner(uow, file_id, owner_id)
    normalized_filename = normalize_filename(filename)
    sibling_filenames = uow.files.list_filenames_in_folder(file.folder_id) - {file.stored_filename}
    if normalized_filename in sibling_filenames:
        raise ConflictError("File name already exists in this location")

    resolved_filename = normalized_filename
    extension = split_filename(resolved_filename)[1].lstrip(".") or None
    file.original_filename = normalized_filename
    file.stored_filename = resolved_filename
    file.extension = extension
    file.version += 1
    try:
        uow.flush()
    except IntegrityError as exc:
        raise ConflictError("File name already exists in this location") from exc
    return file


def move_file(
    uow: UnitOfWorkPort,
    file_id: uuid.UUID,
    owner_id: uuid.UUID,
    target_folder_id: uuid.UUID,
) -> File:
    file = get_file_for_owner(uow, file_id, owner_id)
    target_folder = get_folder_for_owner(uow, target_folder_id, owner_id)
    sibling_filenames = uow.files.list_filenames_in_folder(target_folder.id)
    if target_folder.id == file.folder_id:
        sibling_filenames -= {file.stored_filename}
    if file.stored_filename in sibling_filenames:
        raise ConflictError("File name already exists in this location")

    file.folder_id = target_folder.id
    file.version += 1
    try:
        uow.flush()
    except IntegrityError as exc:
        raise ConflictError("File name already exists in this location") from exc
    return file


def download_file_content(storage: ObjectStoragePort, file: File) -> bytes:
    stored = storage.get_object(file.storage_bucket, file.object_key)
    return stored.data


def prepare_file_delete(uow: UnitOfWorkPort, file_id: uuid.UUID, owner_id: uuid.UUID) -> File:
    return get_file_for_owner(uow, file_id, owner_id)


def delete_file_record(uow: UnitOfWorkPort, file: File) -> None:
    uow.delete(file)
