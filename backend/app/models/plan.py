from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.enums import SessionType
from ..database import Base


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    goal_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    sessions: Mapped[list["TrainingSessionPlanned"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class TrainingSessionPlanned(Base):
    __tablename__ = "training_sessions_planned"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[SessionType] = mapped_column(Enum(SessionType, native_enum=False))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    planned_distance: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    planned_duration: Mapped[Optional[int]] = mapped_column(Integer)
    planned_rpe: Mapped[Optional[int]] = mapped_column(Integer)
    notes_for_athlete: Mapped[Optional[str]] = mapped_column(Text)

    plan: Mapped[TrainingPlan] = relationship(back_populates="sessions")
