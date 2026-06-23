"""Add deck_outputs table

Revision ID: 008
Revises: 007
Create Date: 2026-06-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deck_outputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("deck_id", sa.String(36), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("pptx_url", sa.String, nullable=True),
        sa.Column("rendered_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("deck_id", "version", name="uq_deck_outputs_deck_version"),
    )
    op.create_index("ix_deck_outputs_deck_id", "deck_outputs", ["deck_id"])


def downgrade() -> None:
    op.drop_index("ix_deck_outputs_deck_id", table_name="deck_outputs")
    op.drop_table("deck_outputs")
