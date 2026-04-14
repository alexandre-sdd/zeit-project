from __future__ import annotations

from datetime import date, datetime

from app.domain.entities import Event, Task
from app.solver.cp_sat_model import build_schedule

WEEK_START = date(2026, 4, 13)


def test_solver_respects_hard_events() -> None:
    result = build_schedule(
        tasks=[
            Task(id=1, user_id=1, title="Deep work", est_duration_min=120, priority=4),
        ],
        events=[
            Event(
                id=1,
                user_id=1,
                title="Standup",
                starts_at=datetime(2026, 4, 13, 10, 0),
                ends_at=datetime(2026, 4, 13, 11, 0),
            )
        ],
        options={"week_start": WEEK_START},
    )

    assert len(result.blocks) == 1
    block = result.blocks[0]
    assert not (block.starts_at < datetime(2026, 4, 13, 11, 0) and block.ends_at > datetime(2026, 4, 13, 10, 0))


def test_solver_enforces_hard_due_dates() -> None:
    result = build_schedule(
        tasks=[
            Task(
                id=1,
                user_id=1,
                title="Prep",
                est_duration_min=120,
                priority=5,
                due_at=datetime(2026, 4, 13, 12, 0),
                due_is_hard=True,
            )
        ],
        events=[],
        options={"week_start": WEEK_START},
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].ends_at <= datetime(2026, 4, 13, 12, 0)


def test_solver_keeps_each_task_as_one_contiguous_block() -> None:
    result = build_schedule(
        tasks=[
            Task(id=1, user_id=1, title="Task A", est_duration_min=90, priority=3),
            Task(id=2, user_id=1, title="Task B", est_duration_min=120, priority=2),
        ],
        events=[],
        options={"week_start": WEEK_START},
    )

    assert {block.task_id for block in result.blocks} == {1, 2}
    assert len(result.blocks) == 2


def test_solver_never_overlaps_scheduled_tasks() -> None:
    result = build_schedule(
        tasks=[
            Task(id=1, user_id=1, title="Task A", est_duration_min=240, priority=5),
            Task(id=2, user_id=1, title="Task B", est_duration_min=240, priority=4),
            Task(id=3, user_id=1, title="Task C", est_duration_min=180, priority=3),
        ],
        events=[],
        options={"week_start": WEEK_START},
    )

    ordered_blocks = sorted(result.blocks, key=lambda block: block.starts_at)
    for previous, current in zip(ordered_blocks, ordered_blocks[1:]):
        assert previous.ends_at <= current.starts_at


def test_solver_returns_partial_schedule_when_capacity_runs_out() -> None:
    result = build_schedule(
        tasks=[
            Task(id=1, user_id=1, title="Task 1", est_duration_min=480, priority=5),
            Task(id=2, user_id=1, title="Task 2", est_duration_min=480, priority=4),
            Task(id=3, user_id=1, title="Task 3", est_duration_min=480, priority=3),
            Task(id=4, user_id=1, title="Task 4", est_duration_min=480, priority=2),
            Task(id=5, user_id=1, title="Task 5", est_duration_min=480, priority=1),
            Task(id=6, user_id=1, title="Task 6", est_duration_min=480, priority=1),
        ],
        events=[],
        options={"week_start": WEEK_START},
    )

    assert len(result.blocks) == 5
    assert any(item.reason == "no_capacity" for item in result.unscheduled_tasks)


def test_solver_keeps_blocks_ending_at_workday_boundary_on_same_day() -> None:
    result = build_schedule(
        tasks=[
            Task(id=1, user_id=1, title="Full day task", est_duration_min=480, priority=5),
        ],
        events=[],
        options={"week_start": WEEK_START},
    )

    assert len(result.blocks) == 1
    assert result.blocks[0].starts_at == datetime(2026, 4, 13, 9, 0)
    assert result.blocks[0].ends_at == datetime(2026, 4, 13, 17, 0)


def test_solver_marks_impossible_hard_due_tasks() -> None:
    result = build_schedule(
        tasks=[
            Task(
                id=1,
                user_id=1,
                title="Impossible due",
                est_duration_min=180,
                priority=5,
                due_at=datetime(2026, 4, 13, 10, 0),
                due_is_hard=True,
            )
        ],
        events=[],
        options={"week_start": WEEK_START},
    )

    assert not result.blocks
    assert result.unscheduled_tasks[0].reason == "hard_due_conflict"
