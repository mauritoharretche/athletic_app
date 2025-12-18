from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, cast, literal
from sqlalchemy.types import String
from sqlalchemy.orm import Session

from ..core.enums import UserRole
from ..database import get_db
from ..dependencies import get_current_user, require_role, ensure_athlete_access
from ..models.plan import TrainingPlan, TrainingSessionPlanned
from ..models.session import TrainingSessionDone
from ..models.user import AthleteProfile, CoachAthlete, User
from ..schemas.history import AthleteHistorySummary
from ..schemas.athlete import AthleteTodayOverview, SessionOverview, WeeklyStat
from ..schemas.session import TrainingSessionDoneRead
from ..schemas.user import AthleteProfileRead, AthleteProfileUpdate, AthleteSummary

router = APIRouter(prefix="/athletes", tags=["athletes"])


@router.get("/me", response_model=AthleteProfileRead)
def get_my_profile(
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> AthleteProfile:
    profile = db.get(AthleteProfile, current_user.id)
    if not profile:
        profile = AthleteProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("/me", response_model=AthleteProfileRead)
def update_my_profile(
    payload: AthleteProfileUpdate,
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> AthleteProfile:
    profile = db.get(AthleteProfile, current_user.id)
    if not profile:
        profile = AthleteProfile(user_id=current_user.id)
        db.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{athlete_id}/summary", response_model=AthleteSummary)
def athlete_summary(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AthleteSummary:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    total_plans = db.query(TrainingPlan).filter(TrainingPlan.athlete_id == athlete_id).count()
    planned_sessions = (
        db.query(TrainingSessionPlanned)
        .join(TrainingPlan)
        .filter(TrainingPlan.athlete_id == athlete_id)
        .count()
    )
    completed_sessions = (
        db.query(TrainingSessionDone).filter(TrainingSessionDone.athlete_id == athlete_id).count()
    )
    total_distance = (
        db.query(func.coalesce(func.sum(TrainingSessionDone.actual_distance), 0))
        .filter(TrainingSessionDone.athlete_id == athlete_id)
        .scalar()
        or 0
    )
    return AthleteSummary(
        athlete_id=athlete_id,
        total_plans=total_plans,
        planned_sessions=planned_sessions,
        completed_sessions=completed_sessions,
        total_distance_km=float(total_distance),
    )


@router.get("/{athlete_id}/history", response_model=AthleteHistorySummary)
def athlete_history(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AthleteHistorySummary:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    today = date.today()
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)

    week_stats = _aggregate_period(db, athlete_id, week_start, today)
    month_stats = _aggregate_period(db, athlete_id, month_start, today)

    session_type_label = func.coalesce(
        cast(TrainingSessionPlanned.type, String),
        literal("MANUAL"),
    )
    type_counts = (
        db.query(
            session_type_label,
            func.count(TrainingSessionDone.id),
        )
        .outerjoin(
            TrainingSessionPlanned,
            TrainingSessionDone.planned_session_id == TrainingSessionPlanned.id,
        )
        .filter(
            TrainingSessionDone.athlete_id == athlete_id,
            TrainingSessionDone.date >= month_start,
            TrainingSessionDone.date <= today,
        )
        .group_by(session_type_label)
        .all()
    )
    distribution = {str(session_type): count for session_type, count in type_counts}

    summary = AthleteHistorySummary(
        athlete_id=athlete_id,
        week_total_distance=week_stats["total_distance"],
        week_sessions=week_stats["sessions"],
        week_avg_rpe=week_stats["avg_rpe"],
        month_total_distance=month_stats["total_distance"],
        month_sessions=month_stats["sessions"],
        month_avg_rpe=month_stats["avg_rpe"],
        session_type_distribution=distribution,
    )
    return summary


@router.get("/{athlete_id}/today", response_model=AthleteTodayOverview)
def athlete_today_overview(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AthleteTodayOverview:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    today = date.today()

    sessions = (
        db.query(TrainingSessionPlanned)
        .join(TrainingPlan)
        .filter(
            TrainingPlan.athlete_id == athlete_id,
            TrainingSessionPlanned.date >= today,
        )
        .order_by(TrainingSessionPlanned.date.asc())
        .limit(5)
        .all()
    )
    session_ids = [s.id for s in sessions]
    done_map: dict[int, TrainingSessionDone] = {}
    if session_ids:
        completions = (
            db.query(TrainingSessionDone)
            .filter(
                TrainingSessionDone.athlete_id == athlete_id,
                TrainingSessionDone.planned_session_id.in_(session_ids),
            )
            .all()
        )
        done_map = {c.planned_session_id: c for c in completions if c.planned_session_id}

    def to_overview(session: TrainingSessionPlanned) -> SessionOverview:
        completed_session = done_map.get(session.id)
        return SessionOverview(
            plan_id=session.plan_id,
            session_id=session.id,
            date=session.date,
            type=session.type,
            title=session.title,
            planned_distance=float(session.planned_distance) if session.planned_distance is not None else None,
            planned_duration=session.planned_duration,
            planned_rpe=session.planned_rpe,
            completed=completed_session is not None,
            completed_session=TrainingSessionDoneRead.model_validate(completed_session)
            if completed_session
            else None,
        )

    today_session = next((s for s in sessions if s.date == today), None)
    upcoming = []
    if today_session:
        upcoming = [to_overview(s) for s in sessions if s.id != today_session.id][:3]
    else:
        upcoming = [to_overview(s) for s in sessions][:3]

    overview = AthleteTodayOverview(
        athlete_id=athlete_id,
        date=today,
        today=to_overview(today_session) if today_session else None,
        upcoming=upcoming,
    )
    return overview


def _aggregate_period(db: Session, athlete_id: int, start_date: date, end_date: date) -> dict[str, float | int | None]:
    total_distance, sessions, avg_rpe = (
        db.query(
            func.coalesce(func.sum(TrainingSessionDone.actual_distance), 0),
            func.count(TrainingSessionDone.id),
            func.avg(TrainingSessionDone.actual_rpe),
        )
        .filter(
            TrainingSessionDone.athlete_id == athlete_id,
            TrainingSessionDone.date >= start_date,
            TrainingSessionDone.date <= end_date,
        )
        .one()
    )
    return {
        "total_distance": float(total_distance or 0),
        "sessions": sessions,
        "avg_rpe": float(avg_rpe) if avg_rpe is not None else None,
    }


@router.get("/{athlete_id}/weekly-stats", response_model=list[WeeklyStat])
def athlete_weekly_stats(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WeeklyStat]:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    today = date.today()
    stats: list[WeeklyStat] = []
    for offset in range(0, 4):
        end_date = today - timedelta(days=7 * offset)
        start_date = end_date - timedelta(days=6)
        total_distance, sessions, avg_rpe = (
            db.query(
                func.coalesce(func.sum(TrainingSessionDone.actual_distance), 0),
                func.count(TrainingSessionDone.id),
                func.avg(TrainingSessionDone.actual_rpe),
            )
            .filter(
                TrainingSessionDone.athlete_id == athlete_id,
                TrainingSessionDone.date >= start_date,
                TrainingSessionDone.date <= end_date,
            )
            .one()
        )
        stats.append(
            WeeklyStat(
                start_date=start_date,
                end_date=end_date,
                total_distance=float(total_distance or 0),
                sessions=sessions,
                avg_rpe=float(avg_rpe) if avg_rpe is not None else None,
            )
        )
    return list(reversed(stats))
