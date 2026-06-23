"""Add deck_selections table

Revision ID: 005
Revises: 004
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deck_selections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("deck_id", sa.String(36), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("narrative_id", sa.String(36), sa.ForeignKey("narratives.id"), nullable=False),
        sa.Column("user_edits_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_deck_selections_deck_id", "deck_selections", ["deck_id"], unique=True)
    op.create_index("ix_deck_selections_narrative_id", "deck_selections", ["narrative_id"])


def downgrade() -> None:
    op.drop_index("ix_deck_selections_narrative_id", table_name="deck_selections")
    op.drop_index("ix_deck_selections_deck_id", table_name="deck_selections")
    op.drop_table("deck_selections")
