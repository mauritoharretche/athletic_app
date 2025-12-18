from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.enums import UserRole
from ..database import get_db
from ..dependencies import ensure_athlete_access, get_current_user, require_role
from ..models.plan import TrainingSessionPlanned
from ..models.session import TrainingSessionDone
from ..models.user import User
from ..schemas.session import (
    TrainingSessionDoneCreate,
    TrainingSessionDoneRead,
    TrainingSessionDoneUpdate,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/done", response_model=TrainingSessionDoneRead, status_code=status.HTTP_201_CREATED)
def log_completed_session(
    payload: TrainingSessionDoneCreate,
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> TrainingSessionDone:
    if payload.planned_session_id:
        planned = db.get(TrainingSessionPlanned, payload.planned_session_id)
        if not planned:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planned session not found.")
        if planned.plan.athlete_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session.")
        existing_for_planned = (
            db.query(TrainingSessionDone)
            .filter(
                TrainingSessionDone.athlete_id == current_user.id,
                TrainingSessionDone.planned_session_id == payload.planned_session_id,
            )
            .first()
        )
        if existing_for_planned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already logged this planned session.",
            )
    else:
        _assert_no_manual_duplicate(db, current_user.id, payload.date)
    done = TrainingSessionDone(
        athlete_id=current_user.id,
        planned_session_id=payload.planned_session_id,
        date=payload.date,
        actual_distance=payload.actual_distance,
        actual_duration=payload.actual_duration,
        actual_rpe=payload.actual_rpe,
        surface=payload.surface,
        shoes=payload.shoes,
        notes=payload.notes,
    )
    db.add(done)
    db.commit()
    db.refresh(done)
    return done


@router.get("/done/me", response_model=list[TrainingSessionDoneRead])
def list_my_sessions(
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    planned_session_id: int | None = Query(default=None),
) -> list[TrainingSessionDone]:
    return _query_sessions(
        db,
        athlete_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        planned_session_id=planned_session_id,
    )


@router.get("/done/athlete/{athlete_id}", response_model=list[TrainingSessionDoneRead])
def list_athlete_sessions(
    athlete_id: int,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    planned_session_id: int | None = Query(default=None),
) -> list[TrainingSessionDone]:
    ensure_athlete_access(athlete_id, current_user=current_user, db=db)
    return _query_sessions(
        db,
        athlete_id=athlete_id,
        start_date=start_date,
        end_date=end_date,
        planned_session_id=planned_session_id,
    )


@router.get("/done/{session_id}", response_model=TrainingSessionDoneRead)
def get_completed_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingSessionDone:
    return _get_session_for_edit(session_id, current_user, db)


@router.put("/done/{session_id}", response_model=TrainingSessionDoneRead)
def update_session(
    session_id: int,
    payload: TrainingSessionDoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingSessionDone:
    session = _get_session_for_edit(session_id, current_user, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return session

    new_planned_id = updates.get("planned_session_id", session.planned_session_id)
    new_date = updates.get("date", session.date)

    if new_planned_id:
        planned = db.get(TrainingSessionPlanned, new_planned_id)
        if not planned:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planned session not found.")
        if planned.plan.athlete_id != session.athlete_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session.")
        _assert_no_duplicate_planned(db, session.athlete_id, new_planned_id, exclude_session_id=session.id)
    else:
        _assert_no_manual_duplicate(
            db,
            session.athlete_id,
            new_date,
            exclude_session_id=session.id,
        )

    for field, value in updates.items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/done/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    session = _get_session_for_edit(session_id, current_user, db)
    db.delete(session)
    db.commit()


def _get_session_for_edit(session_id: int, current_user: User, db: Session) -> TrainingSessionDone:
    session = db.get(TrainingSessionDone, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if current_user.role == UserRole.ATHLETE:
        if session.athlete_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session.")
    else:
        ensure_athlete_access(session.athlete_id, current_user=current_user, db=db)
    return session


def _query_sessions(
    db: Session,
    athlete_id: int,
    start_date: date | None,
    end_date: date | None,
    planned_session_id: int | None = None,
) -> list[TrainingSessionDone]:
    query = db.query(TrainingSessionDone).filter(TrainingSessionDone.athlete_id == athlete_id)
    if start_date:
        query = query.filter(TrainingSessionDone.date >= start_date)
    if end_date:
        query = query.filter(TrainingSessionDone.date <= end_date)
    if planned_session_id:
        query = query.filter(TrainingSessionDone.planned_session_id == planned_session_id)
    return query.order_by(TrainingSessionDone.date.desc()).all()


def _assert_no_manual_duplicate(
    db: Session,
    athlete_id: int,
    session_date: date,
    exclude_session_id: int | None = None,
) -> None:
    query = (
        db.query(TrainingSessionDone)
        .filter(
            TrainingSessionDone.athlete_id == athlete_id,
            TrainingSessionDone.date == session_date,
            TrainingSessionDone.planned_session_id.is_(None),
        )
    )
    if exclude_session_id:
        query = query.filter(TrainingSessionDone.id != exclude_session_id)
    duplicate = query.first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A session for this date already exists.",
        )


def _assert_no_duplicate_planned(
    db: Session,
    athlete_id: int,
    planned_session_id: int,
    exclude_session_id: int | None = None,
) -> None:
    query = (
        db.query(TrainingSessionDone)
        .filter(
            TrainingSessionDone.athlete_id == athlete_id,
            TrainingSessionDone.planned_session_id == planned_session_id,
        )
    )
    if exclude_session_id:
        query = query.filter(TrainingSessionDone.id != exclude_session_id)
    duplicate = query.first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already logged this planned session.",
        )
