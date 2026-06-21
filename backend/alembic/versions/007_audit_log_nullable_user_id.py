"""Make audit_log.user_id nullable for system-initiated actions

Revision ID: 007
Revises: 006
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("audit_log", "user_id", existing_type=UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM audit_log WHERE user_id IS NULL")
    op.alter_column("audit_log", "user_id", existing_type=UUID(as_uuid=True), nullable=False)
