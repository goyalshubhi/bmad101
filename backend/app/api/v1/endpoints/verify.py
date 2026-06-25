import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.deck_selection import DeckSelection
from app.models.ingest_job import IngestJob
from app.models.narrative import Narrative
from app.models.reconciliation_report import ReconciliationReport
from app.services.narratives.data_loader import load_dataframe
from app.services.verify.figure_extractor import extract_figures
from app.services.verify.reconciliation_checks import run_all_checks
from app.services.verify.figure_tracer import trace_figures
from app.api.v1.schemas.verify import (
    VerifyResponse, CheckResult, FigureTrace, SourceRowsResponse,
    ApplyFixRequest, DismissCheckRequest,
    AssumptionActionRequest, AssumptionItem,
)

router = APIRouter()

VALID_ASSUMPTION_ACTIONS = {
    "PATTERN": {"acknowledged", "rejected"},
    "INFERRED": {"signed_off", "rejected"},
}


def _build_verify_response(
    report: ReconciliationReport,
    deck_id: uuid.UUID,
    narrative_assumptions: list | None,
) -> VerifyResponse:
    verified_at = None
    if report.verified_at:
        verified_at = report.verified_at.isoformat()
    return VerifyResponse(
        report_id=str(report.id),
        deck_id=str(deck_id),
        narrative_id=str(report.narrative_id),
        passed=report.passed,
        checks={k: CheckResult(**v) for k, v in (report.checks_json or {}).items()},
        figure_traces=[FigureTrace(**t) for t in (report.figure_traces or [])],
        assumptions=[AssumptionItem(**a) for a in (narrative_assumptions or [])],
        assumption_actions=report.assumption_actions_json or [],
        verified_at=verified_at,
    )


async def _load_narrative_assumptions(
    db: AsyncSession, narrative_id: uuid.UUID
) -> list:
    result = await db.execute(
        select(Narrative).where(Narrative.id == narrative_id)
    )
    narrative = result.scalar_one_or_none()
    return (narrative.assumptions_json if narrative else None) or []


@router.post("/decks/{deck_id}/verify", response_model=VerifyResponse)
async def verify_deck(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DeckSelection).where(DeckSelection.deck_id == deck_id)
    )
    selection = result.scalar_one_or_none()
    if not selection:
        raise HTTPException(status_code=404, detail="No narrative selected for this deck")

    result = await db.execute(
        select(Narrative).where(Narrative.id == selection.narrative_id)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(status_code=404, detail="Selected narrative not found")

    narrative_text = selection.user_edits_text or narrative.narrative_text
    if not narrative_text or not narrative_text.strip():
        raise HTTPException(status_code=400, detail="Narrative text is empty — nothing to verify")

    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id, IngestJob.validated_at.is_not(None))
        .order_by(IngestJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=400, detail="No validated ingest job found for this deck")

    if not job.file_url:
        raise HTTPException(status_code=400, detail="Ingest job has no associated file")

    schema = job.schema_json or {"columns": []}

    def _run_verification():
        df = load_dataframe(job.file_url)
        figures = extract_figures(narrative_text)
        checks = run_all_checks(figures, df, narrative_text, schema)
        traces = trace_figures(figures, df, schema)
        return figures, checks, traces

    try:
        figures, checks, traces = await asyncio.to_thread(_run_verification)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Source data file not found in storage")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to load source data: {e}")

    passed = all(c["status"] == "pass" for c in checks.values())

    report = ReconciliationReport(
        deck_id=deck_id,
        narrative_id=selection.narrative_id,
        checks_json=checks,
        figure_traces=traces,
        passed=passed,
    )
    db.add(report)

    try:
        audit_entry = AuditLog(
            deck_id=deck_id,
            user_id=None,
            action="verification_run",
            details={"report_id": str(report.id), "passed": passed},
        )
        db.add(audit_entry)
    except Exception as exc:
        _log.warning("Failed to create audit log for verification: %s", exc)

    await db.commit()
    await db.refresh(report)

    assumptions = narrative.assumptions_json or []

    return _build_verify_response(report, deck_id, assumptions)


@router.get("/decks/{deck_id}/verify", response_model=VerifyResponse)
async def get_latest_verify(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReconciliationReport)
        .where(ReconciliationReport.deck_id == deck_id)
        .order_by(ReconciliationReport.verified_at.desc())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="No verification report found")

    assumptions = await _load_narrative_assumptions(db, report.narrative_id)
    return _build_verify_response(report, deck_id, assumptions)


