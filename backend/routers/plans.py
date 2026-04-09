from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter()


def _owned_plan(db: Session, plan_id: int, user_id: int) -> models.Plan:
    plan = db.query(models.Plan).filter(
        models.Plan.id == plan_id,
        models.Plan.user_id == user_id,
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def _plan_to_schema(plan: models.Plan) -> schemas.PlanOut:
    question_count = sum(len(t.questions) for t in plan.themes)
    return schemas.PlanOut(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        created_at=plan.created_at,
        theme_count=len(plan.themes),
        question_count=question_count,
    )


@router.get("/", response_model=list[schemas.PlanOut])
def list_plans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plans = (
        db.query(models.Plan)
        .filter(models.Plan.user_id == current_user.id)
        .order_by(models.Plan.created_at)
        .all()
    )
    return [_plan_to_schema(p) for p in plans]


@router.post("/", response_model=schemas.PlanOut, status_code=201)
def create_plan(
    payload: schemas.PlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = models.Plan(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_to_schema(plan)


@router.get("/{plan_id}", response_model=schemas.PlanOut)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _plan_to_schema(_owned_plan(db, plan_id, current_user.id))


@router.patch("/{plan_id}", response_model=schemas.PlanOut)
def update_plan(
    plan_id: int,
    payload: schemas.PlanCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _owned_plan(db, plan_id, current_user.id)
    plan.name = payload.name
    plan.description = payload.description
    db.commit()
    db.refresh(plan)
    return _plan_to_schema(plan)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    plan = _owned_plan(db, plan_id, current_user.id)
    db.delete(plan)
    db.commit()
