"""initial schema

Revision ID: 20240314_0001
Revises: 
Create Date: 2024-03-14 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


dependencies: Union[str, Sequence[str], None] = None
revision = "20240314_0001"
down_revision = None
branch_labels: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "athlete_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
    )

    op.create_table(
        "coach_athlete",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("since_date", sa.Date(), server_default=sa.text("CURRENT_DATE")),
        sa.UniqueConstraint("coach_id", "athlete_id", name="coach_athlete_unique"),
    )

    op.create_table(
        "training_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("goal_type", sa.String(length=80), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_training_plans_athlete_id", "training_plans", ["athlete_id"], unique=False)

    op.create_table(
        "training_sessions_planned",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("training_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("planned_distance", sa.Numeric(5, 2), nullable=True),
        sa.Column("planned_duration", sa.Integer(), nullable=True),
        sa.Column("planned_rpe", sa.Integer(), nullable=True),
        sa.Column("notes_for_athlete", sa.Text(), nullable=True),
    )

    op.create_table(
        "training_sessions_done",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "planned_session_id",
            sa.Integer(),
            sa.ForeignKey("training_sessions_planned.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("actual_distance", sa.Numeric(6, 2), nullable=True),
        sa.Column("actual_duration", sa.Integer(), nullable=True),
        sa.Column("actual_rpe", sa.Integer(), nullable=True),
        sa.Column("surface", sa.String(length=80), nullable=True),
        sa.Column("shoes", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_sessions_done_athlete_id", "training_sessions_done", ["athlete_id"], unique=False)

    op.create_table(
        "external_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("athlete_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=120), unique=True, nullable=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("external_activities")
    op.drop_index("ix_sessions_done_athlete_id", table_name="training_sessions_done")
    op.drop_table("training_sessions_done")
    op.drop_table("training_sessions_planned")
    op.drop_index("ix_training_plans_athlete_id", table_name="training_plans")
    op.drop_table("training_plans")
    op.drop_table("coach_athlete")
    op.drop_table("athlete_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
