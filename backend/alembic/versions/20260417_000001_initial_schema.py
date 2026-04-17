"""initial schema

Revision ID: 20260417_000001
Revises:
Create Date: 2026-04-17 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260417_000001"
down_revision = None
branch_labels = None
depends_on = None


sharemodeenum = postgresql.ENUM(
    "GUEST",
    "USER_ONLY",
    "EMAIL_INVITATION",
    name="share_mode_enum",
    create_type=False,
)
permissionlevelenum = postgresql.ENUM(
    "VIEW_DOWNLOAD",
    "UPLOAD",
    "DELETE",
    name="permission_level_enum",
    create_type=False,
)
resourcetypeenum = postgresql.ENUM("FILE", "FOLDER", name="resource_type_enum", create_type=False)
filestatusenum = postgresql.ENUM(
    "PENDING",
    "ACTIVE",
    "FAILED",
    "DELETING",
    name="file_status_enum",
    create_type=False,
)
uploadsessionstatusenum = postgresql.ENUM(
    "PENDING",
    "ACTIVE",
    "FAILED",
    "FINALIZED",
    name="upload_session_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    sharemodeenum.create(bind, checkfirst=True)
    permissionlevelenum.create(bind, checkfirst=True)
    resourcetypeenum.create(bind, checkfirst=True)
    filestatusenum.create(bind, checkfirst=True)
    uploadsessionstatusenum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.create_table(
        "folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("path_cache", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "parent_id", "name", name="uq_folder_sibling_name"),
    )
    op.create_index(op.f("ix_folders_owner_id"), "folders", ["owner_id"], unique=False)
    op.create_index(op.f("ix_folders_parent_id"), "folders", ["parent_id"], unique=False)

    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=50), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("storage_bucket", sa.String(length=255), nullable=False),
        sa.Column("status", filestatusenum, nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("folder_id", "stored_filename", name="uq_file_sibling_name"),
    )
    op.create_index(op.f("ix_files_folder_id"), "files", ["folder_id"], unique=False)
    op.create_index(op.f("ix_files_owner_id"), "files", ["owner_id"], unique=False)
    op.create_index(op.f("ix_files_object_key"), "files", ["object_key"], unique=False)

    op.create_table(
        "share_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", resourcetypeenum, nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("share_mode", sharemodeenum, nullable=False),
        sa.Column("permission_level", permissionlevelenum, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_share_links_owner_id"), "share_links", ["owner_id"], unique=False)
    op.create_index(
        "ix_share_links_resource_lookup",
        "share_links",
        ["resource_type", "resource_id"],
        unique=False,
    )

    op.create_table(
        "share_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("share_link_id", sa.Uuid(), nullable=False),
        sa.Column("invited_user_id", sa.Uuid(), nullable=False),
        sa.Column("invited_email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invited_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["share_link_id"], ["share_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "share_link_id",
            "invited_email",
            name="uq_share_invitation_share_email",
        ),
    )
    op.create_index(
        op.f("ix_share_invitations_share_link_id"),
        "share_invitations",
        ["share_link_id"],
        unique=False,
    )

    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("resolved_filename", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("expected_size", sa.BigInteger(), nullable=False),
        sa.Column("status", uploadsessionstatusenum, nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_upload_sessions_owner_id"),
        "upload_sessions",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_upload_sessions_folder_id"),
        "upload_sessions",
        ["folder_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_sessions_folder_id"), table_name="upload_sessions")
    op.drop_index(op.f("ix_upload_sessions_owner_id"), table_name="upload_sessions")
    op.drop_table("upload_sessions")

    op.drop_index(op.f("ix_share_invitations_share_link_id"), table_name="share_invitations")
    op.drop_table("share_invitations")

    op.drop_index("ix_share_links_resource_lookup", table_name="share_links")
    op.drop_index(op.f("ix_share_links_owner_id"), table_name="share_links")
    op.drop_table("share_links")

    op.drop_index(op.f("ix_files_object_key"), table_name="files")
    op.drop_index(op.f("ix_files_owner_id"), table_name="files")
    op.drop_index(op.f("ix_files_folder_id"), table_name="files")
    op.drop_table("files")

    op.drop_index(op.f("ix_folders_parent_id"), table_name="folders")
    op.drop_index(op.f("ix_folders_owner_id"), table_name="folders")
    op.drop_table("folders")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    uploadsessionstatusenum.drop(bind, checkfirst=True)
    filestatusenum.drop(bind, checkfirst=True)
    resourcetypeenum.drop(bind, checkfirst=True)
    permissionlevelenum.drop(bind, checkfirst=True)
    sharemodeenum.drop(bind, checkfirst=True)
