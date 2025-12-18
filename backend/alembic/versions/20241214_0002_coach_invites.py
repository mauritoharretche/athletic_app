"""coach invites table

Revision ID: 20241214_0002
Revises: 20240314_0001
Create Date: 2024-12-14 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20241214_0002"
down_revision: Union[str, None] = "20240314_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coach_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("athlete_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_coach_invites_coach_id", "coach_invites", ["coach_id"])
    op.create_index("ix_coach_invites_athlete_id", "coach_invites", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_coach_invites_athlete_id", table_name="coach_invites")
    op.drop_index("ix_coach_invites_coach_id", table_name="coach_invites")
    op.drop_table("coach_invites")
