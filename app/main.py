from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.database import engine, Base

# Import models so Alembic / Base.metadata can see them
import app.models.quiz  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: create tables if they don't exist (dev convenience).
    # In production use Alembic migrations instead.
    if not settings.is_production:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # On shutdown: dispose connection pool
    await engine.dispose()


app = FastAPI(
    title="Vitara API",
    description="Backend for Vitara — personalised supplement recommendation MVP",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}
