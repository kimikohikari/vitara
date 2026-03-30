from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.db.database import get_db
from app.models.quiz import QuizSession, Lead, AnalyticsEvent, EventType
from app.schemas.quiz import (
    SessionStartResponse,
    SubmitAnswersRequest,
    SubmitAnswersResponse,
    LeadCaptureRequest,
    LeadCaptureResponse,
    TrackEventRequest,
    TrackEventResponse,
    FunnelStats,
    SessionDetail,
)
from app.services.recommendation import get_recommendations, build_summary

router = APIRouter()


# ── 1. Start a quiz session ──────────────────────────────────────────────────

@router.post(
    "/session/start",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new quiz session",
    description="Call this when the user clicks 'Start assessment'. Returns a session_id to carry through the quiz.",
)
async def start_session(db: AsyncSession = Depends(get_db)):
    session = QuizSession()
    db.add(session)
    await db.flush()  # get the id before commit

    # Record funnel event
    db.add(AnalyticsEvent(
        session_id=session.id,
        event_type=EventType.quiz_started,
    ))

    return SessionStartResponse(session_id=session.id)


# ── 2. Submit answers → get recommendations ──────────────────────────────────

@router.post(
    "/session/submit",
    response_model=SubmitAnswersResponse,
    summary="Submit quiz answers and receive supplement recommendations",
)
async def submit_answers(
    body: SubmitAnswersRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, body.session_id)

    recs = get_recommendations(body.answers)
    rec_keys = [r.key for r in recs]
    summary = build_summary(body.answers)

    session.answers = body.answers.model_dump()
    session.recommendations = rec_keys

    db.add(AnalyticsEvent(
        session_id=session.id,
        event_type=EventType.results_shown,
        payload={"recommendations": rec_keys},
    ))

    return SubmitAnswersResponse(
        session_id=session.id,
        recommendations=recs,
        summary=summary,
    )


# ── 3. Capture lead email ────────────────────────────────────────────────────

@router.post(
    "/lead/capture",
    response_model=LeadCaptureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save email lead",
    description="Called when user submits email on results screen. Idempotent — same session can't create two leads.",
)
async def capture_lead(
    body: LeadCaptureRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await _get_session_or_404(db, body.session_id)

    # Idempotency: one lead per session
    existing = await db.scalar(
        select(Lead).where(Lead.session_id == session.id)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A lead has already been captured for this session.",
        )

    # Also check if same email exists for dedup reporting (not an error)
    lead = Lead(session_id=session.id, email=body.email.lower())
    db.add(lead)
    await db.flush()

    db.add(AnalyticsEvent(
        session_id=session.id,
        event_type=EventType.email_captured,
        payload={"email_domain": body.email.split("@")[1]},  # store domain only for privacy
    ))

    return LeadCaptureResponse(lead_id=lead.id)


# ── 4. Track events (buy click, etc.) ────────────────────────────────────────

@router.post(
    "/analytics/event",
    response_model=TrackEventResponse,
    summary="Track a funnel event",
    description="Track buy_clicked or any custom event. Does not fail loudly — analytics are best-effort.",
)
async def track_event(
    body: TrackEventRequest,
    db: AsyncSession = Depends(get_db),
):
    # Don't 404 on missing session for analytics — be lenient
    session = await db.scalar(
        select(QuizSession).where(QuizSession.id == body.session_id)
    )
    if not session:
        return TrackEventResponse(recorded=False)

    db.add(AnalyticsEvent(
        session_id=body.session_id,
        event_type=body.event_type,
        payload=body.payload,
    ))
    return TrackEventResponse(recorded=True)


# ── 5. Funnel stats (admin) ───────────────────────────────────────────────────

@router.get(
    "/admin/stats",
    response_model=FunnelStats,
    summary="Funnel conversion stats",
    description="Returns aggregate counts and conversion rates for the funnel. Protect with auth in production.",
)
async def funnel_stats(db: AsyncSession = Depends(get_db)):
    def _count(event: EventType):
        return select(func.count()).select_from(AnalyticsEvent).where(
            AnalyticsEvent.event_type == event
        )

    started       = await db.scalar(_count(EventType.quiz_started))      or 0
    results_shown = await db.scalar(_count(EventType.results_shown))     or 0
    email_cap     = await db.scalar(_count(EventType.email_captured))    or 0
    buy_click     = await db.scalar(_count(EventType.buy_clicked))       or 0

    def _rate(num, denom):
        return round(num / denom * 100, 1) if denom else None

    return FunnelStats(
        quiz_started=started,
        results_shown=results_shown,
        email_captured=email_cap,
        buy_clicked=buy_click,
        conversion_to_results=_rate(results_shown, started),
        conversion_to_lead=_rate(email_cap, started),
        conversion_to_buy=_rate(buy_click, started),
    )


# ── 6. Session detail (admin / debug) ────────────────────────────────────────

@router.get(
    "/admin/session/{session_id}",
    response_model=SessionDetail,
    summary="Get full session details",
)
async def session_detail(session_id: UUID, db: AsyncSession = Depends(get_db)):
    session = await _get_session_or_404(db, session_id)
    lead = await db.scalar(select(Lead).where(Lead.session_id == session_id))
    return SessionDetail(
        session_id=session.id,
        answers=session.answers,
        recommendations=session.recommendations,
        email=lead.email if lead else None,
        created_at=session.created_at,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_session_or_404(db: AsyncSession, session_id: UUID) -> QuizSession:
    session = await db.scalar(
        select(QuizSession).where(QuizSession.id == session_id)
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found.",
        )
    return session
