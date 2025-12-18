from typing import Dict, Optional

from pydantic import BaseModel


class AthleteHistorySummary(BaseModel):
    athlete_id: int
    week_total_distance: float
    week_sessions: int
    week_avg_rpe: Optional[float]
    month_total_distance: float
    month_sessions: int
    month_avg_rpe: Optional[float]
    session_type_distribution: Dict[str, int]
