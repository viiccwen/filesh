from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.folder import Folder
    from app.models.share import ShareLink
    from app.models.upload_session import UploadSession


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    folders: Mapped[list[Folder]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    files: Mapped[list[File]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="File.owner_id",
    )
    uploaded_files: Mapped[list[File]] = relationship(
        foreign_keys="File.uploaded_by",
        back_populates="uploader",
    )
    share_links: Mapped[list[ShareLink]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    upload_sessions: Mapped[list[UploadSession]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
