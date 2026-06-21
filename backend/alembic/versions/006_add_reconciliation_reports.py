"""Add reconciliation_reports table

Revision ID: 006
Revises: 005
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deck_id", UUID(as_uuid=True), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("narrative_id", UUID(as_uuid=True), sa.ForeignKey("narratives.id"), nullable=False),
        sa.Column("parent_report_id", UUID(as_uuid=True), sa.ForeignKey("reconciliation_reports.id"), nullable=True),
        sa.Column("checks_json", JSONB, nullable=True),
        sa.Column("figure_traces", JSONB, nullable=True),
        sa.Column("assumption_actions_json", JSONB, nullable=True),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("verified_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_reconciliation_reports_deck_id", "reconciliation_reports", ["deck_id"])
    op.create_index("ix_reconciliation_reports_narrative_id", "reconciliation_reports", ["narrative_id"])


def downgrade() -> None:
    op.drop_index("ix_reconciliation_reports_narrative_id", table_name="reconciliation_reports")
    op.drop_index("ix_reconciliation_reports_deck_id", table_name="reconciliation_reports")
    op.drop_table("reconciliation_reports")
