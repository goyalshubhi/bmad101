from uuid import UUID
from typing import Any

from pydantic import BaseModel


# --- Assumption schema ---

class AssumptionItem(BaseModel):
    text: str
    flag_type: str
    confidence: float
    source_reference: str


# --- Viz recommendation schema ---

class VizRecommendation(BaseModel):
    chart_type: str
    justification: str


# --- Per-narrative response ---

class NarrativeResponse(BaseModel):
    id: str
    story_angle: str
    narrative_text: str
    viz_recommendation: VizRecommendation | None = None
    assumptions: list[AssumptionItem] = []
    overall_confidence: float


# --- Request / Response schemas ---

class GenerateNarrativesRequest(BaseModel):
    session_id: UUID


class GenerateNarrativesResponse(BaseModel):
    narratives: list[NarrativeResponse]


class NarrativesListResponse(BaseModel):
    narratives: list[NarrativeResponse]


class SelectNarrativeRequest(BaseModel):
    narrative_id: UUID
    user_edits_text: str | None = None


class SelectNarrativeResponse(BaseModel):
    selection_id: str
    narrative_id: str
    user_edits_text: str | None
