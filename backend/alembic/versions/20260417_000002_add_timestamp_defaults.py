"""add timestamp defaults

Revision ID: 20260417_000002
Revises: 20260417_000001
Create Date: 2026-04-17 21:10:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260417_000002"
down_revision = "20260417_000001"
branch_labels = None
depends_on = None


def _set_timestamp_defaults(table_name: str, include_updated_at: bool = True) -> None:
    op.alter_column(
        table_name,
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        existing_nullable=False,
    )
    if include_updated_at:
        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            existing_nullable=False,
        )


def _drop_timestamp_defaults(table_name: str, include_updated_at: bool = True) -> None:
    op.alter_column(
        table_name,
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_nullable=False,
    )
    if include_updated_at:
        op.alter_column(
            table_name,
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
            existing_nullable=False,
        )


def upgrade() -> None:
    _set_timestamp_defaults("users")
    _set_timestamp_defaults("folders")
    _set_timestamp_defaults("files")
    _set_timestamp_defaults("share_links")
    _set_timestamp_defaults("upload_sessions")
    _set_timestamp_defaults("share_invitations", include_updated_at=False)


def downgrade() -> None:
    _drop_timestamp_defaults("share_invitations", include_updated_at=False)
    _drop_timestamp_defaults("upload_sessions")
    _drop_timestamp_defaults("share_links")
    _drop_timestamp_defaults("files")
    _drop_timestamp_defaults("folders")
    _drop_timestamp_defaults("users")
