from uuid import UUID

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: str
    template: str
    context: str
    suggestion_chips: list[str]
    tier: int


class QuestionsListResponse(BaseModel):
    session_id: str
    questions: list[QuestionResponse]


class AnswerInput(BaseModel):
    question_id: str
    text: str


class AnswerSubmitRequest(BaseModel):
    session_id: UUID
    answers: list[AnswerInput]


class ParsedAnswer(BaseModel):
    question_id: str
    raw_answer: str
    parsed_intent: str
    confidence: float
    defaulted: bool = False


class AnswerSubmitResponse(BaseModel):
    parsed: list[ParsedAnswer]
    ready_to_generate: bool


class QASummaryItem(BaseModel):
    id: str
    template: str
    answer: str
    parsed_intent: str
    confidence: float


class QASummaryResponse(BaseModel):
    questions: list[QASummaryItem]