@router.get("/decks/{deck_id}/verify/source-rows", response_model=SourceRowsResponse)
async def get_source_rows(
    deck_id: uuid.UUID,
    figure_index: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReconciliationReport)
        .where(ReconciliationReport.deck_id == deck_id)
        .order_by(ReconciliationReport.verified_at.desc())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="No verification report found for this deck")

    traces = report.figure_traces or []
    if figure_index < 0 or figure_index >= len(traces):
        raise HTTPException(status_code=400, detail="Invalid figure index")

    trace = traces[figure_index]

    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id, IngestJob.validated_at.is_not(None))
        .order_by(IngestJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job or not job.file_url:
        raise HTTPException(status_code=400, detail="No validated ingest data available")

    def _parse_source_rows(source_rows_str: str, df_len: int) -> list[int]:
        import re
        cleaned = re.sub(r"^rows?\s+", "", source_rows_str.strip(), flags=re.IGNORECASE)
        if not cleaned:
            raise ValueError("No source row information available for this figure")

        indices: list[int] = []
        for part in cleaned.split(","):
            part = part.strip()
            if not part:
                continue
            range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
            if range_match:
                start = int(range_match.group(1)) - 1
                end = int(range_match.group(2))
                indices.extend(i for i in range(start, end) if 0 <= i < df_len)
            else:
                idx = int(part) - 1
                if 0 <= idx < df_len:
                    indices.append(idx)
        if not indices:
            raise ValueError(f"No valid row indices in source_rows: {source_rows_str}")
        return indices

    def _load_rows():
        df = load_dataframe(job.file_url)
        source_rows_str = trace.get("source_rows", "")
        if not source_rows_str:
            raise ValueError("No source row information available for this figure")

        indices = _parse_source_rows(source_rows_str, len(df))
        sliced = df.iloc[indices]
        return sliced.where(sliced.notna(), None).to_dict(orient="records")

    try:
        rows = await asyncio.to_thread(_load_rows)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Source data file not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to load source data: {e}")

    return SourceRowsResponse(
        figure_value=trace.get("figure_value", ""),
        formula=trace.get("formula", ""),
        rows=rows,
    )


VALID_CHECK_NAMES = {"check_a", "check_b", "check_c", "check_d", "check_e"}
PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000000"


_log = logging.getLogger(__name__)


@router.post("/decks/{deck_id}/verify/apply-fix", response_model=VerifyResponse)
async def apply_fix(
    deck_id: uuid.UUID,
    body: ApplyFixRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.check_name not in VALID_CHECK_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid check name: {body.check_name}")

    row_ids = body.parameters.row_ids
    if body.fix_type == "exclude_rows" and not row_ids:
        raise HTTPException(status_code=400, detail="row_ids must not be empty for exclude_rows fix")

    result = await db.execute(
        select(ReconciliationReport).where(
            ReconciliationReport.id == body.report_id,
            ReconciliationReport.deck_id == deck_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    result = await db.execute(
        select(DeckSelection).where(DeckSelection.deck_id == deck_id)
    )
    selection = result.scalar_one_or_none()
    if not selection:
        raise HTTPException(status_code=404, detail="No narrative selected for this deck")

    result = await db.execute(
        select(Narrative).where(Narrative.id == selection.narrative_id)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(status_code=404, detail="Selected narrative not found")

    narrative_text = selection.user_edits_text or narrative.narrative_text

    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id, IngestJob.validated_at.is_not(None))
        .order_by(IngestJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job or not job.file_url:
        raise HTTPException(status_code=400, detail="No validated ingest job found for this deck")

    schema = job.schema_json or {"columns": []}

    def _run_fix():
        df = load_dataframe(job.file_url)
        if row_ids:
            valid_ids = [i for i in row_ids if 0 <= i < len(df)]
            df = df.drop(index=valid_ids).reset_index(drop=True)
        figures = extract_figures(narrative_text)
        checks = run_all_checks(figures, df, narrative_text, schema)
        traces = trace_figures(figures, df, schema)
        return figures, checks, traces

    try:
        figures, checks, traces = await asyncio.to_thread(_run_fix)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Source data file not found in storage")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to process fix: {e}")

    passed = all(c["status"] != "fail" for c in checks.values())

    new_report = ReconciliationReport(
        deck_id=deck_id,
        narrative_id=selection.narrative_id,
        parent_report_id=report.id,
        checks_json=checks,
        figure_traces=traces,
        passed=passed,
    )
    db.add(new_report)

    try:
        audit_entry = AuditLog(
            deck_id=deck_id,
            user_id=None,
            action="fix_applied",
            details={
                "check_name": body.check_name,
                "fix_type": body.fix_type,
                "row_ids": row_ids,
                "parent_report_id": str(body.report_id),
            },
        )
        db.add(audit_entry)
    except Exception as exc:
        _log.warning("Failed to create audit log for apply-fix: %s", exc)

    await db.commit()
    await db.refresh(new_report)

    assumptions = await _load_narrative_assumptions(db, selection.narrative_id)

    return _build_verify_response(new_report, deck_id, assumptions)


@router.post("/decks/{deck_id}/verify/dismiss-check", response_model=VerifyResponse)
async def dismiss_check(
    deck_id: uuid.UUID,
    body: DismissCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.check_name not in VALID_CHECK_NAMES:
        raise HTTPException(status_code=400, detail=f"Invalid check name: {body.check_name}")

    result = await db.execute(
        select(ReconciliationReport)
        .where(
            ReconciliationReport.id == body.report_id,
            ReconciliationReport.deck_id == deck_id,
        )
        .with_for_update()
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    import json as _json
    checks = _json.loads(_json.dumps(report.checks_json or {}))
    check_data = checks.get(body.check_name)
    if not check_data:
        raise HTTPException(status_code=400, detail=f"Check {body.check_name} not found in report")

    if check_data.get("status") == "dismissed":
        raise HTTPException(status_code=400, detail="Check is already dismissed")
    if check_data.get("status") == "pass":
        raise HTTPException(status_code=400, detail="Cannot dismiss a passing check")

    from datetime import datetime, timezone
    check_data["status"] = "dismissed"
    check_data["dismissed_reason"] = body.reason
    check_data["dismissed_by"] = PLACEHOLDER_USER_ID
    check_data["dismissed_at"] = datetime.now(timezone.utc).isoformat()
    checks[body.check_name] = check_data

    report.checks_json = checks
    flag_modified(report, "checks_json")
    passed = all(c.get("status") != "fail" for c in checks.values())
    report.passed = passed

    try:
        audit_entry = AuditLog(
            deck_id=deck_id,
            user_id=None,
            action="check_dismissed",
            details={"check_name": body.check_name, "reason": body.reason},
        )
        db.add(audit_entry)
    except Exception as exc:
        _log.warning("Failed to create audit log for dismiss-check: %s", exc)

    await db.commit()
    await db.refresh(report)

    assumptions = await _load_narrative_assumptions(db, report.narrative_id)

    return _build_verify_response(report, deck_id, assumptions)


@router.post("/decks/{deck_id}/verify/assumption-action", response_model=VerifyResponse)
async def assumption_action(
    deck_id: uuid.UUID,
    body: AssumptionActionRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReconciliationReport)
        .where(
            ReconciliationReport.id == body.report_id,
            ReconciliationReport.deck_id == deck_id,
        )
        .with_for_update()
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    assumptions = await _load_narrative_assumptions(db, report.narrative_id)

    if body.assumption_index < 0 or body.assumption_index >= len(assumptions):
        raise HTTPException(status_code=400, detail="Invalid assumption index")

    assumption = assumptions[body.assumption_index]
    flag_type = assumption.get("flag_type", "")
    allowed_actions = VALID_ASSUMPTION_ACTIONS.get(flag_type)
    if not allowed_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Assumption with flag_type '{flag_type}' does not require any action",
        )
    if body.action not in allowed_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Action '{body.action}' not valid for flag_type '{flag_type}'. Allowed: {sorted(allowed_actions)}",
        )

    import json as _json
    actions = _json.loads(_json.dumps(report.assumption_actions_json or []))

    existing = next(
        (a for a in reversed(actions) if a.get("assumption_index") == body.assumption_index),
        None,
    )
    if existing and existing.get("action") in ("acknowledged", "signed_off"):
        raise HTTPException(
            status_code=400,
            detail=f"Assumption {body.assumption_index} already resolved with '{existing['action']}'",
        )

    from datetime import datetime, timezone
    actions.append({
        "assumption_index": body.assumption_index,
        "action": body.action,
        "user_id": PLACEHOLDER_USER_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    report.assumption_actions_json = actions
    flag_modified(report, "assumption_actions_json")

    try:
        audit_entry = AuditLog(
            deck_id=deck_id,
            user_id=None,
            action="assumption_action",
            details={
                "assumption_index": body.assumption_index,
                "action": body.action,
                "flag_type": flag_type,
            },
        )
        db.add(audit_entry)
    except Exception as exc:
        _log.warning("Failed to create audit log for assumption-action: %s", exc)

    await db.commit()
    await db.refresh(report)

    return _build_verify_response(report, deck_id, assumptions)


@router.post("/decks/{deck_id}/verify/complete")
async def verify_complete(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ReconciliationReport)
        .where(ReconciliationReport.deck_id == deck_id)
        .order_by(ReconciliationReport.verified_at.desc())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="No verification report found for this deck")

    checks = report.checks_json or {}
    failed_checks = [k for k, v in checks.items() if v.get("status") == "fail"]
    if failed_checks:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete verification: {len(failed_checks)} check(s) still failing",
        )

    assumptions = await _load_narrative_assumptions(db, report.narrative_id)
    actions = report.assumption_actions_json or []
    action_map = {}
    for a in actions:
        idx = a.get("assumption_index")
        action_map[idx] = a.get("action")

    unresolved = []
    for i, assumption in enumerate(assumptions):
        ft = assumption.get("flag_type", "")
        if ft in ("PATTERN", "INFERRED"):
            resolved_action = action_map.get(i)
            if resolved_action not in ("acknowledged", "signed_off", "rejected"):
                unresolved.append(i)

    if unresolved:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete verification: {len(unresolved)} assumption(s) unresolved",
        )

    try:
        audit_entry = AuditLog(
            deck_id=deck_id,
            user_id=None,
            action="verification_completed",
            details={
                "report_id": str(report.id),
                "checks_summary": {k: v.get("status") for k, v in checks.items()},
                "assumptions_count": len(assumptions),
                "actions_count": len(actions),
            },
        )
        db.add(audit_entry)
        await db.commit()
    except Exception as exc:
        _log.warning("Failed to create audit log for verify-complete: %s", exc)

    return {"status": "ok"}
