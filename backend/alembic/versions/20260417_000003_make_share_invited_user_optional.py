"""make share invited user optional

Revision ID: 20260417_000003
Revises: 20260417_000002
Create Date: 2026-04-17 00:03:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260417_000003"
down_revision = "20260417_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "share_invitations",
        "invited_user_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM share_invitations
            WHERE invited_user_id IS NULL
            """
        )
    )
    op.alter_column(
        "share_invitations",
        "invited_user_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
