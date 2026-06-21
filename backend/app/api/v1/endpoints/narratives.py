import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ingest_job import IngestJob
from app.models.question_session import QuestionSession
from app.models.narrative import Narrative
from app.models.deck_selection import DeckSelection
from app.services.narratives.angle_detector import detect_angles
from app.services.narratives.template_engine import generate_narratives, compute_confidence
from app.services.narratives.assumption_extractor import extract_assumptions
from app.services.narratives.data_loader import load_dataframe
from app.api.v1.schemas.narratives import (
    GenerateNarrativesRequest,
    GenerateNarrativesResponse,
    NarrativeResponse,
    NarrativesListResponse,
    SelectNarrativeRequest,
    SelectNarrativeResponse,
)

router = APIRouter()


@router.post("/decks/{deck_id}/generate-narratives", response_model=GenerateNarrativesResponse)
async def generate_deck_narratives(
    deck_id: uuid.UUID,
    body: GenerateNarrativesRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch and validate question session
    result = await db.execute(
        select(QuestionSession)
        .where(QuestionSession.id == body.session_id, QuestionSession.deck_id == deck_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Question session not found")

    if session.answers_json is None:
        raise HTTPException(status_code=400, detail="Questions must be answered before generating narratives")

    parsed_answers = session.answers_json.get("parsed", [])
    ready = session.answers_json.get("ready_to_generate", False)
    if not ready:
        raise HTTPException(status_code=400, detail="Not all required questions have been answered")

    # 2. Fetch validated ingest job to get the file reference
    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id, IngestJob.validated_at.is_not(None))
        .order_by(IngestJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=400, detail="No validated ingest job found for this deck")

    object_key = job.file_url
    if not object_key:
        raise HTTPException(status_code=400, detail="Ingest job has no associated file")

    # 3. Build schema from ingest job (or derive from data)
    schema = job.schema_json or {"columns": []}

    # 4. Load data and run analysis in a background thread (CPU-bound)
    def _generate():
        df = load_dataframe(object_key)

        # Detect statistical angles using schema
        angles = detect_angles(df, schema)

        # Generate narrative variants with actual data values
        narratives_raw = generate_narratives(angles, parsed_answers, schema, df)

        # Extract assumptions
        assumptions = extract_assumptions(df, angles, narratives_raw, parsed_answers)

        # Compute confidence for each narrative
        for i, narr in enumerate(narratives_raw):
            if i < len(angles):
                narr["overall_confidence"] = compute_confidence(df, angles[i], parsed_answers)
            else:
                narr["overall_confidence"] = 0.0
            narr["assumptions"] = assumptions

        return narratives_raw, df

    narratives_raw, df = await asyncio.to_thread(_generate)

    # 5. Persist individual Narrative rows
    narrative_responses: list[NarrativeResponse] = []
    for narr in narratives_raw:
        narrative_row = Narrative(
            deck_id=deck_id,
            question_session_id=body.session_id,
            story_angle=narr["story_angle"],
            narrative_text=narr["narrative_text"],
            viz_recommendation=narr.get("viz_recommendation"),
            assumptions_json=narr.get("assumptions"),
            overall_confidence=narr.get("overall_confidence", 0.5),
        )
        db.add(narrative_row)
        await db.flush()

        narrative_responses.append(NarrativeResponse(
            id=str(narrative_row.id),
            story_angle=narr["story_angle"],
            narrative_text=narr["narrative_text"],
            viz_recommendation=narr.get("viz_recommendation"),
            assumptions=narr.get("assumptions", []),
            overall_confidence=narr.get("overall_confidence", 0.5),
        ))

    await db.commit()

    return GenerateNarrativesResponse(narratives=narrative_responses)


@router.get("/decks/{deck_id}/narratives", response_model=NarrativesListResponse)
async def list_deck_narratives(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all narratives for a deck, ordered by overall_confidence DESC."""
    result = await db.execute(
        select(Narrative)
        .where(Narrative.deck_id == deck_id)
        .order_by(Narrative.overall_confidence.desc())
    )
    rows = result.scalars().all()

    narratives = [
        NarrativeResponse(
            id=str(row.id),
            story_angle=row.story_angle,
            narrative_text=row.narrative_text,
            viz_recommendation=row.viz_recommendation,
            assumptions=row.assumptions_json or [],
            overall_confidence=row.overall_confidence,
        )
        for row in rows
    ]

    return NarrativesListResponse(narratives=narratives)


@router.post("/decks/{deck_id}/select-narrative", response_model=SelectNarrativeResponse)
async def select_narrative(
    deck_id: uuid.UUID,
    body: SelectNarrativeRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Narrative)
        .where(Narrative.id == body.narrative_id, Narrative.deck_id == deck_id)
    )
    narrative = result.scalar_one_or_none()
    if not narrative:
        raise HTTPException(status_code=404, detail="Narrative not found for this deck")

    result = await db.execute(
        select(DeckSelection)
        .where(DeckSelection.deck_id == deck_id)
        .with_for_update()
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.narrative_id = body.narrative_id
        existing.user_edits_text = body.user_edits_text
        selection = existing
    else:
        selection = DeckSelection(
            deck_id=deck_id,
            narrative_id=body.narrative_id,
            user_edits_text=body.user_edits_text,
        )
        db.add(selection)

    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(DeckSelection)
            .where(DeckSelection.deck_id == deck_id)
            .with_for_update()
        )
        selection = result.scalar_one()
        selection.narrative_id = body.narrative_id
        selection.user_edits_text = body.user_edits_text
        await db.commit()

    await db.refresh(selection)

    return SelectNarrativeResponse(
        selection_id=str(selection.id),
        narrative_id=str(selection.narrative_id),
        user_edits_text=selection.user_edits_text,
    )
