from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.plan import TrainingPlan, TrainingSessionPlanned
from app.models.session import TrainingSessionDone
from app.models.user import AthleteProfile, CoachAthlete, User


def ensure_user(
    db: Session,
    *,
    name: str,
    email: str,
    role: UserRole,
    password: str,
) -> User:
    user = db.query(User).filter_by(email=email).first()
    if user:
        return user
    user = User(
        name=name,
        email=email,
        role=role,
        password_hash=get_password_hash(password),
    )
    db.add(user)
    db.flush()
    if role == UserRole.ATHLETE and not db.get(AthleteProfile, user.id):
        db.add(AthleteProfile(user_id=user.id))
    return user


def ensure_plan_with_sessions(
    db: Session,
    *,
    athlete: User,
    coach: User,
) -> TrainingPlan:
    plan = (
        db.query(TrainingPlan)
        .filter(
            TrainingPlan.athlete_id == athlete.id,
            TrainingPlan.name == "Base 10K",
        )
        .first()
    )
    if plan:
        return plan

    today = date.today()
    start = today - timedelta(days=3)
    plan = TrainingPlan(
        athlete_id=athlete.id,
        name="Base 10K",
        goal_type="10K",
        start_date=start,
        end_date=start + timedelta(days=42),
        notes="Plan de muestra generado por seed.",
    )
    plan.sessions = [
        TrainingSessionPlanned(
            date=start,
            type="RODAJE",
            title="Easy 30",
            description="30 minutos Z2",
            planned_distance=6,
            planned_duration=30,
            planned_rpe=4,
        ),
        TrainingSessionPlanned(
            date=start + timedelta(days=2),
            type="PASADAS",
            title="8x400",
            description="8 repeticiones a ritmo controlado",
            planned_distance=10,
            planned_duration=55,
            planned_rpe=7,
        ),
        TrainingSessionPlanned(
            date=start + timedelta(days=4),
            type="FUERZA",
            title="Circuito fuerza",
            planned_duration=45,
            planned_rpe=6,
        ),
    ]
    db.add(plan)
    db.flush()

    link = (
        db.query(CoachAthlete)
        .filter(
            CoachAthlete.coach_id == coach.id,
            CoachAthlete.athlete_id == athlete.id,
        )
        .first()
    )
    if not link:
        db.add(CoachAthlete(coach_id=coach.id, athlete_id=athlete.id))

    return plan


def seed_completed_session(db: Session, *, athlete: User, planned_session_id: int) -> None:
    existing = (
        db.query(TrainingSessionDone)
        .filter(
            TrainingSessionDone.athlete_id == athlete.id,
            TrainingSessionDone.planned_session_id == planned_session_id,
        )
        .first()
    )
    if existing:
        return

    session = TrainingSessionDone(
        athlete_id=athlete.id,
        planned_session_id=planned_session_id,
        date=date.today() - timedelta(days=1),
        actual_distance=6.2,
        actual_duration=32,
        actual_rpe=5,
        notes="Sesión registrada desde seed.",
    )
    db.add(session)


def main() -> None:
    db = SessionLocal()
    try:
        athlete = ensure_user(
            db,
            name="Athlete Demo",
            email="athlete@example.com",
            role=UserRole.ATHLETE,
            password="secret123",
        )
        coach = ensure_user(
            db,
            name="Coach Demo",
            email="coach@example.com",
            role=UserRole.COACH,
            password="secret123",
        )
        plan = ensure_plan_with_sessions(db, athlete=athlete, coach=coach)
        if plan.sessions:
            seed_completed_session(db, athlete=athlete, planned_session_id=plan.sessions[0].id)
        db.commit()
        print("✅ Seed data ready. Users: athlete@example.com / coach@example.com (pass: secret123)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
