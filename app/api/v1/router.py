from fastapi import APIRouter
from app.api.v1.endpoints import quiz

api_router = APIRouter()
api_router.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
