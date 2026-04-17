from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import FileStatus
from app.persistence.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.persistence.models.folder import Folder
    from app.persistence.models.upload_session import UploadSession
    from app.persistence.models.user import User


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
    uploader: Mapped[User] = relationship(
        foreign_keys=[uploaded_by],
        back_populates="uploaded_files",
    )
    upload_sessions: Mapped[list[UploadSession]] = relationship(back_populates="file")
