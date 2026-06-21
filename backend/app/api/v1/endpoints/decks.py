import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.deck import Deck

router = APIRouter()

TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class CreateDeckRequest(BaseModel):
    name: str


class CreateDeckResponse(BaseModel):
    id: str
    name: str


@router.post("/decks", response_model=CreateDeckResponse)
async def create_deck(
    body: CreateDeckRequest,
    db: AsyncSession = Depends(get_db),
):
    deck = Deck(name=body.name, user_id=TEMP_USER_ID)
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return CreateDeckResponse(id=str(deck.id), name=deck.name)
