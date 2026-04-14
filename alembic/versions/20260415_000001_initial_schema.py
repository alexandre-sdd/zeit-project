"""Initial schema

Revision ID: 20260415_000001
Revises: None
Create Date: 2026-04-15 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260415_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("timezone", sa.String(), nullable=False, server_default="America/New_York"),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("est_duration_min", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("due_is_hard", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("preferred_location", sa.String(), nullable=True),
        sa.Column("repeat_rule", sa.String(), nullable=True),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("lock_level", sa.String(), nullable=False, server_default="hard"),
        sa.Column("source", sa.String(), nullable=False, server_default="manual"),
    )
    op.create_table(
        "blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="planned"),
        sa.Column("lock_level", sa.String(), nullable=False, server_default="none"),
        sa.Column("generated_by", sa.String(), nullable=False, server_default="solver"),
        sa.UniqueConstraint("user_id", "starts_at", "ends_at", name="uq_blocks_user_timespan"),
    )
    op.create_table(
        "schedule_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("scheduled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unscheduled_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("constraints_json", sa.Text(), nullable=False),
        sa.Column("tasks_to_plan_json", sa.Text(), nullable=False),
        sa.Column("planned_tasks_json", sa.Text(), nullable=False),
        sa.Column("unplanned_tasks_json", sa.Text(), nullable=False),
        sa.Column("solver_json", sa.Text(), nullable=False),
        sa.Column("solution_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("schedule_runs")
    op.drop_table("blocks")
    op.drop_table("events")
    op.drop_table("tasks")
    op.drop_table("users")
