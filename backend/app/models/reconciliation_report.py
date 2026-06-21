import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReconciliationReport(Base):
    __tablename__ = "reconciliation_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False, index=True
    )
    narrative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("narratives.id"), nullable=False, index=True
    )
    parent_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reconciliation_reports.id"), nullable=True
    )
    checks_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    figure_traces: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    assumption_actions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
