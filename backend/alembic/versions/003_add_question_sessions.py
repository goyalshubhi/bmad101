"""Add question_sessions table

Revision ID: 003
Revises: 002
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deck_id", UUID(as_uuid=True), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("questions_json", JSONB, nullable=True),
        sa.Column("answers_json", JSONB, nullable=True),
        sa.Column("parent_session_id", UUID(as_uuid=True), sa.ForeignKey("question_sessions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_question_sessions_deck_id", "question_sessions", ["deck_id"])


def downgrade() -> None:
    op.drop_index("ix_question_sessions_deck_id", table_name="question_sessions")
    op.drop_table("question_sessions")
