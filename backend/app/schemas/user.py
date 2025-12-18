from datetime import date, datetime
from typing import Optional

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, computed_field

from ..core.enums import InviteStatus, UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[UserRole] = None


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = {"from_attributes": True}


class AthleteProfileBase(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    category: Optional[str] = None


class AthleteProfileUpdate(AthleteProfileBase):
    pass


class AthleteProfileRead(AthleteProfileBase):
    user_id: int

    model_config = {"from_attributes": True}


class AthleteSummary(BaseModel):
    athlete_id: int
    total_plans: int
    planned_sessions: int
    completed_sessions: int
    total_distance_km: float


class CoachInviteRequest(BaseModel):
    athlete_email: EmailStr


class CoachInviteRead(BaseModel):
    id: int
    coach: UserSummary
    athlete: Optional[UserSummary] = None
    athlete_email: EmailStr
    status: InviteStatus
    created_at: datetime
    responded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @computed_field(return_type=bool)  # type: ignore[misc]
    def requires_signup(self) -> bool:
        return self.athlete is None


class CoachInviteResponse(BaseModel):
    action: Literal["ACCEPT", "DECLINE"]
