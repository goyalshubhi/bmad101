import io
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.deck import Deck
from app.models.deck_output import DeckOutput
from app.models.deck_selection import DeckSelection
from app.models.ingest_job import IngestJob
from app.models.narrative import Narrative
from app.models.question_session import QuestionSession
from app.models.reconciliation_report import ReconciliationReport
from app.services.ingest.adapter_factory import get_adapter
from app.services.ingest.quality_checker import run_quality_checks
from app.services.storage import upload_file
from app.api.v1.schemas.ingest import (
    IngestResponse,
    IngestStatusResponse,
    AcknowledgeRequest,
    AcknowledgeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/decks/{deck_id}/ingest", response_model=IngestResponse)
async def ingest_file(
    deck_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Deck).where(Deck.id == deck_id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    filename = file.filename or "upload.csv"
    try:
        adapter = get_adapter(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    contents = await file.read()

    max_size = 100 * 1024 * 1024  # 100 MB
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 100 MB.")

    file_url = await upload_file(contents, filename)

    try:
        df = adapter.parse(io.BytesIO(contents))
        schema = adapter.detect_schema(df)
        quality_result = run_quality_checks(df)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse file. Ensure it is a valid format.")

    # Invalidate all downstream artifacts from prior ingestions.
    # Deletion order respects FK constraints (children first).
    await db.execute(delete(DeckOutput).where(DeckOutput.deck_id == deck_id))
    await db.execute(
        delete(ReconciliationReport).where(ReconciliationReport.deck_id == deck_id)
    )
    await db.execute(delete(DeckSelection).where(DeckSelection.deck_id == deck_id))
    await db.execute(delete(Narrative).where(Narrative.deck_id == deck_id))
    await db.execute(
        delete(QuestionSession).where(QuestionSession.deck_id == deck_id)
    )
    await db.execute(
        delete(AuditLog).where(
            AuditLog.deck_id == deck_id,
            AuditLog.action.in_([
                "verification_completed",
                "verification_run",
                "deck_rendered",
            ]),
        )
    )
    await db.execute(delete(IngestJob).where(IngestJob.deck_id == deck_id))
    logger.info("Invalidated downstream artifacts for deck %s on re-ingest", deck_id)

    status = quality_result["status"]

    validated_at = datetime.now(timezone.utc) if status == "CLEAN" else None
    job = IngestJob(
        deck_id=deck_id,
        file_url=file_url,
        schema_json=schema,
        quality_report=quality_result,
        status=status,
        validated_at=validated_at,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return IngestResponse(
        ingest_job_id=str(job.id),
        schema=schema,
        quality_report=quality_result,
        status=status,
    )


@router.get("/decks/{deck_id}/ingest-status", response_model=IngestStatusResponse)
async def get_ingest_status(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id)
        .order_by(IngestJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No ingest job found for this deck")

    return IngestStatusResponse(
        ingest_job_id=str(job.id),
        schema=job.schema_json,
        quality_report=job.quality_report,
        status=job.status,
        validated_at=job.validated_at,
    )


@router.post("/decks/{deck_id}/validate-acknowledge", response_model=AcknowledgeResponse)
async def validate_acknowledge(
    deck_id: uuid.UUID,
    body: AcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id)
        .order_by(IngestJob.created_at.desc())
        .with_for_update()
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No ingest job found for this deck")

    if job.status == "ISSUES_ACKNOWLEDGED":
        raise HTTPException(status_code=409, detail="Issues already acknowledged")

    if job.status not in ("CLEAN", "ISSUES_BLOCKING"):
        raise HTTPException(status_code=400, detail=f"Cannot acknowledge job with status: {job.status}")

    if job.status == "CLEAN" and job.validated_at is not None:
        return AcknowledgeResponse(
            status=job.status,
            validated_at=job.validated_at,
        )

    previous_status = job.status

    if job.status == "ISSUES_BLOCKING":
        job.status = "ISSUES_ACKNOWLEDGED"

    job.validated_at = datetime.now(timezone.utc)

    issues_count = len(job.quality_report.get("quality_issues", job.quality_report.get("issues", []))) if job.quality_report else 0

    audit_entry = AuditLog(
        deck_id=deck_id,
        user_id=body.user_id,
        action="data_validated",
        details={
            "ingest_job_id": str(job.id),
            "previous_status": previous_status,
            "acknowledged_issues_count": issues_count,
        },
    )
    db.add(audit_entry)
    await db.commit()

    return AcknowledgeResponse(
        status=job.status,
        validated_at=job.validated_at,
    )
