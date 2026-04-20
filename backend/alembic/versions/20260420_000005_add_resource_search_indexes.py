"""add resource search indexes

Revision ID: 20260420_000005
Revises: 20260418_000004
Create Date: 2026-04-20 22:10:00
"""

from __future__ import annotations

from alembic import op

revision = "20260420_000005"
down_revision = "20260418_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_files_owner_folder",
        "files",
        ["owner_id", "folder_id"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_folders_name_trgm
        ON folders
        USING gin (lower(name) gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_files_stored_filename_trgm
        ON files
        USING gin (lower(stored_filename) gin_trgm_ops)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_files_stored_filename_trgm")
        op.execute("DROP INDEX IF EXISTS ix_folders_name_trgm")

    op.drop_index("ix_files_owner_folder", table_name="files")
