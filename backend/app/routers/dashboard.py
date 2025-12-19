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
from ..schemas.dashboard import (
    AthleteMetrics,
    CoachAthleteHighlight,
    CoachOverview,
    CoachTrendPoint,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/coach/me", response_model=list[AthleteMetrics])
def coach_dashboard(
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> list[AthleteMetrics]:
    metrics, _ = _build_coach_metrics(db, current_user.id)
    return metrics


@router.get("/coach/overview", response_model=CoachOverview)
def coach_overview(
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> CoachOverview:
    metrics, athlete_ids = _build_coach_metrics(db, current_user.id)
    if not metrics:
        return CoachOverview(
            total_athletes=0,
            avg_weekly_distance=0.0,
            avg_compliance_rate=None,
            pending_sessions_today=0,
            low_compliance_athletes=0,
            trend=[],
            top_athletes=[],
        )
    avg_distance = sum(m.completed_distance_week for m in metrics) / len(metrics)
    compliance_values = [m.compliance_rate for m in metrics if m.compliance_rate is not None]
    avg_compliance = (
        round(sum(compliance_values) / len(compliance_values), 2) if compliance_values else None
    )
    pending_total = sum(m.pending_sessions_today for m in metrics)
    low_compliance = sum(
        1 for m in metrics if m.compliance_rate is not None and m.compliance_rate < 0.6
    )
    top_athletes = [
        CoachAthleteHighlight(
            athlete_id=m.athlete_id,
            athlete_name=m.athlete_name,
            planned_sessions_week=m.planned_sessions_week,
            completed_sessions_week=m.completed_sessions_week,
            completed_distance_week=m.completed_distance_week,
            compliance_rate=m.compliance_rate,
        )
        for m in sorted(
            metrics,
            key=lambda item: (
                item.compliance_rate if item.compliance_rate is not None else -1,
                item.completed_distance_week,
            ),
            reverse=True,
        )[:3]
    ]
    trend = _build_weekly_trend(db, athlete_ids)
    return CoachOverview(
        total_athletes=len(metrics),
        avg_weekly_distance=round(avg_distance, 2),
        avg_compliance_rate=avg_compliance,
        pending_sessions_today=pending_total,
        low_compliance_athletes=low_compliance,
        trend=trend,
        top_athletes=top_athletes,
    )


def _build_coach_metrics(db: Session, coach_id: int) -> tuple[list[AthleteMetrics], list[int]]:
    today = date.today()
    week_start = today - timedelta(days=6)
    athlete_rows = (
        db.query(CoachAthlete.athlete_id, User.name)
        .join(User, User.id == CoachAthlete.athlete_id)
        .filter(CoachAthlete.coach_id == coach_id)
        .all()
    )
    if not athlete_rows:
        return [], []
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
    return metrics, athlete_ids


def _build_weekly_trend(
    db: Session,
    athlete_ids: list[int],
    weeks: int = 4,
) -> list[CoachTrendPoint]:
    if not athlete_ids:
        return []
    today = date.today()
    points: list[CoachTrendPoint] = []
    for offset in range(weeks - 1, -1, -1):
        period_end = today - timedelta(days=offset * 7)
        period_start = period_end - timedelta(days=6)
        planned_total = (
            db.query(func.count(TrainingSessionPlanned.id))
            .join(TrainingPlan, TrainingPlan.id == TrainingSessionPlanned.plan_id)
            .filter(
                TrainingPlan.athlete_id.in_(athlete_ids),
                TrainingSessionPlanned.date >= period_start,
                TrainingSessionPlanned.date <= period_end,
            )
            .scalar()
            or 0
        )
        completed_row = (
            db.query(
                func.count(TrainingSessionDone.id),
                func.coalesce(func.sum(TrainingSessionDone.actual_distance), 0),
            )
            .filter(
                TrainingSessionDone.athlete_id.in_(athlete_ids),
                TrainingSessionDone.date >= period_start,
                TrainingSessionDone.date <= period_end,
            )
            .one()
        )
        completed_total = completed_row[0] or 0
        total_distance = float(completed_row[1] or 0)
        compliance = (
            round(completed_total / planned_total, 2) if planned_total > 0 else None
        )
        points.append(
            CoachTrendPoint(
                week_start=period_start.isoformat(),
                week_end=period_end.isoformat(),
                planned_sessions=int(planned_total),
                completed_sessions=int(completed_total),
                total_distance=total_distance,
                compliance_rate=compliance,
            )
        )
    return points
