from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..agents import coach_agent

router = APIRouter()


def _owned_plan(db: Session, plan_id: int, user_id: int) -> models.Plan:
    plan = db.query(models.Plan).filter(
        models.Plan.id == plan_id, models.Plan.user_id == user_id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.get("/history", response_model=list[schemas.CoachMessageOut])
def get_history(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _owned_plan(db, plan_id, current_user.id)
    return (
        db.query(models.CoachMessage)
        .filter(
            models.CoachMessage.user_id == current_user.id,
            models.CoachMessage.plan_id == plan_id,
        )
        .order_by(models.CoachMessage.created_at)
        .all()
    )


@router.post("/chat", response_model=schemas.CoachMessageOut)
def chat(
    plan_id: int,
    payload: schemas.CoachMessageIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _owned_plan(db, plan_id, current_user.id)
    try:
        coach_agent.run(payload.content, db, current_user.id, plan_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    last_msg = (
        db.query(models.CoachMessage)
        .filter(
            models.CoachMessage.user_id == current_user.id,
            models.CoachMessage.plan_id == plan_id,
            models.CoachMessage.role == "assistant",
        )
        .order_by(models.CoachMessage.created_at.desc())
        .first()
    )
    return last_msg


@router.delete("/history", status_code=204)
def clear_history(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _owned_plan(db, plan_id, current_user.id)
    db.query(models.CoachMessage).filter(
        models.CoachMessage.user_id == current_user.id,
        models.CoachMessage.plan_id == plan_id,
    ).delete()
    db.commit()
