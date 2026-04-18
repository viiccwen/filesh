"""add share token ciphertext

Revision ID: 20260418_000004
Revises: 20260417_000003
Create Date: 2026-04-18 00:04:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260418_000004"
down_revision = "20260417_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "share_links",
        sa.Column("token_ciphertext", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("share_links", "token_ciphertext")
