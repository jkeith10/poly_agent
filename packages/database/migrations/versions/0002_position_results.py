"""Add realized position results.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The original baseline migration was metadata-driven, so new installations may
    # already contain this column. Existing installations require the additive change.
    op.execute(
        "ALTER TABLE positions ADD COLUMN IF NOT EXISTS realized_pnl NUMERIC(24, 8)"
    )


def downgrade() -> None:
    op.drop_column("positions", "realized_pnl")
