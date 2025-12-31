from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.enums import UserRole
from ..database import get_db
from ..dependencies import ensure_athlete_access, require_role
from ..models.plan import TrainingPlan, TrainingSessionPlanned
from ..models.session import TrainingSessionDone
from ..models.user import CoachAthlete, User
from ..schemas.dashboard import (
    AthleteDetailMetrics,
    AthleteMetrics,
    AthleteAlert,
    AthleteRecentSession,
    CoachAthleteHighlight,
    CoachOverview,
    CoachAlert,
    CoachTrendPoint,
    AlertDispatchResult,
)
from ..services.notifications import send_athlete_alerts_email, send_coach_alerts_email

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


@router.get("/coach/alerts", response_model=list[CoachAlert])
def coach_alerts(
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> list[CoachAlert]:
    return _build_coach_alerts(db, current_user.id)


@router.post("/coach/alerts/send", response_model=AlertDispatchResult)
def trigger_coach_alert_notifications(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> AlertDispatchResult:
    alerts = _build_coach_alerts(db, current_user.id)
    if not alerts:
        return AlertDispatchResult(queued_alerts=0, detail="No alerts to send.")
    background_tasks.add_task(send_coach_alerts_email, current_user, alerts)
    return AlertDispatchResult(
        queued_alerts=len(alerts),
        detail="Alert emails queued for delivery.",
    )


@router.get("/coach/athlete/{athlete_id}", response_model=AthleteDetailMetrics)
def coach_athlete_detail(
    athlete_id: int,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> AthleteDetailMetrics:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    athlete = db.get(User, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found.")
    today = date.today()
    week_start = today - timedelta(days=6)
    planned_week = (
        db.query(func.count(TrainingSessionPlanned.id))
        .join(TrainingPlan, TrainingPlan.id == TrainingSessionPlanned.plan_id)
        .filter(
            TrainingPlan.athlete_id == athlete_id,
            TrainingSessionPlanned.date >= week_start,
            TrainingSessionPlanned.date <= today,
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
            TrainingSessionDone.athlete_id == athlete_id,
            TrainingSessionDone.date >= week_start,
            TrainingSessionDone.date <= today,
        )
        .one()
    )
    completed_week = completed_row[0] or 0
    total_distance = float(completed_row[1] or 0)
    compliance = (
        round(completed_week / planned_week, 2) if planned_week > 0 else None
    )
    upcoming_sessions = (
        db.query(func.count(TrainingSessionPlanned.id))
        .join(TrainingPlan, TrainingPlan.id == TrainingSessionPlanned.plan_id)
        .filter(
            TrainingPlan.athlete_id == athlete_id,
            TrainingSessionPlanned.date >= today,
            TrainingSessionPlanned.date <= today + timedelta(days=7),
        )
        .scalar()
        or 0
    )
    weekly_trend = _build_weekly_trend(db, [athlete_id])
    streak = _calculate_completion_streak(db, athlete_id)
    recent_sessions = (
        db.query(TrainingSessionDone)
        .filter(TrainingSessionDone.athlete_id == athlete_id)
        .order_by(TrainingSessionDone.date.desc())
        .limit(5)
        .all()
    )
    return AthleteDetailMetrics(
        athlete_id=athlete_id,
        athlete_name=athlete.name,
        planned_sessions_week=int(planned_week),
        completed_sessions_week=int(completed_week),
        completed_distance_week=total_distance,
        compliance_rate=compliance,
        current_streak=streak,
        upcoming_sessions=int(upcoming_sessions),
        weekly_trend=weekly_trend,
        pending_sessions_today=_pending_sessions_today(db, athlete_id),
        recent_sessions=[
            AthleteRecentSession(
                id=session.id,
                date=session.date.isoformat(),
                title=session.notes or session.surface,
                actual_distance=session.actual_distance,
                actual_duration=session.actual_duration,
                actual_rpe=session.actual_rpe,
            )
            for session in recent_sessions
        ],
    )


@router.get("/athlete/alerts", response_model=list[AthleteAlert])
def athlete_alerts(
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> list[AthleteAlert]:
    detail = coach_athlete_detail(athlete_id=current_user.id, current_user=current_user, db=db)
    return _build_athlete_alerts_from_detail(detail)


@router.post("/athlete/alerts/send", response_model=AlertDispatchResult)
def trigger_athlete_alert_notifications(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> AlertDispatchResult:
    detail = coach_athlete_detail(athlete_id=current_user.id, current_user=current_user, db=db)
    alerts = _build_athlete_alerts_from_detail(detail)
    if not alerts:
        return AlertDispatchResult(queued_alerts=0, detail="No alerts to send.")
    background_tasks.add_task(send_athlete_alerts_email, current_user, alerts)
    return AlertDispatchResult(
        queued_alerts=len(alerts),
        detail="Alert email queued. Check your inbox shortly.",
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


def _calculate_completion_streak(db: Session, athlete_id: int, days: int = 21) -> int:
    today = date.today()
    start = today - timedelta(days=days)
    completed_dates = {
        row[0]
        for row in (
            db.query(TrainingSessionDone.date)
            .filter(
                TrainingSessionDone.athlete_id == athlete_id,
                TrainingSessionDone.date >= start,
                TrainingSessionDone.date <= today,
            )
            .distinct()
            .all()
        )
    }
    streak = 0
    cursor = today
    while cursor in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _pending_sessions_today(db: Session, athlete_id: int) -> int:
    today = date.today()
    planned = (
        db.query(func.count(TrainingSessionPlanned.id))
        .join(TrainingPlan, TrainingPlan.id == TrainingSessionPlanned.plan_id)
        .filter(
            TrainingPlan.athlete_id == athlete_id,
            TrainingSessionPlanned.date == today,
        )
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(TrainingSessionDone.id))
        .filter(
            TrainingSessionDone.athlete_id == athlete_id,
            TrainingSessionDone.date == today,
        )
        .scalar()
        or 0
    )
    return max(0, int(planned) - int(completed))


def _build_coach_alerts(db: Session, coach_id: int) -> list[CoachAlert]:
    metrics, _ = _build_coach_metrics(db, coach_id)
    alerts: list[CoachAlert] = []
    for metric in metrics:
        if metric.pending_sessions_today > 0:
            alerts.append(
                CoachAlert(
                    athlete_id=metric.athlete_id,
                    athlete_name=metric.athlete_name,
                    message=f"{metric.pending_sessions_today} sesión(es) pendientes hoy.",
                    severity="info",
                )
            )
        if metric.compliance_rate is not None and metric.compliance_rate < 0.6:
            alerts.append(
                CoachAlert(
                    athlete_id=metric.athlete_id,
                    athlete_name=metric.athlete_name,
                    message="Cumplimiento semanal por debajo del 60%.",
                    severity="warning",
                )
            )
    return alerts


def _build_athlete_alerts_from_detail(detail: AthleteDetailMetrics) -> list[AthleteAlert]:
    alerts: list[AthleteAlert] = []
    if detail.pending_sessions_today > 0:
        alerts.append(
            AthleteAlert(
                message=f"Tienes {detail.pending_sessions_today} sesión(es) pendientes hoy.",
                severity="warning",
            )
        )
    if detail.current_streak == 0:
        alerts.append(
            AthleteAlert(
                message="Tu racha está en 0 días. Registra una sesión para reiniciarla.",
                severity="info",
            )
        )
    if detail.upcoming_sessions == 0:
        alerts.append(
            AthleteAlert(
                message="No hay sesiones planificadas para la próxima semana. Contacta a tu coach.",
                severity="info",
            )
        )
    return alerts
