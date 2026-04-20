from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.application.ports import SharesRepositoryPort
from app.domain.enums import ResourceType
from app.persistence.models import File, Folder, ShareLink, User


class SqlAlchemySharesRepository(SharesRepositoryPort):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active_for_resource(
        self,
        resource_type: ResourceType,
        resource_id: uuid.UUID,
    ) -> ShareLink | None:
        now = datetime.now(UTC)
        return self.session.scalar(
            select(ShareLink)
            .options(selectinload(ShareLink.invitations))
            .where(
                ShareLink.resource_type == resource_type,
                ShareLink.resource_id == resource_id,
                ShareLink.is_revoked.is_(False),
                (ShareLink.expires_at.is_(None) | (ShareLink.expires_at > now)),
            )
        )

    def add_share_link(self, share_link: ShareLink) -> None:
        self.session.add(share_link)

    def get_active_users_by_emails(self, emails: list[str]) -> list[User]:
        if not emails:
            return []
        return list(
            self.session.scalars(
                select(User).where(User.email.in_(emails), User.is_active.is_(True))
            )
        )

    def get_by_token_hash(self, token_hash: str) -> ShareLink | None:
        return self.session.scalar(
            select(ShareLink)
            .options(selectinload(ShareLink.invitations))
            .where(ShareLink.token_hash == token_hash)
        )

    def get_shared_file(self, file_id: uuid.UUID) -> File | None:
        return self.session.scalar(select(File).where(File.id == file_id))

    def get_shared_folder(self, folder_id: uuid.UUID) -> Folder | None:
        return self.session.scalar(select(Folder).where(Folder.id == folder_id))
