"""
Integration tests using FastAPI's TestClient with an in-memory SQLite DB
so no real Postgres is needed during CI.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.database import Base, get_db
from app.main import app

# Use SQLite for tests (no Postgres needed in CI)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


GOOD_ANSWERS = {
    "energy": "low",
    "sleep": "wake",
    "stress": "high",
    "focus": "fog",
    "diet": "ok",
    "activity": "moderate",
}


class TestSessionFlow:

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_start_session(self, client):
        r = await client.post("/api/v1/quiz/session/start")
        assert r.status_code == 201
        data = r.json()
        assert "session_id" in data

    @pytest.mark.asyncio
    async def test_submit_answers_returns_recs(self, client):
        session_id = (await client.post("/api/v1/quiz/session/start")).json()["session_id"]
        r = await client.post("/api/v1/quiz/session/submit", json={
            "session_id": session_id,
            "answers": GOOD_ANSWERS,
        })
        assert r.status_code == 200
        data = r.json()
        assert len(data["recommendations"]) == 3
        assert data["summary"]

    @pytest.mark.asyncio
    async def test_capture_lead(self, client):
        session_id = (await client.post("/api/v1/quiz/session/start")).json()["session_id"]
        await client.post("/api/v1/quiz/session/submit", json={
            "session_id": session_id, "answers": GOOD_ANSWERS,
        })
        r = await client.post("/api/v1/quiz/lead/capture", json={
            "session_id": session_id,
            "email": "test@example.com",
        })
        assert r.status_code == 201
        assert "lead_id" in r.json()

    @pytest.mark.asyncio
    async def test_duplicate_lead_returns_409(self, client):
        session_id = (await client.post("/api/v1/quiz/session/start")).json()["session_id"]
        payload = {"session_id": session_id, "email": "test@example.com"}
        await client.post("/api/v1/quiz/lead/capture", json=payload)
        r = await client.post("/api/v1/quiz/lead/capture", json=payload)
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_track_event(self, client):
        session_id = (await client.post("/api/v1/quiz/session/start")).json()["session_id"]
        r = await client.post("/api/v1/quiz/analytics/event", json={
            "session_id": session_id,
            "event_type": "buy_clicked",
            "payload": {"supplement": "magnesium"},
        })
        assert r.status_code == 200
        assert r.json()["recorded"] is True

    @pytest.mark.asyncio
    async def test_funnel_stats(self, client):
        # Create a full funnel
        sid = (await client.post("/api/v1/quiz/session/start")).json()["session_id"]
        await client.post("/api/v1/quiz/session/submit", json={"session_id": sid, "answers": GOOD_ANSWERS})
        await client.post("/api/v1/quiz/lead/capture", json={"session_id": sid, "email": "x@y.com"})

        r = await client.get("/api/v1/quiz/admin/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["quiz_started"] >= 1
        assert data["results_shown"] >= 1
        assert data["email_captured"] >= 1

    @pytest.mark.asyncio
    async def test_invalid_answer_value_rejected(self, client):
        session_id = (await client.post("/api/v1/quiz/session/start")).json()["session_id"]
        bad_answers = {**GOOD_ANSWERS, "energy": "flying_to_mars"}
        r = await client.post("/api/v1/quiz/session/submit", json={
            "session_id": session_id, "answers": bad_answers,
        })
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_session_returns_404(self, client):
        r = await client.post("/api/v1/quiz/session/submit", json={
            "session_id": "00000000-0000-0000-0000-000000000000",
            "answers": GOOD_ANSWERS,
        })
        assert r.status_code == 404
