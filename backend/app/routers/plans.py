from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.enums import UserRole
from ..database import get_db
from ..dependencies import ensure_athlete_access, get_current_user, require_role
from ..models.plan import TrainingPlan, TrainingSessionPlanned
from ..models.user import CoachAthlete, User
from datetime import timedelta

from ..schemas.plan import (
    TrainingPlanCreate,
    TrainingPlanRead,
    TrainingPlanDuplicateRequest,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=TrainingPlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: TrainingPlanCreate,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> TrainingPlan:
    plan = TrainingPlan(
        athlete_id=payload.athlete_id,
        name=payload.name,
        goal_type=payload.goal_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
    )
    for session in payload.sessions:
        plan.sessions.append(
            TrainingSessionPlanned(
                date=session.date,
                type=session.type,
                title=session.title,
                description=session.description,
                planned_distance=session.planned_distance,
                planned_duration=session.planned_duration,
                planned_rpe=session.planned_rpe,
                notes_for_athlete=session.notes_for_athlete,
            )
        )
    db.add(plan)
    link = (
        db.query(CoachAthlete)
        .filter(
            CoachAthlete.coach_id == current_user.id,
            CoachAthlete.athlete_id == payload.athlete_id,
        )
        .first()
    )
    if not link:
        db.add(CoachAthlete(coach_id=current_user.id, athlete_id=payload.athlete_id))
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=TrainingPlanRead)
def read_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingPlan:
    plan = db.get(TrainingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    ensure_athlete_access(plan.athlete_id, current_user=current_user, db=db)
    return plan


@router.get("/athlete/{athlete_id}", response_model=list[TrainingPlanRead])
def list_athlete_plans(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TrainingPlan]:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    return (
        db.query(TrainingPlan)
        .filter(TrainingPlan.athlete_id == athlete_id)
        .order_by(TrainingPlan.start_date.desc())
        .all()
    )


@router.post("/{plan_id}/duplicate", response_model=TrainingPlanRead, status_code=status.HTTP_201_CREATED)
def duplicate_plan(
    plan_id: int,
    payload: TrainingPlanDuplicateRequest,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> TrainingPlan:
    plan = db.get(TrainingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    ensure_athlete_access(plan.athlete_id, current_user=current_user, db=db)
    target_athlete_id = payload.target_athlete_id or plan.athlete_id
    ensure_athlete_access(target_athlete_id, current_user=current_user, db=db)

    shift_days = (payload.start_date - plan.start_date).days
    end_date = payload.end_date or (plan.end_date + timedelta(days=shift_days))

    new_plan = TrainingPlan(
        athlete_id=target_athlete_id,
        name=payload.name or f"{plan.name} Copy",
        goal_type=payload.goal_type if payload.goal_type is not None else plan.goal_type,
        start_date=payload.start_date,
        end_date=end_date,
        notes=payload.notes if payload.notes is not None else plan.notes,
    )
    for session in plan.sessions:
        new_plan.sessions.append(
            TrainingSessionPlanned(
                date=session.date + timedelta(days=shift_days),
                type=session.type,
                title=session.title,
                description=session.description,
                planned_distance=session.planned_distance,
                planned_duration=session.planned_duration,
                planned_rpe=session.planned_rpe,
                notes_for_athlete=session.notes_for_athlete,
            )
        )

    db.add(new_plan)
    link = (
        db.query(CoachAthlete)
        .filter(
            CoachAthlete.coach_id == current_user.id,
            CoachAthlete.athlete_id == target_athlete_id,
        )
        .first()
    )
    if not link:
        db.add(CoachAthlete(coach_id=current_user.id, athlete_id=target_athlete_id))
    db.commit()
    db.refresh(new_plan)
    return new_plan
