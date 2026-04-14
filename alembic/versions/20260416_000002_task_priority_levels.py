"""Collapse task priorities to three named levels.

Revision ID: 20260416_000002
Revises: 20260415_000001
Create Date: 2026-04-16 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260416_000002"
down_revision = "20260415_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE tasks
            SET priority = CASE
                WHEN priority >= 4 THEN 3
                WHEN priority >= 2 THEN 2
                ELSE 1
            END
            """
        )
    )

    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "priority",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="2",
        )
        batch_op.create_check_constraint(
            "ck_tasks_priority_levels",
            "priority BETWEEN 1 AND 3",
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("ck_tasks_priority_levels", type_="check")
        batch_op.alter_column(
            "priority",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default="0",
        )
