import asyncio
import logging
import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func as sa_func
from sqlalchemy.exc import IntegrityError
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
from app.services.render.pptx_builder import build_pptx, RenderContext
from app.services.storage import upload_file, download_file
from app.api.v1.schemas.render import RenderResponse

logger = logging.getLogger(__name__)

router = APIRouter()

PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000000"


def _extract_filename(file_url: str | None) -> str:
    if not file_url:
        return "unknown"
    parts = file_url.rstrip("/").split("/")
    return parts[-1] if parts else "unknown"


def _build_reconciliation_summary(checks_json: dict | list | None) -> dict:
    if not checks_json:
        return {"total_checks": 0, "passed_count": 0, "failed_count": 0, "dismissed_count": 0}

    items = checks_json.values() if isinstance(checks_json, dict) else checks_json
    passed = 0
    failed = 0
    dismissed = 0
    for check in items:
        status = check.get("status", "pass") if isinstance(check, dict) else check
        if status == "pass":
            passed += 1
        elif status == "dismissed":
            dismissed += 1
        else:
            failed += 1

    total = len(checks_json)
    return {
        "total_checks": total,
        "passed_count": passed,
        "failed_count": failed,
        "dismissed_count": dismissed,
    }


def _merge_qa(questions_json: list | None, answers_json: list | None) -> list[dict]:
    questions = questions_json or []
    answers = answers_json or []
    answer_map = {}
    for a in answers:
        if isinstance(a, dict):
            qid = a.get("question_id")
            if qid is not None:
                answer_map[qid] = a.get("raw_answer", "")

    result = []
    for q in questions:
        if isinstance(q, dict):
            qid = q.get("id")
            result.append({
                "question": q.get("template", q.get("context", "")),
                "answer": answer_map.get(qid, "Not answered"),
            })
    return result


@router.post("/decks/{deck_id}/render", response_model=RenderResponse)
async def render_deck(deck_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    verification_result = await db.execute(
        select(AuditLog).where(
            AuditLog.deck_id == deck_id,
            AuditLog.action == "verification_completed",
        ).limit(1)
    )
    if not verification_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Verification must be completed before rendering")

    selection_result = await db.execute(
        select(DeckSelection).where(DeckSelection.deck_id == deck_id)
    )
    selection = selection_result.scalar_one_or_none()
    if not selection:
        raise HTTPException(status_code=404, detail="No narrative selected for this deck")

    narrative_result = await db.execute(
        select(Narrative).where(Narrative.id == selection.narrative_id)
    )
    narrative = narrative_result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(status_code=404, detail="Selected narrative not found")

    final_text = selection.user_edits_text or narrative.narrative_text

    deck_result = await db.execute(select(Deck).where(Deck.id == deck_id))
    deck = deck_result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    qs_result = await db.execute(
        select(QuestionSession)
        .where(QuestionSession.deck_id == deck_id)
        .order_by(QuestionSession.created_at.desc())
        .limit(1)
    )
    question_session = qs_result.scalar_one_or_none()

    ij_result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id)
        .order_by(IngestJob.created_at.desc())
        .limit(1)
    )
    ingest_job = ij_result.scalar_one_or_none()

    report_result = await db.execute(
        select(ReconciliationReport)
        .where(ReconciliationReport.deck_id == deck_id)
        .order_by(ReconciliationReport.verified_at.desc())
        .limit(1)
    )
    report = report_result.scalar_one_or_none()

    data_source_filename = _extract_filename(ingest_job.file_url if ingest_job else None)
    quality_issues = []
    if ingest_job and isinstance(ingest_job.quality_report, dict):
        quality_issues = ingest_job.quality_report.get("issues", [])

    qa_pairs = _merge_qa(
        question_session.questions_json if question_session else None,
        question_session.answers_json if question_session else None,
    )

    recon_summary = _build_reconciliation_summary(report.checks_json if report else None)
    verified_at_str = ""
    if report and report.verified_at:
        verified_at_str = report.verified_at.isoformat()

    context = RenderContext(
        deck_name=deck.name,
        data_source_filename=data_source_filename,
        narrative_text=final_text,
        narrative_confidence=narrative.overall_confidence,
        story_angle=narrative.story_angle,
        viz_recommendation=narrative.viz_recommendation,
        assumptions=narrative.assumptions_json or [],
        questions_and_answers=qa_pairs,
        quality_notes=quality_issues,
        reconciliation_summary=recon_summary,
        verified_at=verified_at_str,
    )

    pptx_bytes = await asyncio.to_thread(build_pptx, context)

    max_retries = 3
    for attempt in range(max_retries):
        version_result = await db.execute(
            select(sa_func.count()).select_from(DeckOutput).where(DeckOutput.deck_id == deck_id)
        )
        existing_count = version_result.scalar() or 0
        version = existing_count + 1

        pptx_url = await upload_file(pptx_bytes, f"{deck_id}/deck_v{version}.pptx")

        deck_output = DeckOutput(
            deck_id=deck_id,
            version=version,
            pptx_url=pptx_url,
        )
        db.add(deck_output)

        try:
            audit_entry = AuditLog(
                deck_id=deck_id,
                user_id=uuid.UUID(PLACEHOLDER_USER_ID),
                action="deck_rendered",
                details={
                    "version": version,
                    "narrative_id": str(narrative.id),
                    "deck_output_id": str(deck_output.id),
                },
            )
            db.add(audit_entry)
        except Exception:
            logger.warning("Failed to create audit log for deck_rendered", exc_info=True)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            if attempt < max_retries - 1:
                logger.info("Version conflict on deck %s, retrying (attempt %d)", deck_id, attempt + 1)
                continue
            raise HTTPException(status_code=409, detail="Version conflict after retries, please try again")

        return RenderResponse(
            deck_id=str(deck_id),
            version=version,
            pptx_url=pptx_url,
            status="rendered",
        )


@router.get("/decks/{deck_id}/render/download")
async def download_deck(deck_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    output_result = await db.execute(
        select(DeckOutput)
        .where(DeckOutput.deck_id == deck_id)
        .order_by(DeckOutput.rendered_at.desc())
        .limit(1)
    )
    deck_output = output_result.scalar_one_or_none()
    if not deck_output:
        raise HTTPException(status_code=404, detail="No rendered deck found")

    pptx_url = deck_output.pptx_url
    if not pptx_url:
        raise HTTPException(status_code=404, detail="Rendered deck has no storage URL")

    if pptx_url.startswith("s3://"):
        parts = pptx_url.split("/", 3)
        object_key = parts[3] if len(parts) > 3 else ""
        if not object_key:
            raise HTTPException(status_code=500, detail="Malformed storage URL")
    else:
        object_key = pptx_url

    try:
        pptx_bytes = await asyncio.to_thread(download_file, object_key)
    except ClientError:
        logger.exception("S3 download failed for key %s", object_key)
        raise HTTPException(status_code=502, detail="Failed to retrieve file from storage")

    if pptx_bytes is None:
        raise HTTPException(status_code=404, detail="PPTX file not found in storage")

    filename = f"deck_v{deck_output.version}.pptx"

    async def _stream():
        yield pptx_bytes

    return StreamingResponse(
        _stream(),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pptx_bytes)),
        },
    )
