from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ── Plans ─────────────────────────────────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = None

class PlanOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    theme_count: int = 0
    question_count: int = 0
    model_config = {"from_attributes": True}


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    created_at: datetime
    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str


# ── Themes ────────────────────────────────────────────────────────────────────

class ThemeCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None

class ThemeOut(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Questions ─────────────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    id: int
    theme_id: int
    content: str
    difficulty: int
    type: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Question Progress ─────────────────────────────────────────────────────────

class QuestionProgressOut(BaseModel):
    id: int
    question_id: int
    status: str
    ef: float
    interval_days: int
    repetitions: int
    next_review_at: Optional[datetime]
    last_reviewed_at: Optional[datetime]
    model_config = {"from_attributes": True}


# ── Sessions ──────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    type: str      # 'practice' | 'mock'
    plan_id: int

class SessionOut(BaseModel):
    id: int
    type: str
    started_at: datetime
    ended_at: Optional[datetime]
    notes: Optional[str]
    model_config = {"from_attributes": True}


# ── Answers ───────────────────────────────────────────────────────────────────

class AnswerOut(BaseModel):
    id: int
    session_id: int
    question_id: int
    content: Optional[str]
    ai_feedback: Optional[str]
    sm2_grade: Optional[int]
    answered_at: datetime
    model_config = {"from_attributes": True}


# ── Interview ─────────────────────────────────────────────────────────────────

class QuestionForInterview(BaseModel):
    id: int
    content: str
    difficulty: int
    type: str
    theme_name: str

class SM2Result(BaseModel):
    status: str
    interval_days: int
    next_review_in_days: int

class AnswerSubmit(BaseModel):
    question_id: int
    content: str
    is_retry: bool = False

class AnswerEvaluation(BaseModel):
    answer_id: int
    feedback: str
    grade: int
    explanation: Optional[str]
    awaiting_retry: bool = False
    sm2: SM2Result
    next_question: Optional[QuestionForInterview]

class SessionStart(BaseModel):
    session_id: int
    type: str
    first_question: Optional[QuestionForInterview]


# ── Coach ─────────────────────────────────────────────────────────────────────

class CoachMessageIn(BaseModel):
    content: str

class CoachMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingUpdate(BaseModel):
    key: str
    value: str

class SettingOut(BaseModel):
    key: str
    value: str
    model_config = {"from_attributes": True}
