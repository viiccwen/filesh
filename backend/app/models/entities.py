from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    FileStatus,
    PermissionLevel,
    ResourceType,
    ShareMode,
    UploadSessionStatus,
)


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
    uploaded_files: Mapped[list[File]] = relationship(foreign_keys="File.uploaded_by")
    share_links: Mapped[list[ShareLink]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    upload_sessions: Mapped[list[UploadSession]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )


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


class File(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("folder_id", "stored_filename", name="uq_file_sibling_name"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    folder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"),
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255))
    extension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    object_key: Mapped[str] = mapped_column(String(512), index=True)
    storage_bucket: Mapped[str] = mapped_column(String(255))
    status: Mapped[FileStatus] = mapped_column(Enum(FileStatus, name="file_status_enum"))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    owner: Mapped[User] = relationship(back_populates="files", foreign_keys=[owner_id])
    folder: Mapped[Folder] = relationship(back_populates="files")
    uploader: Mapped[User] = relationship(foreign_keys=[uploaded_by])
    upload_sessions: Mapped[list[UploadSession]] = relationship(back_populates="file")


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
    invited_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    invited_email: Mapped[str] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    share_link: Mapped[ShareLink] = relationship(back_populates="invitations")


class UploadSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "upload_sessions"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    folder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("folders.id", ondelete="CASCADE"),
        index=True,
    )
    file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    resolved_filename: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_size: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[UploadSessionStatus] = mapped_column(
        Enum(UploadSessionStatus, name="upload_session_status_enum")
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[User] = relationship(back_populates="upload_sessions")
    folder: Mapped[Folder] = relationship(back_populates="upload_sessions")
    file: Mapped[File | None] = relationship(back_populates="upload_sessions")
