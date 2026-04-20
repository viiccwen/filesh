from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.application.mappers import to_share_read
from app.application.ports import ObjectStoragePort, UnitOfWorkPort
from app.application.services.files import create_file_in_folder, get_file_for_owner
from app.application.services.folders import (
    ROOT_FOLDER_NAME,
    create_folder,
    get_folder_for_owner,
    list_folder_contents,
)
from app.application.types import AuthenticatedUser
from app.core.security import decrypt_share_token, encrypt_share_token
from app.domain import AuthorizationError, ConflictError, GoneError, NotFoundError, ValidationError
from app.domain.enums import PermissionLevel, ResourceType, ShareMode
from app.persistence.models import File, Folder, ShareInvitation, ShareLink
from app.schemas.folder import FolderCreateRequest
from app.schemas.share import ShareRead, ShareUpsertRequest

PERMISSION_RANK = {
    PermissionLevel.VIEW_DOWNLOAD: 1,
    PermissionLevel.UPLOAD: 2,
    PermissionLevel.DELETE: 3,
}


def hash_share_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_share_token() -> str:
    return secrets.token_urlsafe(32)


def resolve_expiry(expiry: str) -> datetime | None:
    now = datetime.now(UTC)
    if expiry == "hour":
        return now + timedelta(hours=1)
    if expiry == "day":
        return now + timedelta(days=1)
    return None


