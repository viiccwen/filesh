from __future__ import annotations

from app.domain.enums import (
    FileStatus,
    PermissionLevel,
    ResourceType,
    ShareMode,
    UploadSessionStatus,
)
from app.models import File, Folder, ShareInvitation, ShareLink, UploadSession, User
from app.models.base import Base


def test_model_exports_and_metadata_tables() -> None:
    assert User.__tablename__ == "users"
    assert Folder.__tablename__ == "folders"
    assert File.__tablename__ == "files"
    assert ShareLink.__tablename__ == "share_links"
    assert ShareInvitation.__tablename__ == "share_invitations"
    assert UploadSession.__tablename__ == "upload_sessions"
    assert sorted(Base.metadata.tables) == [
        "files",
        "folders",
        "share_invitations",
        "share_links",
        "upload_sessions",
        "users",
    ]


def test_model_enums_expose_expected_values() -> None:
    assert ShareMode.GUEST == "GUEST"
    assert ResourceType.FILE == "FILE"
    assert PermissionLevel.DELETE == "DELETE"
    assert FileStatus.ACTIVE == "ACTIVE"
    assert UploadSessionStatus.FINALIZED == "FINALIZED"
