"""Add deck_outputs table

Revision ID: 008
Revises: 007
Create Date: 2026-06-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deck_outputs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deck_id", UUID(as_uuid=True), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("pptx_url", sa.String, nullable=True),
        sa.Column("rendered_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_deck_outputs_deck_id", "deck_outputs", ["deck_id"])
    op.create_unique_constraint("uq_deck_outputs_deck_version", "deck_outputs", ["deck_id", "version"])


def downgrade() -> None:
    op.drop_constraint("uq_deck_outputs_deck_version", "deck_outputs", type_="unique")
    op.drop_index("ix_deck_outputs_deck_id", table_name="deck_outputs")
    op.drop_table("deck_outputs")
