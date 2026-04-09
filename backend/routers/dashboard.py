from datetime import datetime, timedelta, date as date_type
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter()


def _to_date(val) -> date_type:
    if isinstance(val, str):
        return date_type.fromisoformat(val)
    return val


def _compute_streak(db: Session, user_id: int, plan_id: int) -> int:
    rows = (
        db.query(func.date(models.Answer.answered_at))
        .join(models.Session)
        .filter(
            models.Session.user_id == user_id,
            models.Session.plan_id == plan_id,
        )
        .distinct()
        .order_by(func.date(models.Answer.answered_at).desc())
        .all()
    )
    if not rows:
        return 0
    today = datetime.utcnow().date()
    dates = [_to_date(r[0]) for r in rows]
    if dates[0] < today - timedelta(days=1):
        return 0
    streak = 0
    expected = dates[0]
    for d in dates:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak


@router.get("/overview")
def overview(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = current_user.id
    now = datetime.utcnow()

    progress_records = (
        db.query(models.QuestionProgress)
        .join(models.Question).join(models.Theme)
        .filter(
            models.Theme.user_id == user_id,
            models.Theme.plan_id == plan_id,
            models.QuestionProgress.user_id == user_id,
        )
        .all()
    )

    by_status = {"new": 0, "learning": 0, "acquired": 0}
    due_count = 0
    for p in progress_records:
        by_status[p.status] = by_status.get(p.status, 0) + 1
        if p.next_review_at and p.next_review_at <= now:
            due_count += 1

    total_answers = (
        db.query(func.count(models.Answer.id))
        .join(models.Session)
        .filter(models.Session.user_id == user_id, models.Session.plan_id == plan_id)
        .scalar() or 0
    )
    sessions_count = (
        db.query(func.count(models.Session.id))
        .filter(models.Session.user_id == user_id, models.Session.plan_id == plan_id)
        .scalar() or 0
    )

    return {
        "total_questions": sum(by_status.values()),
        "by_status": by_status,
        "due_today": due_count,
        "total_answers": total_answers,
        "sessions_count": sessions_count,
        "streak_days": _compute_streak(db, user_id, plan_id),
    }


@router.get("/themes")
def themes_progress(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = current_user.id
    now = datetime.utcnow()

    themes = (
        db.query(models.Theme)
        .filter(models.Theme.user_id == user_id, models.Theme.plan_id == plan_id)
        .order_by(models.Theme.name)
        .all()
    )

    result = []
    for theme in themes:
        question_ids = [q.id for q in theme.questions]
        counts = {"new": 0, "learning": 0, "acquired": 0}
        due = 0
        if question_ids:
            for p in db.query(models.QuestionProgress).filter(
                models.QuestionProgress.question_id.in_(question_ids),
                models.QuestionProgress.user_id == user_id,
            ).all():
                counts[p.status] = counts.get(p.status, 0) + 1
                if p.next_review_at and p.next_review_at <= now:
                    due += 1
        result.append({
            "id": theme.id, "name": theme.name, "total": len(question_ids),
            **counts, "due": due,
        })
    return result


@router.get("/heatmap")
def heatmap(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    today = datetime.utcnow().date()
    since = datetime.utcnow() - timedelta(days=90)

    rows = (
        db.query(func.date(models.Answer.answered_at), func.count(models.Answer.id))
        .join(models.Session)
        .filter(
            models.Session.user_id == current_user.id,
            models.Session.plan_id == plan_id,
            models.Answer.answered_at >= since,
        )
        .group_by(func.date(models.Answer.answered_at))
        .all()
    )

    counts = {str(_to_date(r[0])): r[1] for r in rows}
    days = [
        {"date": str(today - timedelta(days=i)), "count": counts.get(str(today - timedelta(days=i)), 0)}
        for i in range(90, -1, -1)
    ]
    return {"days": days}


@router.get("/recent-sessions")
def recent_sessions(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    sessions = (
        db.query(models.Session)
        .filter(models.Session.user_id == current_user.id, models.Session.plan_id == plan_id)
        .order_by(models.Session.started_at.desc())
        .limit(10)
        .all()
    )
    result = []
    for s in sessions:
        answer_count = (
            db.query(func.count(models.Answer.id))
            .filter(models.Answer.session_id == s.id).scalar() or 0
        )
        avg_grade = (
            db.query(func.avg(models.Answer.sm2_grade))
            .filter(models.Answer.session_id == s.id, models.Answer.sm2_grade.isnot(None))
            .scalar()
        )
        result.append({
            "id": s.id, "type": s.type,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "answer_count": answer_count,
            "avg_grade": round(avg_grade, 1) if avg_grade is not None else None,
        })
    return result
