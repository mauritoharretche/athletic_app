from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.enums import InviteStatus, UserRole
from ..core.security import create_access_token, get_password_hash, verify_password
from ..database import get_db
from ..dependencies import get_current_user, require_role
from ..models.user import AthleteProfile, CoachAthlete, CoachInvite, User
from ..schemas.user import (
    CoachInviteRequest,
    CoachInviteRead,
    CoachInviteResponse,
    Token,
    UserCreate,
    UserRead,
)
from ..services.notifications import (
    send_invite_accepted,
    send_invite_email,
    send_invite_reminder,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")
    user = User(
        name=user_in.name,
        email=user_in.email,
        role=user_in.role,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(user)
    db.flush()
    if user.role == UserRole.ATHLETE:
        db.add(AthleteProfile(user_id=user.id))
        _attach_pending_invites_to_user(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(email: str, password: str, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)) -> Token:
    access_token = create_access_token({"sub": str(current_user.id), "role": current_user.role.value})
    return Token(access_token=access_token)


@router.post("/invite-athlete", response_model=CoachInviteRead, status_code=status.HTTP_200_OK)
def invite_athlete(
    payload: CoachInviteRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> CoachInvite:
    athlete = db.query(User).filter(User.email == payload.athlete_email).first()
    if athlete and athlete.role != UserRole.ATHLETE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email belongs to a coach.")
    if athlete:
        existing = (
            db.query(CoachAthlete)
            .filter(CoachAthlete.coach_id == current_user.id, CoachAthlete.athlete_id == athlete.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Athlete already linked.")
    invite = (
        db.query(CoachInvite)
        .filter(
            CoachInvite.coach_id == current_user.id,
            CoachInvite.athlete_email == payload.athlete_email,
            CoachInvite.status == InviteStatus.PENDING,
        )
        .first()
    )
    if invite:
        if athlete and invite.athlete_id is None:
            invite.athlete_id = athlete.id
            db.commit()
            db.refresh(invite)
            background_tasks.add_task(send_invite_email, invite)
        return invite
    invite = CoachInvite(
        coach_id=current_user.id,
        athlete_id=athlete.id if athlete else None,
        athlete_email=athlete.email if athlete else payload.athlete_email,
        status=InviteStatus.PENDING,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    background_tasks.add_task(send_invite_email, invite)
    return invite


@router.get("/invitations/coach", response_model=list[CoachInviteRead])
def list_coach_invites(
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> list[CoachInvite]:
    return (
        db.query(CoachInvite)
        .filter(CoachInvite.coach_id == current_user.id)
        .order_by(CoachInvite.created_at.desc())
        .all()
    )


@router.get("/invitations/athlete", response_model=list[CoachInviteRead])
def list_athlete_invites(
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> list[CoachInvite]:
    _attach_pending_invites_to_user(db, current_user, commit=True)
    return (
        db.query(CoachInvite)
        .filter(
            CoachInvite.athlete_id == current_user.id,
        )
        .order_by(CoachInvite.created_at.desc())
        .all()
    )


@router.post("/invitations/{invite_id}/remind", response_model=CoachInviteRead)
def remind_invite(
    invite_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.COACH)),
    db: Session = Depends(get_db),
) -> CoachInvite:
    invite = db.get(CoachInvite, invite_id)
    if not invite or invite.coach_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite already processed.")
    background_tasks.add_task(send_invite_reminder, invite)
    return invite


@router.post("/invitations/{invite_id}/respond", response_model=CoachInviteRead)
def respond_invite(
    invite_id: int,
    payload: CoachInviteResponse,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(UserRole.ATHLETE)),
    db: Session = Depends(get_db),
) -> CoachInvite:
    invite = db.get(CoachInvite, invite_id)
    if not invite or invite.athlete_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite already processed.")
    invite.responded_at = datetime.utcnow()
    if payload.action == "ACCEPT":
        existing_link = (
            db.query(CoachAthlete)
            .filter(CoachAthlete.coach_id == invite.coach_id, CoachAthlete.athlete_id == current_user.id)
            .first()
        )
        if not existing_link:
            db.add(CoachAthlete(coach_id=invite.coach_id, athlete_id=current_user.id))
        invite.status = InviteStatus.ACCEPTED
    else:
        invite.status = InviteStatus.DECLINED
    db.commit()
    db.refresh(invite)
    if invite.status == InviteStatus.ACCEPTED:
        background_tasks.add_task(send_invite_accepted, invite)
    return invite


def _attach_pending_invites_to_user(db: Session, athlete: User, commit: bool = False) -> None:
    if athlete.role != UserRole.ATHLETE:
        return
    pending = (
        db.query(CoachInvite)
        .filter(
            CoachInvite.athlete_id.is_(None),
            CoachInvite.athlete_email == athlete.email,
            CoachInvite.status == InviteStatus.PENDING,
        )
        .all()
    )
    if not pending:
        return
    for invite in pending:
        invite.athlete_id = athlete.id
    if commit:
        db.commit()
    else:
        db.flush()
