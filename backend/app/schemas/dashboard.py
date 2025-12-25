from pydantic import BaseModel


class AthleteMetrics(BaseModel):
    athlete_id: int
    athlete_name: str
    planned_sessions_week: int
    completed_sessions_week: int
    completed_distance_week: float
    compliance_rate: float | None
    pending_sessions_today: int


class CoachAthleteHighlight(BaseModel):
    athlete_id: int
    athlete_name: str
    planned_sessions_week: int
    completed_sessions_week: int
    completed_distance_week: float
    compliance_rate: float | None


class CoachTrendPoint(BaseModel):
    week_start: str
    week_end: str
    planned_sessions: int
    completed_sessions: int
    total_distance: float
    compliance_rate: float | None


class CoachOverview(BaseModel):
    total_athletes: int
    avg_weekly_distance: float
    avg_compliance_rate: float | None
    pending_sessions_today: int
    low_compliance_athletes: int
    trend: list[CoachTrendPoint]
    top_athletes: list[CoachAthleteHighlight]


class AthleteRecentSession(BaseModel):
    id: int
    date: str
    title: str | None = None
    actual_distance: float | None = None
    actual_duration: float | None = None
    actual_rpe: float | None = None


class AthleteDetailMetrics(BaseModel):
    athlete_id: int
    athlete_name: str
    planned_sessions_week: int
    completed_sessions_week: int
    completed_distance_week: float
    compliance_rate: float | None
    current_streak: int
    upcoming_sessions: int
    weekly_trend: list[CoachTrendPoint]
    recent_sessions: list[AthleteRecentSession]
