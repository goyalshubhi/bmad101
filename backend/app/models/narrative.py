import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, Float, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Narrative(Base):
    __tablename__ = "narratives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decks.id"), nullable=False, index=True
    )
    question_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_sessions.id"), nullable=False
    )
    story_angle: Mapped[str] = mapped_column(String(50), nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    viz_recommendation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    assumptions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
