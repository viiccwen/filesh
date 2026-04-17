from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import ResourceType
from app.models import File, Folder, ShareLink, User


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


def add_share_link(session: Session, share_link: ShareLink) -> None:
    session.add(share_link)


def get_active_users_by_emails(session: Session, emails: list[str]) -> list[User]:
    if not emails:
        return []
    return list(
        session.scalars(select(User).where(User.email.in_(emails), User.is_active.is_(True)))
    )


def get_share_by_token_hash(session: Session, token_hash: str) -> ShareLink | None:
    return session.scalar(
        select(ShareLink)
        .options(selectinload(ShareLink.invitations))
        .where(ShareLink.token_hash == token_hash)
    )


def get_shared_file(session: Session, file_id: uuid.UUID) -> File | None:
    return session.scalar(select(File).where(File.id == file_id))


def get_shared_folder(session: Session, folder_id: uuid.UUID) -> Folder | None:
    return session.scalar(select(Folder).where(Folder.id == folder_id))
