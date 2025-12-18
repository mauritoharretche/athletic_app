from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .core.config import get_settings
from .core.enums import UserRole
from .core.security import oauth2_scheme
from .database import get_db
from .models.user import CoachAthlete, User
from .schemas.user import TokenData


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise credentials_exception
    token_data = TokenData.model_validate(payload)
    if not token_data.sub:
        raise credentials_exception
    user = db.get(User, int(token_data.sub))
    if user is None:
        raise credentials_exception
    return user


def require_role(expected_role: UserRole):
    def _role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != expected_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role.")
        return current_user

    return _role_dependency


def ensure_athlete_access(
    athlete_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if current_user.role == UserRole.ATHLETE and current_user.id != athlete_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if current_user.role == UserRole.COACH:
        link_exists = (
            db.query(CoachAthlete)
            .filter(
                CoachAthlete.coach_id == current_user.id,
                CoachAthlete.athlete_id == athlete_id,
            )
            .first()
        )
        if not link_exists:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return current_user
