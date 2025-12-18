from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.enums import SessionType


class TrainingSessionPlannedBase(BaseModel):
    date: date
    type: SessionType
    title: str
    description: Optional[str] = None
    planned_distance: Optional[float] = Field(default=None, ge=0)
    planned_duration: Optional[int] = Field(default=None, ge=0)
    planned_rpe: Optional[int] = Field(default=None, ge=1, le=10)
    notes_for_athlete: Optional[str] = None


class TrainingSessionPlannedCreate(TrainingSessionPlannedBase):
    pass


class TrainingSessionPlannedRead(TrainingSessionPlannedBase):
    id: int

    model_config = {"from_attributes": True}


class TrainingPlanBase(BaseModel):
    name: str
    goal_type: Optional[str] = None
    start_date: date
    end_date: date
    notes: Optional[str] = None


class TrainingPlanCreate(TrainingPlanBase):
    athlete_id: int
    sessions: List[TrainingSessionPlannedCreate] = []


class TrainingPlanUpdate(TrainingPlanBase):
    pass


class TrainingPlanRead(TrainingPlanBase):
    id: int
    athlete_id: int
    sessions: List[TrainingSessionPlannedRead] = []

    model_config = {"from_attributes": True}


class TrainingPlanDuplicateRequest(BaseModel):
    start_date: date
    target_athlete_id: Optional[int] = None
    name: Optional[str] = None
    end_date: Optional[date] = None
    goal_type: Optional[str] = None
    notes: Optional[str] = None
