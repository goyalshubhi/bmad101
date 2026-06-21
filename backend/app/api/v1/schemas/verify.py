from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class CheckResult(BaseModel):
    status: str
    expected: Any = None
    actual: Any = None
    fix_suggestion: str | None = None
    dismissed_reason: str | None = None
    dismissed_by: str | None = None
    dismissed_at: str | None = None


class ApplyFixParameters(BaseModel):
    row_ids: list[int]


class ApplyFixRequest(BaseModel):
    report_id: UUID
    check_name: str
    fix_type: Literal["exclude_rows"]
    parameters: ApplyFixParameters


class DismissCheckRequest(BaseModel):
    report_id: UUID
    check_name: str
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Reason must not be empty")
        return v.strip()


class AssumptionItem(BaseModel):
    text: str
    flag_type: str
    confidence: float
    source_reference: str


class AssumptionActionRequest(BaseModel):
    report_id: UUID
    assumption_index: int
    action: Literal["acknowledged", "signed_off", "rejected"]


class FigureTrace(BaseModel):
    figure_value: str
    source_rows: str
    formula: str
    match_status: str
    variance_pct: float


class VerifyResponse(BaseModel):
    report_id: str
    deck_id: str
    narrative_id: str
    passed: bool
    checks: dict[str, CheckResult]
    figure_traces: list[FigureTrace]
    assumptions: list[AssumptionItem] = []
    assumption_actions: list[dict[str, Any]] = []


class SourceRowsResponse(BaseModel):
    figure_value: str
    formula: str
    rows: list[dict[str, Any]]
