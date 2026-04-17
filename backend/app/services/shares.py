from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    File,
    Folder,
    ResourceType,
    ShareInvitation,
    ShareLink,
    ShareMode,
    User,
)
from app.schemas.share import ShareRead, ShareUpsertRequest
from app.services.files import get_file_for_owner
from app.services.folders import get_folder_for_owner, list_folder_contents


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
    session: Session,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> ShareLink | None:
    now = datetime.now(UTC)
    return session.scalar(
        select(ShareLink)
        .options(selectinload(ShareLink.invitations))
        .where(
            ShareLink.resource_type == resource_type,
            ShareLink.resource_id == resource_id,
            ShareLink.is_revoked.is_(False),
            (ShareLink.expires_at.is_(None) | (ShareLink.expires_at > now)),
        )
    )


def validate_share_resource(
    session: Session,
    owner: User,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> File | Folder:
    if resource_type is ResourceType.FILE:
        return get_file_for_owner(session, resource_id, owner.id)
    return get_folder_for_owner(session, resource_id, owner.id)


def resolve_invited_users(session: Session, emails: list[str]) -> list[User]:
    if not emails:
        return []

    normalized = sorted({email.lower() for email in emails})
    users = list(
        session.scalars(select(User).where(User.email.in_(normalized), User.is_active.is_(True)))
    )
    matched_emails = {user.email.lower() for user in users}
    missing = [email for email in normalized if email not in matched_emails]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invited users must be registered: {', '.join(missing)}",
        )
    return users


def assert_share_payload(payload: ShareUpsertRequest) -> list[User] | None:
    if payload.share_mode is ShareMode.EMAIL_INVITATION and not payload.invitation_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation emails are required for email invitation mode",
        )
    if payload.share_mode is not ShareMode.EMAIL_INVITATION and payload.invitation_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation emails are only allowed for email invitation mode",
        )
    return None


def to_share_read(share_link: ShareLink, raw_token: str) -> ShareRead:
    return ShareRead(
        id=share_link.id,
        resource_type=share_link.resource_type,
        resource_id=share_link.resource_id,
        share_mode=share_link.share_mode,
        permission_level=share_link.permission_level,
        expires_at=share_link.expires_at,
        is_revoked=share_link.is_revoked,
        invitation_emails=[inv.invited_email for inv in share_link.invitations],
        share_url=f"/s/{raw_token}",
    )


def create_share(
    session: Session,
    owner: User,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
    payload: ShareUpsertRequest,
) -> ShareRead:
    validate_share_resource(session, owner, resource_type, resource_id)
    assert_share_payload(payload)

    if get_active_share_for_resource(session, resource_type, resource_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active share link already exists",
        )

    invited_users = resolve_invited_users(
        session,
        [str(email) for email in payload.invitation_emails],
    )
    raw_token = generate_share_token()
    share_link = ShareLink(
        resource_type=resource_type,
        resource_id=resource_id,
        owner_id=owner.id,
        share_mode=payload.share_mode,
        permission_level=payload.permission_level,
        token_hash=hash_share_token(raw_token),
        expires_at=resolve_expiry(payload.expiry),
        is_revoked=False,
    )
    session.add(share_link)
    session.flush()

    for user in invited_users:
        session.add(
            ShareInvitation(
                share_link_id=share_link.id,
                invited_user_id=user.id,
                invited_email=user.email,
                created_at=datetime.now(UTC),
            )
        )

    session.commit()
    session.refresh(share_link)
    return to_share_read(share_link, raw_token)


def update_share(
    session: Session,
    owner: User,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
    payload: ShareUpsertRequest,
) -> ShareRead:
    validate_share_resource(session, owner, resource_type, resource_id)
    assert_share_payload(payload)

    share_link = get_active_share_for_resource(session, resource_type, resource_id)
    if share_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active share link not found",
        )

    invited_users = resolve_invited_users(
        session,
        [str(email) for email in payload.invitation_emails],
    )
    share_link.share_mode = payload.share_mode
    share_link.permission_level = payload.permission_level
    share_link.expires_at = resolve_expiry(payload.expiry)
    share_link.invitations.clear()
    session.flush()

    for user in invited_users:
        session.add(
            ShareInvitation(
                share_link_id=share_link.id,
                invited_user_id=user.id,
                invited_email=user.email,
                created_at=datetime.now(UTC),
            )
        )

    session.commit()
    session.refresh(share_link)
    return to_share_read(share_link, "[redacted]")


def get_share(
    session: Session,
    owner: User,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> ShareRead:
    validate_share_resource(session, owner, resource_type, resource_id)
    share_link = get_active_share_for_resource(session, resource_type, resource_id)
    if share_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active share link not found",
        )
    return to_share_read(share_link, "[redacted]")


def revoke_share(
    session: Session,
    owner: User,
    resource_type: ResourceType,
    resource_id: uuid.UUID,
) -> None:
    validate_share_resource(session, owner, resource_type, resource_id)
    share_link = get_active_share_for_resource(session, resource_type, resource_id)
    if share_link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active share link not found",
        )
    share_link.is_revoked = True
    session.commit()


def resolve_share_by_token(session: Session, token: str) -> ShareLink:
    share_link = session.scalar(
        select(ShareLink)
        .options(selectinload(ShareLink.invitations))
        .where(ShareLink.token_hash == hash_share_token(token))
    )
    if share_link is None or share_link.is_revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if share_link.expires_at is not None and share_link.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")
    return share_link


def authorize_share_access(share_link: ShareLink, requester: User | None) -> None:
    if share_link.share_mode is ShareMode.GUEST:
        return
    if requester is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Share access unauthorized",
        )
    if share_link.share_mode is ShareMode.USER_ONLY:
        return

    invited_emails = {inv.invited_email.lower() for inv in share_link.invitations}
    if requester.email.lower() not in invited_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Share access unauthorized",
        )


def get_shared_resource(
    session: Session,
    share_link: ShareLink,
) -> File | Folder:
    if share_link.resource_type is ResourceType.FILE:
        file = session.scalar(select(File).where(File.id == share_link.resource_id))
        if file is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        return file

    folder = session.scalar(select(Folder).where(Folder.id == share_link.resource_id))
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return folder


def get_shared_folder_contents(
    session: Session,
    share_link: ShareLink,
) -> tuple[Folder, list[Folder], list[File]]:
    if share_link.resource_type is not ResourceType.FOLDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shared resource is not a folder",
        )
    folder, folders, files = list_folder_contents(
        session,
        share_link.resource_id,
        share_link.owner_id,
    )
    return folder, folders, files
