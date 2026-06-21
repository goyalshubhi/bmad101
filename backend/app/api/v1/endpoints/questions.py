import uuid

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.deck import Deck
from app.models.ingest_job import IngestJob
from app.models.question_session import QuestionSession
from app.services.questions.generator import generate_questions
from app.services.questions.parser import parse_answers
from app.api.v1.schemas.questions import (
    QuestionsListResponse,
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    QASummaryItem,
    QASummaryResponse,
)

router = APIRouter()


@router.get("/decks/{deck_id}/questions", response_model=QuestionsListResponse)
async def get_questions(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # H2: Check that the deck exists before proceeding
    deck_result = await db.execute(select(Deck).where(Deck.id == deck_id))
    if not deck_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Deck not found")

    result = await db.execute(
        select(IngestJob)
        .where(IngestJob.deck_id == deck_id, IngestJob.validated_at.is_not(None))
        .order_by(IngestJob.created_at.desc())
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=400, detail="No validated ingest job found for this deck. Complete data validation before generating questions.")

    # C1: Return existing unanswered session if one exists (idempotency)
    existing_result = await db.execute(
        select(QuestionSession)
        .where(
            QuestionSession.deck_id == deck_id,
            QuestionSession.answers_json.is_(None),
        )
        .order_by(QuestionSession.created_at.desc())
    )
    existing_session = existing_result.scalar_one_or_none()
    if existing_session:
        return QuestionsListResponse(
            session_id=str(existing_session.id),
            questions=existing_session.questions_json or [],
        )

    schema = job.schema_json or {}
    quality_report = job.quality_report or {}

    questions = generate_questions(schema, quality_report)

    session = QuestionSession(
        deck_id=deck_id,
        questions_json=questions,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return QuestionsListResponse(
        session_id=str(session.id),
        questions=questions,
    )


@router.post("/decks/{deck_id}/answer-questions", response_model=AnswerSubmitResponse)
async def answer_questions(
    deck_id: uuid.UUID,
    body: AnswerSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    # H2: Check that the deck exists before proceeding
    deck_result = await db.execute(select(Deck).where(Deck.id == deck_id))
    if not deck_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Deck not found")

    result = await db.execute(
        select(QuestionSession)
        .where(QuestionSession.id == body.session_id, QuestionSession.deck_id == deck_id)
        .with_for_update()
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Question session not found")

    if session.answers_json is not None:
        raise HTTPException(status_code=409, detail="Answers already submitted for this session")

    questions = session.questions_json or []
    answers_raw = [{"question_id": a.question_id, "text": a.text} for a in body.answers]

    parsed_result = parse_answers(questions, answers_raw)

    session.answers_json = parsed_result
    session.version = session.version + 1
    await db.commit()

    return AnswerSubmitResponse(
        parsed=parsed_result["parsed"],
        ready_to_generate=parsed_result["ready_to_generate"],
    )


@router.get("/decks/{deck_id}/qa-summary", response_model=QASummaryResponse)
async def get_qa_summary(
    deck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionSession)
        .where(
            QuestionSession.deck_id == deck_id,
            QuestionSession.answers_json.is_not(None),
        )
        .order_by(QuestionSession.created_at.desc())
    )
    session = result.scalar_one_or_none()
    if not session:
        return QASummaryResponse(questions=[])

    questions_json = session.questions_json or []
    answers_json = session.answers_json or {}
    parsed = answers_json.get("parsed", [])

    parsed_by_id = {p["question_id"]: p for p in parsed if "question_id" in p}

    items = []
    for q in questions_json:
        q_id = q.get("id", "")
        p = parsed_by_id.get(q_id, {})
        items.append(QASummaryItem(
            id=q_id,
            template=q.get("template", ""),
            answer=p.get("raw_answer", ""),
            parsed_intent=p.get("parsed_intent", ""),
            confidence=p.get("confidence", 0.0),
        ))

    return QASummaryResponse(questions=items)
