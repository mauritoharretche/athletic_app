from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.enums import UserRole
from ..database import get_db
from ..dependencies import require_role
from ..models.plan import TrainingPlan, TrainingSessionPlanned
from ..models.session import TrainingSessionDone
from ..models.user import CoachAthlete, User
from ..schemas.dashboard import AthleteMetrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/coach/me", response_model=list[AthleteMetrics])
def coach_dashboard(
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> list[AthleteMetrics]:
    today = date.today()
    week_start = today - timedelta(days=6)

    athlete_rows = (
        db.query(CoachAthlete.athlete_id, User.name)
        .join(User, User.id == CoachAthlete.athlete_id)
        .filter(CoachAthlete.coach_id == current_user.id)
        .all()
    )
    if not athlete_rows:
        return []
    athlete_ids = [row.athlete_id for row in athlete_rows]

    planned_by_athlete = {
        athlete_id: count
        for athlete_id, count in (
            db.query(
                TrainingPlan.athlete_id,
                func.count(TrainingSessionPlanned.id),
            )
            .join(TrainingSessionPlanned, TrainingPlan.id == TrainingSessionPlanned.plan_id)
            .filter(
                TrainingPlan.athlete_id.in_(athlete_ids),
                TrainingSessionPlanned.date >= week_start,
                TrainingSessionPlanned.date <= today,
            )
            .group_by(TrainingPlan.athlete_id)
            .all()
        )
    }

    completed_by_athlete = {
        athlete_id: (count, total_distance or 0)
        for athlete_id, count, total_distance in (
            db.query(
                TrainingSessionDone.athlete_id,
                func.count(TrainingSessionDone.id),
                func.coalesce(func.sum(TrainingSessionDone.actual_distance), 0),
            )
            .filter(
                TrainingSessionDone.athlete_id.in_(athlete_ids),
                TrainingSessionDone.date >= week_start,
                TrainingSessionDone.date <= today,
            )
            .group_by(TrainingSessionDone.athlete_id)
            .all()
        )
    }

    planned_today = {
        athlete_id: count
        for athlete_id, count in (
            db.query(
                TrainingPlan.athlete_id,
                func.count(TrainingSessionPlanned.id),
            )
            .join(TrainingSessionPlanned, TrainingPlan.id == TrainingSessionPlanned.plan_id)
            .filter(
                TrainingPlan.athlete_id.in_(athlete_ids),
                TrainingSessionPlanned.date == today,
            )
            .group_by(TrainingPlan.athlete_id)
            .all()
        )
    }

    completed_today = {
        athlete_id: count
        for athlete_id, count in (
            db.query(
                TrainingSessionDone.athlete_id,
                func.count(TrainingSessionDone.id),
            )
            .filter(
                TrainingSessionDone.athlete_id.in_(athlete_ids),
                TrainingSessionDone.date == today,
            )
            .group_by(TrainingSessionDone.athlete_id)
            .all()
        )
    }

    metrics: list[AthleteMetrics] = []
    for athlete_id, athlete_name in athlete_rows:
        planned_count = planned_by_athlete.get(athlete_id, 0)
        completed_count, total_distance = completed_by_athlete.get(athlete_id, (0, 0))
        compliance = (
            round(completed_count / planned_count, 2) if planned_count > 0 else None
        )
        pending_today = max(
            0,
            planned_today.get(athlete_id, 0) - completed_today.get(athlete_id, 0),
        )
        metrics.append(
            AthleteMetrics(
                athlete_id=athlete_id,
                athlete_name=athlete_name,
                planned_sessions_week=planned_count,
                completed_sessions_week=completed_count,
                completed_distance_week=float(total_distance or 0),
                compliance_rate=compliance,
                pending_sessions_today=pending_today,
            )
        )
    return metrics
