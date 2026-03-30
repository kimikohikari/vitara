from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.quiz import EventType


# ── Quiz answers ────────────────────────────────────────────────────────────

VALID_ENERGY  = {"great", "slump", "low", "crashes"}
VALID_SLEEP   = {"good", "fall", "wake", "early"}
VALID_STRESS  = {"low", "moderate", "high", "extreme"}
VALID_FOCUS   = {"great", "fog", "poor", "caffeine"}
VALID_DIET    = {"great", "ok", "poor", "vegan"}
VALID_ACTIVITY= {"high", "moderate", "low", "none"}


class QuizAnswers(BaseModel):
    energy:   str = Field(..., description="Energy level answer key")
    sleep:    str = Field(..., description="Sleep quality answer key")
    stress:   str = Field(..., description="Stress level answer key")
    focus:    str = Field(..., description="Focus/clarity answer key")
    diet:     str = Field(..., description="Diet quality answer key")
    activity: str = Field(..., description="Activity level answer key")

    @field_validator("energy")
    @classmethod
    def validate_energy(cls, v):
        if v not in VALID_ENERGY:
            raise ValueError(f"energy must be one of {VALID_ENERGY}")
        return v

    @field_validator("sleep")
    @classmethod
    def validate_sleep(cls, v):
        if v not in VALID_SLEEP:
            raise ValueError(f"sleep must be one of {VALID_SLEEP}")
        return v

    @field_validator("stress")
    @classmethod
    def validate_stress(cls, v):
        if v not in VALID_STRESS:
            raise ValueError(f"stress must be one of {VALID_STRESS}")
        return v

    @field_validator("focus")
    @classmethod
    def validate_focus(cls, v):
        if v not in VALID_FOCUS:
            raise ValueError(f"focus must be one of {VALID_FOCUS}")
        return v

    @field_validator("diet")
    @classmethod
    def validate_diet(cls, v):
        if v not in VALID_DIET:
            raise ValueError(f"diet must be one of {VALID_DIET}")
        return v

    @field_validator("activity")
    @classmethod
    def validate_activity(cls, v):
        if v not in VALID_ACTIVITY:
            raise ValueError(f"activity must be one of {VALID_ACTIVITY}")
        return v


# ── Session ──────────────────────────────────────────────────────────────────

class SessionStartResponse(BaseModel):
    session_id: UUID
    message: str = "Quiz session created"


class SubmitAnswersRequest(BaseModel):
    session_id: UUID
    answers: QuizAnswers


class SupplementInfo(BaseModel):
    key: str
    name: str
    latin: str
    emoji: str
    reason: str
    price: str


class SubmitAnswersResponse(BaseModel):
    session_id: UUID
    recommendations: List[SupplementInfo]
    summary: str


# ── Lead capture ─────────────────────────────────────────────────────────────

class LeadCaptureRequest(BaseModel):
    session_id: UUID
    email: EmailStr


class LeadCaptureResponse(BaseModel):
    message: str = "Lead captured successfully"
    lead_id: UUID


# ── Analytics ────────────────────────────────────────────────────────────────

class TrackEventRequest(BaseModel):
    session_id: UUID
    event_type: EventType
    payload: Optional[dict] = None


class TrackEventResponse(BaseModel):
    recorded: bool = True


# ── Admin / stats ─────────────────────────────────────────────────────────────

class FunnelStats(BaseModel):
    quiz_started: int
    results_shown: int
    email_captured: int
    buy_clicked: int
    conversion_to_results: Optional[float]   # results / started
    conversion_to_lead: Optional[float]       # email / started
    conversion_to_buy: Optional[float]        # buy / started


class SessionDetail(BaseModel):
    session_id: UUID
    answers: Optional[dict]
    recommendations: Optional[List[str]]
    email: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
