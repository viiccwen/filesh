from __future__ import annotations

from enum import StrEnum


class ShareMode(StrEnum):
    GUEST = "GUEST"
    USER_ONLY = "USER_ONLY"
    EMAIL_INVITATION = "EMAIL_INVITATION"


class PermissionLevel(StrEnum):
    VIEW_DOWNLOAD = "VIEW_DOWNLOAD"
    UPLOAD = "UPLOAD"
    DELETE = "DELETE"


class ResourceType(StrEnum):
    FILE = "FILE"
    FOLDER = "FOLDER"


class FileStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    DELETING = "DELETING"


class UploadSessionStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    FINALIZED = "FINALIZED"
