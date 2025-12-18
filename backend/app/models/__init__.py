from .user import User, AthleteProfile, CoachAthlete, CoachInvite
from .plan import TrainingPlan, TrainingSessionPlanned
from .session import TrainingSessionDone
from .external_activity import ExternalActivity

__all__ = [
    "User",
    "AthleteProfile",
    "CoachAthlete",
    "CoachInvite",
    "TrainingPlan",
    "TrainingSessionPlanned",
    "TrainingSessionDone",
    "ExternalActivity",
]
