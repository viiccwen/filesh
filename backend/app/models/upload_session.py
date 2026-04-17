from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UploadSessionStatus

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.folder import Folder
    from app.models.user import User


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
