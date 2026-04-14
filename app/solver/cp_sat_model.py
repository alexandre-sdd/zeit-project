"""
Constraint programming model orchestrating the scheduling logic.

The preferred path uses OR-Tools CP-SAT when the runtime supports it.
For incompatible environments, such as the Python 3.13 runtime used in
this workspace, the module falls back to a deterministic greedy planner
so the demo remains runnable and testable.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from math import ceil, floor
import sys
from typing import Any

from app.domain.entities import Block, Event, ScheduleResult, Task, UnscheduledTask
from app.services.schedule_policy import (
    SLOT_MINUTES,
    SLOTS_PER_DAY,
    TOTAL_WEEKLY_SLOTS,
    WORKDAY_END_HOUR,
    WORKDAY_START_HOUR,
    WORKDAYS_PER_WEEK,
    slot_count,
)


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []

    merged: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _event_busy_intervals(
    events: list[Event],
    week_start: date,
) -> tuple[list[tuple[int, int]], dict[int, list[tuple[int, int]]]]:
    daily_busy: dict[int, list[tuple[int, int]]] = {day_index: [] for day_index in range(WORKDAYS_PER_WEEK)}

    for event in events:
        for day_index in range(WORKDAYS_PER_WEEK):
            day = week_start + timedelta(days=day_index)
            day_start = datetime.combine(day, time(hour=WORKDAY_START_HOUR))
            day_end = datetime.combine(day, time(hour=WORKDAY_END_HOUR))

            overlap_start = max(event.starts_at, day_start)
            overlap_end = min(event.ends_at, day_end)
            if overlap_start >= overlap_end:
                continue

            start_minutes = (overlap_start - day_start).total_seconds() / 60
            end_minutes = (overlap_end - day_start).total_seconds() / 60
            start_slot = max(0, floor(start_minutes / SLOT_MINUTES))
            end_slot = min(SLOTS_PER_DAY, ceil(end_minutes / SLOT_MINUTES))
            if end_slot > start_slot:
                daily_busy[day_index].append((start_slot, end_slot))

    global_intervals: list[tuple[int, int]] = []
    for day_index, intervals in daily_busy.items():
        merged = _merge_intervals(intervals)
        daily_busy[day_index] = merged
        day_offset = day_index * SLOTS_PER_DAY
        for start_slot, end_slot in merged:
            global_intervals.append((day_offset + start_slot, end_slot - start_slot))
    return global_intervals, daily_busy


def _latest_end_slot(due_at: datetime, week_start: date) -> int:
    day_index = (due_at.date() - week_start).days
    if day_index < 0:
        return 0
    if day_index >= WORKDAYS_PER_WEEK:
        return TOTAL_WEEKLY_SLOTS

    day_start = datetime.combine(due_at.date(), time(hour=WORKDAY_START_HOUR))
    minutes_since_day_start = (due_at - day_start).total_seconds() / 60
    slot_limit = floor(minutes_since_day_start / SLOT_MINUTES)
    slot_limit = max(0, min(SLOTS_PER_DAY, slot_limit))
    return (day_index * SLOTS_PER_DAY) + slot_limit


def _valid_starts(duration_slots: int, *, latest_end: int | None = None) -> list[int]:
    starts: list[int] = []
    for day_index in range(WORKDAYS_PER_WEEK):
        day_offset = day_index * SLOTS_PER_DAY
        for start_slot in range(SLOTS_PER_DAY - duration_slots + 1):
            absolute_start = day_offset + start_slot
            absolute_end = absolute_start + duration_slots
            if latest_end is not None and absolute_end > latest_end:
                continue
            starts.append(absolute_start)
    return starts


def _overlaps_busy(day_intervals: list[tuple[int, int]], start_slot: int, duration_slots: int) -> bool:
    end_slot = start_slot + duration_slots
    return any(start_slot < busy_end and end_slot > busy_start for busy_start, busy_end in day_intervals)


def _has_window_outside_fixed_events(
    starts: list[int],
    duration_slots: int,
    busy_by_day: dict[int, list[tuple[int, int]]],
) -> bool:
    for absolute_start in starts:
        day_index = absolute_start // SLOTS_PER_DAY
        day_start = absolute_start % SLOTS_PER_DAY
        if not _overlaps_busy(busy_by_day[day_index], day_start, duration_slots):
            return True
    return False


def _slot_to_datetime(slot_index: int, week_start: date) -> datetime:
    day_index = slot_index // SLOTS_PER_DAY
    slot_offset = slot_index % SLOTS_PER_DAY
    day = week_start + timedelta(days=day_index)
    return datetime.combine(day, time(hour=WORKDAY_START_HOUR)) + timedelta(minutes=slot_offset * SLOT_MINUTES)


def _slot_end_to_datetime(slot_index: int, week_start: date) -> datetime:
    """Map a compressed end slot back to the wall-clock edge of the workday."""
    if slot_index > 0 and slot_index % SLOTS_PER_DAY == 0:
        day_index = (slot_index // SLOTS_PER_DAY) - 1
        day = week_start + timedelta(days=day_index)
        return datetime.combine(day, time(hour=WORKDAY_END_HOUR))
    return _slot_to_datetime(slot_index, week_start)


def _task_sort_key(task: Task) -> tuple[int, int, datetime, int, str]:
    due_bucket = 0 if task.due_is_hard else 1 if task.due_at is not None else 2
    due_value = task.due_at or datetime.max
    duration_slots = slot_count(task.est_duration_min)
    return (-max(task.priority, 1), due_bucket, due_value, -duration_slots, task.title)


def _make_unscheduled(task: Task, reason: str) -> UnscheduledTask:
    return UnscheduledTask(
        task_id=task.id,
        user_id=task.user_id,
        title=task.title,
        est_duration_min=task.est_duration_min,
        priority=task.priority,
        due_at=task.due_at,
        reason=reason,
    )


def _available_starts_for_soft_due(task: Task, duration_slots: int, starts: list[int], week_start: date) -> list[int]:
    if task.due_at is None:
        return starts

    due_slot = _latest_end_slot(task.due_at, week_start)
    on_time = [start for start in starts if start + duration_slots <= due_slot]
    late = [start for start in starts if start + duration_slots > due_slot]
    return on_time + late


def _build_schedule_greedy(tasks: list[Task], events: list[Event], week_start: date) -> ScheduleResult:
    _, fixed_busy = _event_busy_intervals(events, week_start)
    current_busy = {day_index: list(intervals) for day_index, intervals in fixed_busy.items()}

    blocks: list[Block] = []
    unscheduled: list[UnscheduledTask] = []

    for task in sorted(tasks, key=_task_sort_key):
        duration_slots = slot_count(task.est_duration_min)
        if duration_slots > SLOTS_PER_DAY:
            unscheduled.append(_make_unscheduled(task, "outside_work_window"))
            continue

        latest_end = _latest_end_slot(task.due_at, week_start) if task.due_at else None
        valid_starts = _valid_starts(duration_slots, latest_end=latest_end if task.due_is_hard else None)
        if not valid_starts:
            unscheduled.append(_make_unscheduled(task, "hard_due_conflict" if task.due_is_hard else "outside_work_window"))
            continue

        if task.due_is_hard and not _has_window_outside_fixed_events(valid_starts, duration_slots, fixed_busy):
            unscheduled.append(_make_unscheduled(task, "hard_due_conflict"))
            continue

        candidate_starts = _available_starts_for_soft_due(task, duration_slots, valid_starts, week_start)
        chosen_start: int | None = None
        for absolute_start in candidate_starts:
            day_index = absolute_start // SLOTS_PER_DAY
            day_slot = absolute_start % SLOTS_PER_DAY
            if _overlaps_busy(current_busy[day_index], day_slot, duration_slots):
                continue
            chosen_start = absolute_start
            current_busy[day_index].append((day_slot, day_slot + duration_slots))
            current_busy[day_index] = _merge_intervals(current_busy[day_index])
            break

        if chosen_start is None:
            unscheduled.append(_make_unscheduled(task, "no_capacity"))
            continue

        end_slot = chosen_start + duration_slots
        blocks.append(
            Block(
                id=None,
                user_id=task.user_id,
                task_id=task.id,
                event_id=None,
                starts_at=_slot_to_datetime(chosen_start, week_start),
                ends_at=_slot_end_to_datetime(end_slot, week_start),
                location=task.preferred_location,
                status="planned",
                lock_level="none",
                generated_by="solver",
            )
        )

    blocks.sort(key=lambda block: block.starts_at)
    unscheduled.sort(key=lambda item: (-item.priority, item.title))
    return ScheduleResult(blocks=blocks, unscheduled_tasks=unscheduled)


def _load_cp_model():
    if sys.version_info >= (3, 13):
        return None

    try:
        from ortools.sat.python import cp_model  # type: ignore
    except Exception:
        return None
    return cp_model


def _build_schedule_cp_sat(tasks: list[Task], events: list[Event], week_start: date) -> ScheduleResult | None:
    cp_model = _load_cp_model()
    if cp_model is None:
        return None

    model = cp_model.CpModel()
    busy_intervals, busy_by_day = _event_busy_intervals(events, week_start)
    intervals = []
    for index, (start_slot, duration_slots) in enumerate(busy_intervals):
        start_const = model.NewConstant(start_slot)
        end_const = model.NewConstant(start_slot + duration_slots)
        intervals.append(model.NewIntervalVar(start_const, duration_slots, end_const, f"busy_{index}"))

    scheduled_candidates: list[dict[str, object]] = []
    unscheduled_tasks: list[UnscheduledTask] = []

    for task in tasks:
        duration_slots = slot_count(task.est_duration_min)
        if duration_slots > SLOTS_PER_DAY:
            unscheduled_tasks.append(_make_unscheduled(task, "outside_work_window"))
            continue

        latest_end = _latest_end_slot(task.due_at, week_start) if task.due_at else None
        valid_starts = _valid_starts(duration_slots, latest_end=latest_end if task.due_is_hard else None)
        if not valid_starts:
            unscheduled_tasks.append(_make_unscheduled(task, "hard_due_conflict" if task.due_is_hard else "outside_work_window"))
            continue

        if task.due_is_hard and not _has_window_outside_fixed_events(valid_starts, duration_slots, busy_by_day):
            unscheduled_tasks.append(_make_unscheduled(task, "hard_due_conflict"))
            continue

        start_var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(valid_starts),
            f"task_{task.id}_start",
        )
        end_var = model.NewIntVar(0, TOTAL_WEEKLY_SLOTS, f"task_{task.id}_end")
        present_var = model.NewBoolVar(f"task_{task.id}_present")
        interval = model.NewOptionalIntervalVar(
            start_var,
            duration_slots,
            end_var,
            present_var,
            f"task_{task.id}_interval",
        )
        intervals.append(interval)

        if task.due_is_hard and latest_end is not None:
            model.Add(end_var <= latest_end).OnlyEnforceIf(present_var)

        on_time_var = None
        if task.due_at is not None:
            due_slot = _latest_end_slot(task.due_at, week_start)
            if due_slot >= TOTAL_WEEKLY_SLOTS:
                on_time_var = present_var
            elif due_slot > 0:
                on_time_var = model.NewBoolVar(f"task_{task.id}_on_time")
                model.Add(on_time_var == 0).OnlyEnforceIf(present_var.Not())
                model.Add(end_var <= due_slot).OnlyEnforceIf(on_time_var)
                model.Add(end_var > due_slot).OnlyEnforceIf([present_var, on_time_var.Not()])

        start_reward = model.NewIntVar(0, TOTAL_WEEKLY_SLOTS, f"task_{task.id}_start_reward")
        model.Add(start_reward == TOTAL_WEEKLY_SLOTS - start_var).OnlyEnforceIf(present_var)
        model.Add(start_reward == 0).OnlyEnforceIf(present_var.Not())

        scheduled_candidates.append(
            {
                "task": task,
                "start_var": start_var,
                "end_var": end_var,
                "present_var": present_var,
                "start_reward": start_reward,
                "duration_slots": duration_slots,
                "on_time_var": on_time_var,
            }
        )

    model.AddNoOverlap(intervals)
    objective_terms = []
    for candidate in scheduled_candidates:
        task = candidate["task"]
        priority_weight = max(task.priority, 1)
        objective_terms.append(candidate["present_var"] * priority_weight * int(candidate["duration_slots"]) * 10_000)
        objective_terms.append(candidate["start_reward"])
        if candidate["on_time_var"] is not None:
            objective_terms.append(candidate["on_time_var"] * priority_weight * 500)

    if objective_terms:
        model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ScheduleResult(blocks=[], unscheduled_tasks=unscheduled_tasks)

    blocks: list[Block] = []
    for candidate in scheduled_candidates:
        task = candidate["task"]
        if solver.Value(candidate["present_var"]):
            start_slot = solver.Value(candidate["start_var"])
            end_slot = solver.Value(candidate["end_var"])
            blocks.append(
                Block(
                    id=None,
                    user_id=task.user_id,
                    task_id=task.id,
                    event_id=None,
                    starts_at=_slot_to_datetime(start_slot, week_start),
                    ends_at=_slot_end_to_datetime(end_slot, week_start),
                    location=task.preferred_location,
                    status="planned",
                    lock_level="none",
                    generated_by="solver",
                )
            )
            continue

        unscheduled_tasks.append(_make_unscheduled(task, "no_capacity"))

    blocks.sort(key=lambda block: block.starts_at)
    unscheduled_tasks.sort(key=lambda item: (-item.priority, item.title))
    return ScheduleResult(blocks=blocks, unscheduled_tasks=unscheduled_tasks)


def build_schedule(
    tasks: Iterable[Task],
    events: Iterable[Event],
    *,
    options: dict[str, Any] | None = None,
) -> ScheduleResult:
    """
    Build a demo-ready schedule using OR-Tools when possible.

    Args:
        tasks: Candidate tasks to place on the timeline.
        events: Hard/soft events that constrain availability.
        options: Optional solver configuration overrides.

    Returns:
        Scheduled blocks plus any tasks left unscheduled with reasons.
    """
    task_list = list(tasks)
    event_list = list(events)
    week_start = (options or {}).get("week_start")
    if not isinstance(week_start, date):
        raise ValueError("`week_start` must be provided to build_schedule")

    if not task_list:
        return ScheduleResult(blocks=[], unscheduled_tasks=[])

    cp_sat_result = _build_schedule_cp_sat(task_list, event_list, week_start)
    if cp_sat_result is not None:
        return cp_sat_result
    return _build_schedule_greedy(task_list, event_list, week_start)
