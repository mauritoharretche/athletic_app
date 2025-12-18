from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .plan import TrainingSessionPlanned


class TrainingSessionDone(Base):
    __tablename__ = "training_sessions_done"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    planned_session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("training_sessions_planned.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_distance: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    actual_duration: Mapped[Optional[int]] = mapped_column(Integer)
    actual_rpe: Mapped[Optional[int]] = mapped_column(Integer)
    surface: Mapped[Optional[str]] = mapped_column(String(80))
    shoes: Mapped[Optional[str]] = mapped_column(String(120))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    planned_session: Mapped[Optional[TrainingSessionPlanned]] = relationship()
