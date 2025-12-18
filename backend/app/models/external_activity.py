from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ExternalActivity(Base):
    """Placeholder for future Garmin/external integrations."""

    __tablename__ = "external_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(50))
    external_id: Mapped[str] = mapped_column(String(120), unique=True)
    payload: Mapped[Optional[str]] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