def get_active_share_for_resource(
    uow: UnitOfWorkPort,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> ShareLink | None:
    return uow.shares.get_active_for_resource(resource_type, resource_id)


def validate_share_resource(
    uow: UnitOfWorkPort,
    owner_id: uuid.UUID,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> File | Folder:
    if resource_type is ResourceType.FILE:
        return get_file_for_owner(uow, resource_id, owner_id)
    return get_folder_for_owner(uow, resource_id, owner_id)


def resolve_invitations(
    uow: UnitOfWorkPort,
    emails: list[str],
) -> list[tuple[str, uuid.UUID | None]]:
    if not emails:
        return []

    normalized = sorted({email.lower() for email in emails})
    users = uow.shares.get_active_users_by_emails(normalized)
    users_by_email = {user.email.lower(): user for user in users}
    return [
        (email, users_by_email[email].id if email in users_by_email else None)
        for email in normalized
    ]


def assert_share_payload(payload: ShareUpsertRequest) -> None:
    if payload.share_mode is ShareMode.EMAIL_INVITATION and not payload.invitation_emails:
        raise ValidationError("Invitation emails are required for email invitation mode")
    if payload.share_mode is not ShareMode.EMAIL_INVITATION and payload.invitation_emails:
        raise ValidationError("Invitation emails are only allowed for email invitation mode")


def resolve_share_read_token(share_link: ShareLink) -> str:
    if share_link.token_ciphertext is None:
        return "[redacted]"

    decrypted_token = decrypt_share_token(share_link.token_ciphertext)
    if decrypted_token is None:
        return "[redacted]"

    return decrypted_token


def create_share(
    uow: UnitOfWorkPort,
    owner: AuthenticatedUser,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
    payload: ShareUpsertRequest,
) -> ShareRead:
    validate_share_resource(uow, owner.id, resource_type, resource_id)
    assert_share_payload(payload)

    if get_active_share_for_resource(uow, resource_type, resource_id) is not None:
        raise ConflictError("Active share link already exists")

    invitations = resolve_invitations(uow, [str(email) for email in payload.invitation_emails])
    raw_token = generate_share_token()
    share_link = ShareLink(
        resource_type=resource_type,
        resource_id=resource_id,
        owner_id=owner.id,
        share_mode=payload.share_mode,
        permission_level=payload.permission_level,
        token_hash=hash_share_token(raw_token),
        token_ciphertext=encrypt_share_token(raw_token),
        expires_at=resolve_expiry(payload.expiry),
        is_revoked=False,
    )
    uow.shares.add_share_link(share_link)
    uow.flush()

    for invited_email, invited_user_id in invitations:
        uow.add(
            ShareInvitation(
                share_link_id=share_link.id,
                invited_user_id=invited_user_id,
                invited_email=invited_email,
                created_at=datetime.now(UTC),
            )
        )

    uow.flush()
    return to_share_read(share_link, raw_token)


def update_share(
    uow: UnitOfWorkPort,
    owner: AuthenticatedUser,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
    payload: ShareUpsertRequest,
) -> ShareRead:
    validate_share_resource(uow, owner.id, resource_type, resource_id)
    assert_share_payload(payload)

    share_link = get_active_share_for_resource(uow, resource_type, resource_id)
    if share_link is None:
        raise NotFoundError("Active share link not found")

    invitations = resolve_invitations(uow, [str(email) for email in payload.invitation_emails])
    share_link.share_mode = payload.share_mode
    share_link.permission_level = payload.permission_level
    share_link.expires_at = resolve_expiry(payload.expiry)
    share_link.invitations.clear()
    uow.flush()

    for invited_email, invited_user_id in invitations:
        uow.add(
            ShareInvitation(
                share_link_id=share_link.id,
                invited_user_id=invited_user_id,
                invited_email=invited_email,
                created_at=datetime.now(UTC),
            )
        )

    uow.flush()
    return to_share_read(share_link, resolve_share_read_token(share_link))


def get_share(
    uow: UnitOfWorkPort,
    owner: AuthenticatedUser,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> ShareRead:
    validate_share_resource(uow, owner.id, resource_type, resource_id)
    share_link = get_active_share_for_resource(uow, resource_type, resource_id)
    if share_link is None:
        raise NotFoundError("Active share link not found")
    return to_share_read(share_link, resolve_share_read_token(share_link))


def revoke_share(
    uow: UnitOfWorkPort,
    owner: AuthenticatedUser,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> None:
    validate_share_resource(uow, owner.id, resource_type, resource_id)
    share_link = get_active_share_for_resource(uow, resource_type, resource_id)
    if share_link is None:
        raise NotFoundError("Active share link not found")
    share_link.is_revoked = True


def resolve_share_by_token(uow: UnitOfWorkPort, token: str) -> ShareLink:
    share_link = uow.shares.get_by_token_hash(hash_share_token(token))
    if share_link is None or share_link.is_revoked:
        raise NotFoundError("Share link not found")
    if share_link.expires_at is not None and share_link.expires_at <= datetime.now(UTC):
        raise GoneError("Share link expired")
    return share_link


def authorize_share_access(share_link: ShareLink, requester: AuthenticatedUser | None) -> None:
    if share_link.share_mode is ShareMode.GUEST:
        return
    if requester is None:
        raise AuthorizationError("Share access unauthorized")
    if share_link.share_mode is ShareMode.USER_ONLY:
        return

    invited_emails = {inv.invited_email.lower() for inv in share_link.invitations}
    if requester.email.lower() not in invited_emails:
        raise AuthorizationError("Share access unauthorized")


def authorize_share_permission(
    share_link: ShareLink,
    requester: AuthenticatedUser | None,
    required_permission: PermissionLevel,
) -> None:
    authorize_share_access(share_link, requester)
    if PERMISSION_RANK[share_link.permission_level] < PERMISSION_RANK[required_permission]:
        raise AuthorizationError("Share permission denied")


def get_shared_resource(uow: UnitOfWorkPort, share_link: ShareLink) -> File | Folder:
    if share_link.resource_type is ResourceType.FILE:
        file = uow.shares.get_shared_file(share_link.resource_id)
        if file is None:
            raise NotFoundError("Resource not found")
        return file

    folder = uow.shares.get_shared_folder(share_link.resource_id)
    if folder is None:
        raise NotFoundError("Resource not found")
    return folder


def is_folder_within_shared_tree(root_folder: Folder, candidate_folder: Folder) -> bool:
    if root_folder.owner_id != candidate_folder.owner_id:
        return False
    if root_folder.path_cache == "/":
        return True
    if candidate_folder.path_cache is None or root_folder.path_cache is None:
        return False
    return (
        candidate_folder.path_cache == root_folder.path_cache
        or candidate_folder.path_cache.startswith(f"{root_folder.path_cache}/")
    )


def get_shared_folder_target(
    uow: UnitOfWorkPort,
    share_link: ShareLink,
    folder_id: uuid.UUID | None = None,
) -> Folder:
    if share_link.resource_type is not ResourceType.FOLDER:
        raise ValidationError("Shared resource is not a folder")

    root_folder = uow.folders.get_by_id(share_link.resource_id)
    if root_folder is None:
        raise NotFoundError("Resource not found")
    if folder_id is None or folder_id == root_folder.id:
        return root_folder

    folder = uow.folders.get_by_owner(folder_id, share_link.owner_id)
    if folder is None or not is_folder_within_shared_tree(root_folder, folder):
        raise NotFoundError("Resource not found")
    return folder


def get_shared_file_target(uow: UnitOfWorkPort, share_link: ShareLink, file_id: uuid.UUID) -> File:
    file = uow.files.get_by_owner(file_id, share_link.owner_id)
    if file is None:
        raise NotFoundError("Resource not found")

    folder = uow.folders.get_by_id(file.folder_id)
    root_folder = get_shared_folder_target(uow, share_link)
    if folder is None or not is_folder_within_shared_tree(root_folder, folder):
        raise NotFoundError("Resource not found")
    return file


def resolve_effective_file_share(
    uow: UnitOfWorkPort,
    folder_share_link: ShareLink,
    file: File,
) -> ShareLink:
    file_share = get_active_share_for_resource(uow, ResourceType.FILE, file.id)
    if file_share is not None:
        return file_share
    return folder_share_link


def resolve_shared_file_action(
    uow: UnitOfWorkPort,
    share_link: ShareLink,
    file_id: uuid.UUID,
    requester: AuthenticatedUser | None,
    required_permission: PermissionLevel,
) -> tuple[File, ShareLink]:
    file = get_shared_file_target(uow, share_link, file_id)
    effective_share = resolve_effective_file_share(uow, share_link, file)
    authorize_share_permission(effective_share, requester, required_permission)
    return file, effective_share


def get_shared_folder_contents_for_target(
    uow: UnitOfWorkPort,
    share_link: ShareLink,
    requester: AuthenticatedUser | None,
    folder_id: uuid.UUID | None = None,
) -> tuple[Folder, list[Folder], list[File]]:
    authorize_share_permission(share_link, requester, PermissionLevel.VIEW_DOWNLOAD)
    folder = get_shared_folder_target(uow, share_link, folder_id)
    return list_folder_contents(uow, folder.id, share_link.owner_id)


def create_shared_subfolder(
    uow: UnitOfWorkPort,
    share_link: ShareLink,
    requester: AuthenticatedUser | None,
    payload: FolderCreateRequest,
) -> Folder:
    authorize_share_permission(share_link, requester, PermissionLevel.UPLOAD)
    parent_folder = get_shared_folder_target(uow, share_link, payload.parent_id)
    if payload.name == ROOT_FOLDER_NAME:
        raise ValidationError("Folder name is reserved")
    folder = create_folder(
        uow,
        share_link.owner_id,
        FolderCreateRequest(name=payload.name, parent_id=parent_folder.id),
    )
    uow.flush()
    return folder


def create_shared_file(
    uow: UnitOfWorkPort,
    share_link: ShareLink,
    requester: AuthenticatedUser | None,
    filename: str,
    data: bytes,
    content_type: str | None,
    storage: ObjectStoragePort,
    folder_id: uuid.UUID | None = None,
) -> File:
    authorize_share_permission(share_link, requester, PermissionLevel.UPLOAD)
    target_folder = get_shared_folder_target(uow, share_link, folder_id)
    return create_file_in_folder(
        uow,
        share_link.owner_id,
        target_folder.id,
        filename,
        data,
        content_type,
        storage,
        uploaded_by=requester.id if requester is not None else share_link.owner_id,
    )
