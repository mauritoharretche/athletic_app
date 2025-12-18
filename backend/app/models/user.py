from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.enums import InviteStatus, UserRole
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    athlete_profile: Mapped["AthleteProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    coached_links: Mapped[list["CoachAthlete"]] = relationship(
        back_populates="coach", foreign_keys="CoachAthlete.coach_id"
    )
    assigned_coaches: Mapped[list["CoachAthlete"]] = relationship(
        back_populates="athlete", foreign_keys="CoachAthlete.athlete_id"
    )
    sent_invites: Mapped[list["CoachInvite"]] = relationship(
        back_populates="coach", foreign_keys="CoachInvite.coach_id"
    )
    received_invites: Mapped[list["CoachInvite"]] = relationship(
        back_populates="athlete", foreign_keys="CoachInvite.athlete_id"
    )


class AthleteProfile(Base):
    __tablename__ = "athlete_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    height_cm: Mapped[Optional[float]] = mapped_column(nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped[User] = relationship(back_populates="athlete_profile")


class CoachAthlete(Base):
    __tablename__ = "coach_athlete"
    __table_args__ = (UniqueConstraint("coach_id", "athlete_id", name="coach_athlete_unique"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    since_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    coach: Mapped[User] = relationship(
        back_populates="coached_links", foreign_keys=[coach_id], lazy="joined"
    )
    athlete: Mapped[User] = relationship(
        back_populates="assigned_coaches", foreign_keys=[athlete_id], lazy="joined"
    )


class CoachInvite(Base):
    __tablename__ = "coach_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    athlete_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    athlete_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, native_enum=False), default=InviteStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    coach: Mapped[User] = relationship("User", foreign_keys=[coach_id], lazy="joined")
    athlete: Mapped[Optional[User]] = relationship("User", foreign_keys=[athlete_id], lazy="joined")
