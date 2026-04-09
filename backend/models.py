from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.orm import relationship, backref
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    plans = relationship("Plan", back_populates="user")
    themes = relationship("Theme", back_populates="user")
    question_progress = relationship("QuestionProgress", back_populates="user")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="plans")
    themes = relationship("Theme", back_populates="plan", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="plan", cascade="all, delete-orphan")
    settings = relationship("Setting", back_populates="plan", cascade="all, delete-orphan")
    coach_messages = relationship("CoachMessage", back_populates="plan", cascade="all, delete-orphan")


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("themes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="themes")
    plan = relationship("Plan", back_populates="themes")
    questions = relationship("Question", back_populates="theme", cascade="all, delete-orphan")
    children = relationship("Theme", backref=backref("parent", remote_side="Theme.id"))


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_question_difficulty"),
        CheckConstraint("type IN ('concept', 'algo', 'system_design', 'behavioral')", name="ck_question_type"),
    )

    id = Column(Integer, primary_key=True)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    content = Column(Text, nullable=False)
    difficulty = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    theme = relationship("Theme", back_populates="questions")
    progress = relationship("QuestionProgress", back_populates="question", cascade="all, delete-orphan")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class QuestionProgress(Base):
    __tablename__ = "question_progress"
    __table_args__ = (
        UniqueConstraint("question_id", "user_id", name="uq_progress_question_user"),
        CheckConstraint("status IN ('new', 'learning', 'acquired')", name="ck_progress_status"),
    )

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="new", nullable=False)
    ef = Column(Float, default=2.5, nullable=False)
    interval_days = Column(Integer, default=1, nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    next_review_at = Column(DateTime, nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    question = relationship("Question", back_populates="progress")
    user = relationship("User", back_populates="question_progress")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("type IN ('practice', 'mock')", name="ck_session_type"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=True)
    type = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User")
    plan = relationship("Plan", back_populates="sessions")
    answers = relationship("Answer", back_populates="session")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        CheckConstraint("sm2_grade BETWEEN 0 AND 5", name="ck_answer_sm2_grade"),
    )

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    content = Column(Text, nullable=True)
    audio_path = Column(String, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    sm2_grade = Column(Integer, nullable=True)
    answered_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("plan_id", "key", name="uq_setting_plan_key"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)

    user = relationship("User")
    plan = relationship("Plan", back_populates="settings")


class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(6), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")


class CoachMessage(Base):
    __tablename__ = "coach_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_coach_message_role"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    plan = relationship("Plan", back_populates="coach_messages")
