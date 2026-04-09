from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..agents import interview_agent
from ..services.sm2 import update_sm2

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_setting(db: Session, plan_id: int, key: str, default: str) -> str:
    row = (
        db.query(models.Setting)
        .filter(models.Setting.plan_id == plan_id, models.Setting.key == key)
        .first()
    )
    return row.value if row else default


def _question_to_schema(q: models.Question) -> schemas.QuestionForInterview:
    return schemas.QuestionForInterview(
        id=q.id,
        content=q.content,
        difficulty=q.difficulty,
        type=q.type,
        theme_name=q.theme.name,
    )


def _next_question(
    db: Session,
    user_id: int,
    plan_id: int,
    session_id: int,
) -> models.Question | None:
    answered_ids = {
        a.question_id
        for a in db.query(models.Answer.question_id)
        .filter(models.Answer.session_id == session_id)
        .all()
    }

    now = datetime.utcnow()

    base = (
        db.query(models.Question)
        .join(models.Theme)
        .filter(
            models.Theme.user_id == user_id,
            models.Theme.plan_id == plan_id,
        )
    )
    if answered_ids:
        base = base.filter(~models.Question.id.in_(answered_ids))

    overdue = (
        base.join(
            models.QuestionProgress,
            (models.QuestionProgress.question_id == models.Question.id)
            & (models.QuestionProgress.user_id == user_id),
        )
        .filter(models.QuestionProgress.next_review_at <= now)
        .order_by(models.QuestionProgress.next_review_at)
        .first()
    )
    if overdue:
        return overdue

    return (
        base.join(
            models.QuestionProgress,
            (models.QuestionProgress.question_id == models.Question.id)
            & (models.QuestionProgress.user_id == user_id),
        )
        .filter(models.QuestionProgress.status == "new")
        .first()
    )


def _get_or_404_session(db: Session, session_id: int, user_id: int) -> models.Session:
    session = (
        db.query(models.Session)
        .filter(models.Session.id == session_id, models.Session.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=schemas.SessionStart, status_code=201)
def start_session(
    payload: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.type not in ("practice", "mock"):
        raise HTTPException(status_code=422, detail="type must be 'practice' or 'mock'")

    # Verify plan ownership
    plan = db.query(models.Plan).filter(
        models.Plan.id == payload.plan_id,
        models.Plan.user_id == current_user.id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    session = models.Session(
        user_id=current_user.id,
        plan_id=payload.plan_id,
        type=payload.type,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    first = _next_question(db, current_user.id, payload.plan_id, session.id)

    return schemas.SessionStart(
        session_id=session.id,
        type=session.type,
        first_question=_question_to_schema(first) if first else None,
    )


@router.post("/sessions/{session_id}/answer", response_model=schemas.AnswerEvaluation)
def submit_answer(
    session_id: int,
    payload: schemas.AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_or_404_session(db, session_id, current_user.id)
    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    question = (
        db.query(models.Question)
        .join(models.Theme)
        .filter(
            models.Question.id == payload.question_id,
            models.Theme.user_id == current_user.id,
            models.Theme.plan_id == session.plan_id,
        )
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    severity = int(_get_setting(db, session.plan_id, "teacher_severity", "3"))
    try:
        evaluation = interview_agent.evaluate(
            question_content=question.content,
            answer=payload.content,
            teacher_severity=severity,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")

    grade = evaluation["grade"]

    answer = models.Answer(
        session_id=session_id,
        question_id=question.id,
        content=payload.content,
        ai_feedback=evaluation["feedback"],
        sm2_grade=grade,
    )
    db.add(answer)
    db.flush()

    progress = (
        db.query(models.QuestionProgress)
        .filter(
            models.QuestionProgress.question_id == question.id,
            models.QuestionProgress.user_id == current_user.id,
        )
        .first()
    )
    if not progress:
        progress = models.QuestionProgress(
            question_id=question.id, user_id=current_user.id
        )
        db.add(progress)
        db.flush()

    update_sm2(progress, grade)
    db.commit()

    next_q = _next_question(db, current_user.id, session.plan_id, session_id)
    if next_q is None:
        session.ended_at = datetime.utcnow()
        db.commit()

    return schemas.AnswerEvaluation(
        answer_id=answer.id,
        feedback=evaluation["feedback"],
        grade=grade,
        correct_answer_hint=evaluation.get("correct_answer_hint"),
        sm2=schemas.SM2Result(
            status=progress.status,
            interval_days=progress.interval_days,
            next_review_in_days=progress.interval_days,
        ),
        next_question=_question_to_schema(next_q) if next_q else None,
    )


@router.post("/sessions/{session_id}/end", response_model=schemas.SessionOut)
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_or_404_session(db, session_id, current_user.id)
    if not session.ended_at:
        session.ended_at = datetime.utcnow()
        db.commit()
    return session


@router.get("/sessions/{session_id}", response_model=schemas.SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_or_404_session(db, session_id, current_user.id)


@router.get("/sessions/{session_id}/review")
def session_review(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_or_404_session(db, session_id, current_user.id)
    answers = (
        db.query(models.Answer)
        .filter(models.Answer.session_id == session_id)
        .order_by(models.Answer.answered_at)
        .all()
    )
    result = []
    for ans in answers:
        q = db.query(models.Question).filter(models.Question.id == ans.question_id).first()
        result.append({
            "question": {
                "id": q.id, "content": q.content,
                "difficulty": q.difficulty, "type": q.type, "theme_name": q.theme.name,
            },
            "answer": {
                "id": ans.id, "content": ans.content,
                "ai_feedback": ans.ai_feedback, "sm2_grade": ans.sm2_grade,
                "answered_at": ans.answered_at.isoformat(),
            },
        })
    return result


@router.get("/due-count")
def due_count(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    now = datetime.utcnow()
    due = (
        db.query(models.QuestionProgress)
        .join(models.Question).join(models.Theme)
        .filter(
            models.Theme.user_id == current_user.id,
            models.Theme.plan_id == plan_id,
            models.QuestionProgress.user_id == current_user.id,
            models.QuestionProgress.next_review_at <= now,
        )
        .count()
    )
    new_count = (
        db.query(models.QuestionProgress)
        .join(models.Question).join(models.Theme)
        .filter(
            models.Theme.user_id == current_user.id,
            models.Theme.plan_id == plan_id,
            models.QuestionProgress.user_id == current_user.id,
            models.QuestionProgress.status == "new",
        )
        .count()
    )
    return {"due": due, "new": new_count, "total_available": due + new_count}
