"""Add narratives table

Revision ID: 004
Revises: 003
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "narratives",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deck_id", UUID(as_uuid=True), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("question_session_id", UUID(as_uuid=True), sa.ForeignKey("question_sessions.id"), nullable=False),
        sa.Column("story_angle", sa.String(50), nullable=False),
        sa.Column("narrative_text", sa.Text, nullable=False),
        sa.Column("viz_recommendation", JSONB, nullable=True),
        sa.Column("assumptions_json", JSONB, nullable=True),
        sa.Column("overall_confidence", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_narratives_deck_id", "narratives", ["deck_id"])


def downgrade() -> None:
    op.drop_index("ix_narratives_deck_id", table_name="narratives")
    op.drop_table("narratives")
