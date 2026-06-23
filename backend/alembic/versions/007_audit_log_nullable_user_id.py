"""Make audit_log.user_id nullable for system-initiated actions

Revision ID: 007
Revises: 006
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM audit_log WHERE user_id IS NULL")
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(36), nullable=False)
