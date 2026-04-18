from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import PermissionLevel, ResourceType, ShareMode
from app.persistence.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.persistence.models.user import User


class ShareLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "share_links"
    __table_args__ = (Index("ix_share_links_resource_lookup", "resource_type", "resource_id"),)

    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, name="resource_type_enum")
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    share_mode: Mapped[ShareMode] = mapped_column(Enum(ShareMode, name="share_mode_enum"))
    permission_level: Mapped[PermissionLevel] = mapped_column(
        Enum(PermissionLevel, name="permission_level_enum")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_ciphertext: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner: Mapped[User] = relationship(back_populates="share_links")
    invitations: Mapped[list[ShareInvitation]] = relationship(
        back_populates="share_link",
        cascade="all, delete-orphan",
    )


class ShareInvitation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "share_invitations"
    __table_args__ = (
        UniqueConstraint("share_link_id", "invited_email", name="uq_share_invitation_share_email"),
    )

    share_link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("share_links.id", ondelete="CASCADE"),
        index=True,
    )
    invited_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    invited_email: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    share_link: Mapped[ShareLink] = relationship(back_populates="invitations")
