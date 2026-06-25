import asyncio
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
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
from app.services.render.pptx_builder import build_pptx, RenderContext, VerificationGateError
from app.services.storage import UPLOADS_DIR
from app.api.v1.schemas.render import RenderResponse, RenderStatusResponse

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


def _merge_qa(questions_json: list | None, answers_json: dict | list | None) -> list[dict]:
    questions = questions_json or []
    if isinstance(answers_json, dict):
        answers = answers_json.get("parsed", [])
    elif isinstance(answers_json, list):
        answers = answers_json
    else:
        answers = []
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


def _save_pptx(pptx_bytes: bytes, deck_id: uuid.UUID, version: int) -> str:
    os.makedirs(str(UPLOADS_DIR), exist_ok=True)
    filename = f"deck_v{version}.pptx"
    deck_dir = os.path.join(str(UPLOADS_DIR), str(deck_id))
    os.makedirs(deck_dir, exist_ok=True)
    file_path = os.path.join(deck_dir, filename)
    with open(file_path, "wb") as f:
        f.write(pptx_bytes)
    logger.info("PPTX saved: %s (%d bytes)", file_path, len(pptx_bytes))
    return file_path


def _resolve_pptx_path(deck_id: uuid.UUID, pptx_url: str) -> str | None:
    if pptx_url.startswith("local://"):
        key = pptx_url[len("local://"):]
    else:
        key = pptx_url

    file_path = os.path.join(str(UPLOADS_DIR), key)
    if os.path.isfile(file_path):
        return file_path

    # Fallback: scan deck directory for latest version
    deck_dir = os.path.join(str(UPLOADS_DIR), str(deck_id))
    if os.path.isdir(deck_dir):
        pptx_files = sorted(
            [f for f in os.listdir(deck_dir) if f.endswith(".pptx")],
            reverse=True,
        )
        if pptx_files:
            return os.path.join(deck_dir, pptx_files[0])

    return None


@router.post("/decks/{deck_id}/render", response_model=RenderResponse)
async def render_deck(
    deck_id: uuid.UUID,
    skip_verification: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    selection_result = await db.execute(
        select(DeckSelection).where(DeckSelection.deck_id == deck_id).limit(1)
    )
    selection = selection_result.scalar_one_or_none()
    if not selection:
        raise HTTPException(status_code=404, detail="No narrative selected for this deck")

    if not skip_verification:
        verification_result = await db.execute(
            select(AuditLog).where(
                AuditLog.deck_id == deck_id,
                AuditLog.action == "verification_completed",
                AuditLog.created_at >= selection.updated_at,
            ).order_by(AuditLog.created_at.desc()).limit(1)
        )
        if not verification_result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Verification must be completed before rendering")

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
        quality_issues = ingest_job.quality_report.get("quality_issues", ingest_job.quality_report.get("issues", []))

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
        narrative_confidence=float(narrative.overall_confidence or 0),
        story_angle=narrative.story_angle or "",
        viz_recommendation=narrative.viz_recommendation,
        assumptions=narrative.assumptions_json or [],
        questions_and_answers=qa_pairs,
        quality_notes=quality_issues,
        reconciliation_summary=recon_summary,
        verified_at=verified_at_str,
    )

    try:
        pptx_bytes = await asyncio.to_thread(build_pptx, context, skip_verification=skip_verification)
    except VerificationGateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception:
        logger.exception("PPTX build failed for deck %s", deck_id)
        raise HTTPException(status_code=500, detail="Failed to build PPTX")

    logger.info("PPTX built for deck %s: %d bytes", deck_id, len(pptx_bytes))

    max_retries = 3
    for attempt in range(max_retries):
        version_result = await db.execute(
            select(sa_func.count()).select_from(DeckOutput).where(DeckOutput.deck_id == deck_id)
        )
        existing_count = version_result.scalar() or 0
        version = existing_count + 1

        file_path = await asyncio.to_thread(_save_pptx, pptx_bytes, deck_id, version)
        pptx_url = f"local://{deck_id}/deck_v{version}.pptx"

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

        download_url = f"/api/v1/decks/{deck_id}/render/download"
        return RenderResponse(
            deck_id=str(deck_id),
            version=version,
            download_url=download_url,
            status="rendered",
        )


@router.get("/decks/{deck_id}/render/status", response_model=RenderStatusResponse)
async def render_status(deck_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    output_result = await db.execute(
        select(DeckOutput)
        .where(DeckOutput.deck_id == deck_id)
        .order_by(DeckOutput.rendered_at.desc())
        .limit(1)
    )
    deck_output = output_result.scalar_one_or_none()
    if not deck_output:
        return RenderStatusResponse(status="processing")
    return RenderStatusResponse(
        status="complete",
        download_url=f"/api/v1/decks/{deck_id}/render/download",
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

    file_path = _resolve_pptx_path(deck_id, pptx_url)
    if not file_path:
        raise HTTPException(status_code=404, detail="PPTX file not found on disk")

    return FileResponse(
        path=file_path,
        filename=f"deck_v{deck_output.version}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
