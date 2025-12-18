from pydantic import BaseModel


class AthleteMetrics(BaseModel):
    athlete_id: int
    athlete_name: str
    planned_sessions_week: int
    completed_sessions_week: int
    completed_distance_week: float
    compliance_rate: float | None
    pending_sessions_today: int
