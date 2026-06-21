from fastapi import APIRouter

from app.api.v1.endpoints import health, ingest, questions, narratives, verify, render

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ingest.router, tags=["ingest"])
api_router.include_router(questions.router, tags=["questions"])
api_router.include_router(narratives.router, tags=["narratives"])
api_router.include_router(verify.router, tags=["verify"])
api_router.include_router(render.router, tags=["render"])
