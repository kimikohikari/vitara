from sqlalchemy import (
    Column, String, Text, DateTime, Integer,
    ForeignKey, Enum as SAEnum, JSON, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.db.database import Base


class EventType(str, enum.Enum):
    quiz_started = "quiz_started"
    results_shown = "results_shown"
    buy_clicked = "buy_clicked"
    email_captured = "email_captured"


class QuizSession(Base):
    """
    One row per visitor who started the quiz.
    Identified by a client-generated session_id (UUID) so we can
    correlate events across the funnel without requiring a login.
    """
    __tablename__ = "quiz_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # answers stored as {question_id: selected_value}
    answers = Column(JSON, nullable=True)
    # recommendations as list of supplement keys e.g. ["magnesium","vitaminB"]
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    lead = relationship("Lead", back_populates="session", uselist=False)
    events = relationship("AnalyticsEvent", back_populates="session")


class Lead(Base):
    """
    Email captured at the end of the results screen.
    One-to-one with QuizSession (a session can have at most one lead).
    """
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quiz_sessions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    email = Column(String(320), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("QuizSession", back_populates="lead")


class AnalyticsEvent(Base):
    """
    Funnel events: started → results_shown → buy_clicked / email_captured.
    Thin append-only log — no updates, ever.
    """
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(SAEnum(EventType), nullable=False, index=True)
    # any extra payload (e.g. which supplement was clicked)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("QuizSession", back_populates="events")
