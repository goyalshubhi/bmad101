from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    severity: str
    description: str
    count: int
    sample_rows: list[int] = []


class IngestResponse(BaseModel):
    model_config = {"populate_by_name": True}

    ingest_job_id: str
    schema_info: dict = Field(alias="schema")
    quality_report: dict
    status: str


class IngestStatusResponse(BaseModel):
    model_config = {"populate_by_name": True}

    ingest_job_id: str
    schema_info: dict | None = Field(alias="schema", default=None)
    quality_report: dict | None = None
    status: str
    validated_at: datetime | None = None


class AcknowledgeRequest(BaseModel):
    user_id: UUID


class AcknowledgeResponse(BaseModel):
    status: str
    validated_at: datetime | None = None
