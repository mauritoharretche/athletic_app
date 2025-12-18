from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class TrainingSessionDoneBase(BaseModel):
    date: date
    planned_session_id: Optional[int] = None
    actual_distance: Optional[float] = Field(default=None, ge=0)
    actual_duration: Optional[int] = Field(default=None, ge=0)
    actual_rpe: Optional[int] = Field(default=None, ge=1, le=10)
    surface: Optional[str] = None
    shoes: Optional[str] = None
    notes: Optional[str] = None


class TrainingSessionDoneCreate(TrainingSessionDoneBase):
    pass


class TrainingSessionDoneUpdate(BaseModel):
    date: Optional[date] = None
    planned_session_id: Optional[int] = None
    actual_distance: Optional[float] = Field(default=None, ge=0)
    actual_duration: Optional[int] = Field(default=None, ge=0)
    actual_rpe: Optional[int] = Field(default=None, ge=1, le=10)
    surface: Optional[str] = None
    shoes: Optional[str] = None
    notes: Optional[str] = None


class TrainingSessionDoneRead(TrainingSessionDoneBase):
    id: int
    athlete_id: int

    model_config = {"from_attributes": True}
