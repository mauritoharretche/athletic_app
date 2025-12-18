from datetime import date
from typing import Optional

from pydantic import BaseModel

from .session import TrainingSessionDoneRead


class SessionOverview(BaseModel):
    plan_id: int
    session_id: int
    date: date
    type: str
    title: str
    planned_distance: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_rpe: Optional[int] = None
    completed: bool
    completed_session: Optional[TrainingSessionDoneRead] = None


class AthleteTodayOverview(BaseModel):
    athlete_id: int
    date: date
    today: Optional[SessionOverview] = None
    upcoming: list[SessionOverview]


class WeeklyStat(BaseModel):
    start_date: date
    end_date: date
    total_distance: float
    sessions: int
    avg_rpe: Optional[float] = None
