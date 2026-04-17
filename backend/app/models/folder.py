from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.upload_session import UploadSession
    from app.models.user import User


class Folder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("owner_id", "parent_id", "name", name="uq_folder_sibling_name"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    path_cache: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship(back_populates="folders")
    parent: Mapped[Folder | None] = relationship(
        remote_side="Folder.id",
        back_populates="children",
    )
    children: Mapped[list[Folder]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    files: Mapped[list[File]] = relationship(back_populates="folder", cascade="all, delete-orphan")
    upload_sessions: Mapped[list[UploadSession]] = relationship(back_populates="folder")
