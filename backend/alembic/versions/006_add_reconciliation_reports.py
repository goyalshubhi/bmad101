"""Add reconciliation_reports table

Revision ID: 006
Revises: 005
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("deck_id", sa.String(36), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("narrative_id", sa.String(36), sa.ForeignKey("narratives.id"), nullable=False),
        sa.Column("parent_report_id", sa.String(36), sa.ForeignKey("reconciliation_reports.id"), nullable=True),
        sa.Column("checks_json", sa.Text, nullable=True),
        sa.Column("figure_traces", sa.Text, nullable=True),
        sa.Column("assumption_actions_json", sa.Text, nullable=True),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("verified_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_reconciliation_reports_deck_id", "reconciliation_reports", ["deck_id"])
    op.create_index("ix_reconciliation_reports_narrative_id", "reconciliation_reports", ["narrative_id"])


def downgrade() -> None:
    op.drop_index("ix_reconciliation_reports_narrative_id", table_name="reconciliation_reports")
    op.drop_index("ix_reconciliation_reports_deck_id", table_name="reconciliation_reports")
    op.drop_table("reconciliation_reports")
