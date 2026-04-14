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

from app.core.priorities import normalize_priority, priority_label
from app.domain.entities import Block, Event, ScheduleResult, SolverRun, Task, UnscheduledTask
from app.services.schedule_policy import (
    SLOT_MINUTES,
    WorkdayWindow,
    resolve_workday_window,
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
    workday_window: WorkdayWindow,
) -> tuple[list[tuple[int, int]], dict[int, list[tuple[int, int]]]]:
    daily_busy: dict[int, list[tuple[int, int]]] = {day_index: [] for day_index in range(WORKDAYS_PER_WEEK)}
    slots_per_day = workday_window.slots_per_day

    for event in events:
        for day_index in range(WORKDAYS_PER_WEEK):
            day = week_start + timedelta(days=day_index)
            day_start = datetime.combine(day, workday_window.start_time)
            day_end = datetime.combine(day, workday_window.end_time)

            overlap_start = max(event.starts_at, day_start)
            overlap_end = min(event.ends_at, day_end)
            if overlap_start >= overlap_end:
                continue

            start_minutes = (overlap_start - day_start).total_seconds() / 60
            end_minutes = (overlap_end - day_start).total_seconds() / 60
            start_slot = max(0, floor(start_minutes / SLOT_MINUTES))
            end_slot = min(slots_per_day, ceil(end_minutes / SLOT_MINUTES))
            if end_slot > start_slot:
                daily_busy[day_index].append((start_slot, end_slot))

    global_intervals: list[tuple[int, int]] = []
    for day_index, intervals in daily_busy.items():
        merged = _merge_intervals(intervals)
        daily_busy[day_index] = merged
        day_offset = day_index * slots_per_day
        for start_slot, end_slot in merged:
            global_intervals.append((day_offset + start_slot, end_slot - start_slot))
    return global_intervals, daily_busy


def _latest_end_slot(due_at: datetime, week_start: date, workday_window: WorkdayWindow) -> int:
    day_index = (due_at.date() - week_start).days
    slots_per_day = workday_window.slots_per_day
    if day_index < 0:
        return 0
    if day_index >= WORKDAYS_PER_WEEK:
        return workday_window.total_weekly_slots

    day_start = datetime.combine(due_at.date(), workday_window.start_time)
    minutes_since_day_start = (due_at - day_start).total_seconds() / 60
    slot_limit = floor(minutes_since_day_start / SLOT_MINUTES)
    slot_limit = max(0, min(slots_per_day, slot_limit))
    return (day_index * slots_per_day) + slot_limit


def _valid_starts(duration_slots: int, *, slots_per_day: int, latest_end: int | None = None) -> list[int]:
    starts: list[int] = []
    for day_index in range(WORKDAYS_PER_WEEK):
        day_offset = day_index * slots_per_day
        for start_slot in range(slots_per_day - duration_slots + 1):
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
    *,
    slots_per_day: int,
) -> bool:
    for absolute_start in starts:
        day_index = absolute_start // slots_per_day
        day_start = absolute_start % slots_per_day
        if not _overlaps_busy(busy_by_day[day_index], day_start, duration_slots):
            return True
    return False


def _slot_to_datetime(slot_index: int, week_start: date, workday_window: WorkdayWindow) -> datetime:
    slots_per_day = workday_window.slots_per_day
    day_index = slot_index // slots_per_day
    slot_offset = slot_index % slots_per_day
    day = week_start + timedelta(days=day_index)
    return datetime.combine(day, workday_window.start_time) + timedelta(minutes=slot_offset * SLOT_MINUTES)


def _slot_end_to_datetime(slot_index: int, week_start: date, workday_window: WorkdayWindow) -> datetime:
    """Map a compressed end slot back to the wall-clock edge of the workday."""
    slots_per_day = workday_window.slots_per_day
    if slot_index > 0 and slot_index % slots_per_day == 0:
        day_index = (slot_index // slots_per_day) - 1
        day = week_start + timedelta(days=day_index)
        return datetime.combine(day, workday_window.end_time)
    return _slot_to_datetime(slot_index, week_start, workday_window)


def _task_sort_key(task: Task) -> tuple[int, int, datetime, int, str]:
    due_bucket = 0 if task.due_is_hard else 1 if task.due_at is not None else 2
    due_value = task.due_at or datetime.max
    duration_slots = slot_count(task.est_duration_min)
    priority = normalize_priority(task.priority)
    return (-priority, due_bucket, due_value, -duration_slots, task.title)


def _make_unscheduled(task: Task, reason: str) -> UnscheduledTask:
    normalized_priority = normalize_priority(task.priority)
    return UnscheduledTask(
        task_id=task.id,
        user_id=task.user_id,
        title=task.title,
        est_duration_min=task.est_duration_min,
        priority=normalized_priority,
        due_at=task.due_at,
        reason=reason,
    )


def _task_sort_details(task: Task) -> dict[str, Any]:
    due_bucket = 0 if task.due_is_hard else 1 if task.due_at is not None else 2
    due_value = task.due_at or datetime.max
    duration_slots = slot_count(task.est_duration_min)
    normalized_priority = normalize_priority(task.priority)
    return {
        "priority": normalized_priority,
        "priority_label": priority_label(normalized_priority),
        "priority_weight": normalized_priority,
        "due_bucket": due_bucket,
        "due_value": None if due_value == datetime.max else due_value,
        "duration_slots": duration_slots,
        "title": task.title,
    }


def _task_trace_header(task: Task, evaluation_index: int) -> dict[str, Any]:
    normalized_priority = normalize_priority(task.priority)
    return {
        "evaluation_index": evaluation_index,
        "task_id": task.id,
        "title": task.title,
        "priority": normalized_priority,
        "priority_label": priority_label(normalized_priority),
        "est_duration_min": task.est_duration_min,
        "due_at": task.due_at,
        "due_is_hard": task.due_is_hard,
        "sort_details": _task_sort_details(task),
    }


def _slot_window_payload(
    absolute_start: int,
    duration_slots: int,
    week_start: date,
    workday_window: WorkdayWindow,
) -> dict[str, Any]:
    slots_per_day = workday_window.slots_per_day
    day_index = absolute_start // slots_per_day
    day_slot = absolute_start % slots_per_day
    absolute_end = absolute_start + duration_slots
    return {
        "absolute_start_slot": absolute_start,
        "absolute_end_slot": absolute_end,
        "day_index": day_index,
        "day_slot": day_slot,
        "duration_slots": duration_slots,
        "duration_min": duration_slots * SLOT_MINUTES,
        "starts_at": _slot_to_datetime(absolute_start, week_start, workday_window),
        "ends_at": _slot_end_to_datetime(absolute_end, week_start, workday_window),
    }


def _segment_payload(
    *,
    kind: str,
    day_index: int,
    start_slot: int,
    end_slot: int,
    week_start: date,
    workday_window: WorkdayWindow,
    title: str | None = None,
    task_id: int | None = None,
    event_id: int | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    absolute_start = (day_index * workday_window.slots_per_day) + start_slot
    absolute_end = (day_index * workday_window.slots_per_day) + end_slot
    return {
        "kind": kind,
        "day_index": day_index,
        "start_slot": start_slot,
        "end_slot": end_slot,
        "title": title,
        "task_id": task_id,
        "event_id": event_id,
        "source": source,
        "starts_at": _slot_to_datetime(absolute_start, week_start, workday_window),
        "ends_at": _slot_end_to_datetime(absolute_end, week_start, workday_window),
    }


def _event_segments(
    events: list[Event],
    week_start: date,
    workday_window: WorkdayWindow,
) -> dict[int, list[dict[str, Any]]]:
    segments: dict[int, list[dict[str, Any]]] = {day_index: [] for day_index in range(WORKDAYS_PER_WEEK)}
    slots_per_day = workday_window.slots_per_day

    for event in events:
        for day_index in range(WORKDAYS_PER_WEEK):
            day = week_start + timedelta(days=day_index)
            day_start = datetime.combine(day, workday_window.start_time)
            day_end = datetime.combine(day, workday_window.end_time)

            overlap_start = max(event.starts_at, day_start)
            overlap_end = min(event.ends_at, day_end)
            if overlap_start >= overlap_end:
                continue

            start_minutes = (overlap_start - day_start).total_seconds() / 60
            end_minutes = (overlap_end - day_start).total_seconds() / 60
            start_slot = max(0, floor(start_minutes / SLOT_MINUTES))
            end_slot = min(slots_per_day, ceil(end_minutes / SLOT_MINUTES))
            if end_slot <= start_slot:
                continue

            segments[day_index].append(
                _segment_payload(
                    kind="event",
                    day_index=day_index,
                    start_slot=start_slot,
                    end_slot=end_slot,
                    week_start=week_start,
                    workday_window=workday_window,
                    title=event.title,
                    event_id=event.id,
                    source=event.source,
                )
            )

    return segments


def _find_blockers(
    segments: list[dict[str, Any]],
    start_slot: int,
    duration_slots: int,
) -> list[dict[str, Any]]:
    end_slot = start_slot + duration_slots
    blockers: list[dict[str, Any]] = []
    for segment in sorted(segments, key=lambda item: (item["start_slot"], item["end_slot"])):
        if start_slot < int(segment["end_slot"]) and end_slot > int(segment["start_slot"]):
            blockers.append(segment)
    return blockers


def _largest_free_gap_minutes(
    segments_by_day: dict[int, list[dict[str, Any]]],
    workday_window: WorkdayWindow,
) -> int:
    largest_gap_slots = 0
    slots_per_day = workday_window.slots_per_day
    for day_index in range(WORKDAYS_PER_WEEK):
        merged = _merge_intervals(
            [(int(segment["start_slot"]), int(segment["end_slot"])) for segment in segments_by_day[day_index]]
        )
        cursor = 0
        for start_slot, end_slot in merged:
            largest_gap_slots = max(largest_gap_slots, start_slot - cursor)
            cursor = max(cursor, end_slot)
        largest_gap_slots = max(largest_gap_slots, slots_per_day - cursor)
    return largest_gap_slots * SLOT_MINUTES


def get_solver_runtime_status() -> SolverRun:
    """Describe whether the OR-Tools CP-SAT path can run in this environment."""
    cp_model = _load_cp_model()
    if cp_model is not None:
        return SolverRun(
            engine="or_tools_cp_sat",
            ortools_available=True,
            status="READY",
            message="OR-Tools CP-SAT is available in this runtime.",
        )

    if sys.version_info >= (3, 13):
        message = "OR-Tools CP-SAT is unavailable in this runtime, so the app will use the greedy fallback."
    else:
        message = "OR-Tools CP-SAT could not be imported, so the app will use the greedy fallback."
    return SolverRun(
        engine="greedy_fallback",
        ortools_available=False,
        status="FALLBACK_READY",
        message=message,
    )


def _available_starts_for_soft_due(
    task: Task,
    duration_slots: int,
    starts: list[int],
    week_start: date,
    workday_window: WorkdayWindow,
) -> list[int]:
    if task.due_at is None:
        return starts

    due_slot = _latest_end_slot(task.due_at, week_start, workday_window)
    on_time = [start for start in starts if start + duration_slots <= due_slot]
    late = [start for start in starts if start + duration_slots > due_slot]
    return on_time + late


def _build_schedule_greedy(
    tasks: list[Task],
    events: list[Event],
    week_start: date,
    workday_window: WorkdayWindow,
) -> ScheduleResult:
    _, fixed_busy = _event_busy_intervals(events, week_start, workday_window)
    slots_per_day = workday_window.slots_per_day
    current_busy = {day_index: list(intervals) for day_index, intervals in fixed_busy.items()}
    fixed_segments = _event_segments(events, week_start, workday_window)
    occupied_segments = {
        day_index: list(segments)
        for day_index, segments in fixed_segments.items()
    }
    ordered_tasks = sorted(tasks, key=_task_sort_key)
    task_order = [_task_trace_header(task, index) for index, task in enumerate(ordered_tasks)]

    blocks: list[Block] = []
    unscheduled: list[UnscheduledTask] = []
    task_traces: list[dict[str, Any]] = []

    for evaluation_index, task in enumerate(ordered_tasks):
        trace = _task_trace_header(task, evaluation_index)
        duration_slots = slot_count(task.est_duration_min)
        trace["duration_slots"] = duration_slots
        trace["largest_available_gap_min_before"] = _largest_free_gap_minutes(occupied_segments, workday_window)
        if duration_slots > slots_per_day:
            trace["decision"] = "unscheduled"
            trace["reason"] = "outside_work_window"
            unscheduled.append(_make_unscheduled(task, "outside_work_window"))
            task_traces.append(trace)
            continue

        latest_end = _latest_end_slot(task.due_at, week_start, workday_window) if task.due_at else None
        trace["latest_end_slot"] = latest_end
        trace["latest_end_at"] = (
            _slot_end_to_datetime(latest_end, week_start, workday_window) if latest_end is not None else None
        )
        valid_starts = _valid_starts(
            duration_slots,
            slots_per_day=slots_per_day,
            latest_end=latest_end if task.due_is_hard else None,
        )
        trace["valid_start_count"] = len(valid_starts)
        trace["valid_windows"] = [
            _slot_window_payload(start, duration_slots, week_start, workday_window)
            for start in valid_starts
        ]
        if not valid_starts:
            trace["decision"] = "unscheduled"
            trace["reason"] = "hard_due_conflict" if task.due_is_hard else "outside_work_window"
            unscheduled.append(_make_unscheduled(task, "hard_due_conflict" if task.due_is_hard else "outside_work_window"))
            task_traces.append(trace)
            continue

        if task.due_is_hard and not _has_window_outside_fixed_events(
            valid_starts,
            duration_slots,
            fixed_busy,
            slots_per_day=slots_per_day,
        ):
            trace["attempts"] = []
            for start in valid_starts:
                day_index = start // slots_per_day
                day_slot = start % slots_per_day
                trace["attempts"].append(
                    {
                        **_slot_window_payload(start, duration_slots, week_start, workday_window),
                        "result": "rejected",
                        "rejection_reason": "fixed_event_conflict",
                        "blockers": _find_blockers(fixed_segments[day_index], day_slot, duration_slots),
                    }
                )
            trace["decision"] = "unscheduled"
            trace["reason"] = "hard_due_conflict"
            unscheduled.append(_make_unscheduled(task, "hard_due_conflict"))
            task_traces.append(trace)
            continue

        candidate_starts = _available_starts_for_soft_due(task, duration_slots, valid_starts, week_start, workday_window)
        trace["candidate_windows_in_order"] = [
            _slot_window_payload(start, duration_slots, week_start, workday_window)
            for start in candidate_starts
        ]
        trace["attempts"] = []
        chosen_start: int | None = None
        for absolute_start in candidate_starts:
            day_index = absolute_start // slots_per_day
            day_slot = absolute_start % slots_per_day
            blockers = _find_blockers(occupied_segments[day_index], day_slot, duration_slots)
            if _overlaps_busy(current_busy[day_index], day_slot, duration_slots):
                trace["attempts"].append(
                    {
                        **_slot_window_payload(absolute_start, duration_slots, week_start, workday_window),
                        "result": "rejected",
                        "rejection_reason": "busy_overlap",
                        "blockers": blockers,
                    }
                )
                continue
            chosen_start = absolute_start
            current_busy[day_index].append((day_slot, day_slot + duration_slots))
            current_busy[day_index] = _merge_intervals(current_busy[day_index])
            task_segment = _segment_payload(
                kind="task",
                day_index=day_index,
                start_slot=day_slot,
                end_slot=day_slot + duration_slots,
                week_start=week_start,
                workday_window=workday_window,
                title=task.title,
                task_id=task.id,
                source="solver",
            )
            occupied_segments[day_index].append(task_segment)
            trace["attempts"].append(
                {
                    **_slot_window_payload(absolute_start, duration_slots, week_start, workday_window),
                    "result": "accepted",
                    "blockers": [],
                }
            )
            trace["decision"] = "scheduled"
            trace["chosen_window"] = _slot_window_payload(absolute_start, duration_slots, week_start, workday_window)
            break

        if chosen_start is None:
            trace["decision"] = "unscheduled"
            trace["reason"] = "no_capacity"
            trace["largest_available_gap_min_after"] = _largest_free_gap_minutes(occupied_segments, workday_window)
            unscheduled.append(_make_unscheduled(task, "no_capacity"))
            task_traces.append(trace)
            continue

        end_slot = chosen_start + duration_slots
        blocks.append(
            Block(
                id=None,
                user_id=task.user_id,
                task_id=task.id,
                event_id=None,
                starts_at=_slot_to_datetime(chosen_start, week_start, workday_window),
                ends_at=_slot_end_to_datetime(end_slot, week_start, workday_window),
                location=task.preferred_location,
                status="planned",
                lock_level="none",
                generated_by="solver",
            )
        )
        task_traces.append(trace)

    blocks.sort(key=lambda block: block.starts_at)
    unscheduled.sort(key=lambda item: (-item.priority, item.title))
    return ScheduleResult(
        blocks=blocks,
        unscheduled_tasks=unscheduled,
        solver_run=SolverRun(
            engine="greedy_fallback",
            ortools_available=False,
            status="FALLBACK_GREEDY",
            message=f"Greedy fallback scheduled {len(blocks)} blocks and left {len(unscheduled)} tasks unscheduled.",
            diagnostics={
                "strategy": "greedy_fallback",
                "task_order": task_order,
                "task_traces": task_traces,
            },
        ),
    )


def _load_cp_model():
    if sys.version_info >= (3, 13):
        return None

    try:
        from ortools.sat.python import cp_model  # type: ignore
    except Exception:
        return None
    return cp_model


def _build_schedule_cp_sat(
    tasks: list[Task],
    events: list[Event],
    week_start: date,
    workday_window: WorkdayWindow,
) -> ScheduleResult | None:
    cp_model = _load_cp_model()
    if cp_model is None:
        return None

    model = cp_model.CpModel()
    busy_intervals, busy_by_day = _event_busy_intervals(events, week_start, workday_window)
    fixed_segments = _event_segments(events, week_start, workday_window)
    slots_per_day = workday_window.slots_per_day
    total_weekly_slots = workday_window.total_weekly_slots
    intervals = []
    for index, (start_slot, duration_slots) in enumerate(busy_intervals):
        start_const = model.NewConstant(start_slot)
        end_const = model.NewConstant(start_slot + duration_slots)
        intervals.append(model.NewIntervalVar(start_const, duration_slots, end_const, f"busy_{index}"))

    scheduled_candidates: list[dict[str, object]] = []
    unscheduled_tasks: list[UnscheduledTask] = []
    task_traces: list[dict[str, Any]] = []
    task_order = [_task_trace_header(task, index) for index, task in enumerate(tasks)]

    for evaluation_index, task in enumerate(tasks):
        trace = _task_trace_header(task, evaluation_index)
        duration_slots = slot_count(task.est_duration_min)
        trace["duration_slots"] = duration_slots
        trace["largest_available_gap_min_before"] = _largest_free_gap_minutes(fixed_segments, workday_window)
        if duration_slots > slots_per_day:
            trace["decision"] = "unscheduled"
            trace["reason"] = "outside_work_window"
            unscheduled_tasks.append(_make_unscheduled(task, "outside_work_window"))
            task_traces.append(trace)
            continue

        latest_end = _latest_end_slot(task.due_at, week_start, workday_window) if task.due_at else None
        trace["latest_end_slot"] = latest_end
        trace["latest_end_at"] = (
            _slot_end_to_datetime(latest_end, week_start, workday_window) if latest_end is not None else None
        )
        valid_starts = _valid_starts(
            duration_slots,
            slots_per_day=slots_per_day,
            latest_end=latest_end if task.due_is_hard else None,
        )
        trace["valid_start_count"] = len(valid_starts)
        trace["valid_windows"] = [
            _slot_window_payload(start, duration_slots, week_start, workday_window)
            for start in valid_starts
        ]
        if not valid_starts:
            trace["decision"] = "unscheduled"
            trace["reason"] = "hard_due_conflict" if task.due_is_hard else "outside_work_window"
            unscheduled_tasks.append(_make_unscheduled(task, "hard_due_conflict" if task.due_is_hard else "outside_work_window"))
            task_traces.append(trace)
            continue

        if task.due_is_hard and not _has_window_outside_fixed_events(
            valid_starts,
            duration_slots,
            busy_by_day,
            slots_per_day=slots_per_day,
        ):
            trace["attempts"] = []
            for start in valid_starts:
                day_index = start // slots_per_day
                day_slot = start % slots_per_day
                trace["attempts"].append(
                    {
                        **_slot_window_payload(start, duration_slots, week_start, workday_window),
                        "result": "rejected",
                        "rejection_reason": "fixed_event_conflict",
                        "blockers": _find_blockers(fixed_segments[day_index], day_slot, duration_slots),
                    }
                )
            trace["decision"] = "unscheduled"
            trace["reason"] = "hard_due_conflict"
            unscheduled_tasks.append(_make_unscheduled(task, "hard_due_conflict"))
            task_traces.append(trace)
            continue

        start_var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(valid_starts),
            f"task_{task.id}_start",
        )
        end_var = model.NewIntVar(0, total_weekly_slots, f"task_{task.id}_end")
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
            due_slot = _latest_end_slot(task.due_at, week_start, workday_window)
            if due_slot >= total_weekly_slots:
                on_time_var = present_var
            elif due_slot > 0:
                on_time_var = model.NewBoolVar(f"task_{task.id}_on_time")
                model.Add(on_time_var == 0).OnlyEnforceIf(present_var.Not())
                model.Add(end_var <= due_slot).OnlyEnforceIf(on_time_var)
                model.Add(end_var > due_slot).OnlyEnforceIf([present_var, on_time_var.Not()])

        start_reward = model.NewIntVar(0, total_weekly_slots, f"task_{task.id}_start_reward")
        model.Add(start_reward == total_weekly_slots - start_var).OnlyEnforceIf(present_var)
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
                "trace": trace,
            }
        )
        task_traces.append(trace)

    model.AddNoOverlap(intervals)
    objective_terms = []
    for candidate in scheduled_candidates:
        task = candidate["task"]
        priority_weight = normalize_priority(task.priority)
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
    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ScheduleResult(
            blocks=[],
            unscheduled_tasks=unscheduled_tasks,
            solver_run=SolverRun(
                engine="or_tools_cp_sat",
                ortools_available=True,
                status=status_name,
                message=f"OR-Tools CP-SAT completed with status {status_name} and did not produce a usable schedule.",
                diagnostics={
                    "strategy": "or_tools_cp_sat",
                    "task_order": task_order,
                    "task_traces": task_traces,
                    "solve_status": status_name,
                    "max_time_in_seconds": 5,
                },
            ),
        )

    blocks: list[Block] = []
    for candidate in scheduled_candidates:
        task = candidate["task"]
        trace = candidate["trace"]
        if solver.Value(candidate["present_var"]):
            start_slot = solver.Value(candidate["start_var"])
            end_slot = solver.Value(candidate["end_var"])
            trace["decision"] = "scheduled"
            trace["present"] = True
            trace["chosen_window"] = _slot_window_payload(start_slot, int(candidate["duration_slots"]), week_start, workday_window)
            if candidate["on_time_var"] is not None:
                trace["on_time"] = bool(solver.Value(candidate["on_time_var"]))
            blocks.append(
                Block(
                    id=None,
                    user_id=task.user_id,
                    task_id=task.id,
                    event_id=None,
                    starts_at=_slot_to_datetime(start_slot, week_start, workday_window),
                    ends_at=_slot_end_to_datetime(end_slot, week_start, workday_window),
                    location=task.preferred_location,
                    status="planned",
                    lock_level="none",
                    generated_by="solver",
                )
            )
            continue

        trace["decision"] = "unscheduled"
        trace["present"] = False
        trace["reason"] = "no_capacity"
        unscheduled_tasks.append(_make_unscheduled(task, "no_capacity"))

    blocks.sort(key=lambda block: block.starts_at)
    unscheduled_tasks.sort(key=lambda item: (-item.priority, item.title))
    return ScheduleResult(
        blocks=blocks,
        unscheduled_tasks=unscheduled_tasks,
        solver_run=SolverRun(
            engine="or_tools_cp_sat",
            ortools_available=True,
            status=status_name,
            message=f"OR-Tools CP-SAT returned {status_name}, scheduled {len(blocks)} blocks, and left {len(unscheduled_tasks)} tasks unscheduled.",
            objective_value=solver.ObjectiveValue(),
            diagnostics={
                "strategy": "or_tools_cp_sat",
                "task_order": task_order,
                "task_traces": task_traces,
                "solve_status": status_name,
                "max_time_in_seconds": 5,
            },
        ),
    )


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
    resolved_options = options or {}
    week_start = resolved_options.get("week_start")
    if not isinstance(week_start, date):
        raise ValueError("`week_start` must be provided to build_schedule")
    workday_window = resolved_options.get("workday_window")
    if workday_window is None:
        workday_window = resolve_workday_window(
            workday_start=resolved_options.get("workday_start"),
            workday_end=resolved_options.get("workday_end"),
        )
    if not isinstance(workday_window, WorkdayWindow):
        raise ValueError("`workday_window` must be a WorkdayWindow instance when provided")

    if not task_list:
        runtime = get_solver_runtime_status()
        return ScheduleResult(
            blocks=[],
            unscheduled_tasks=[],
            solver_run=SolverRun(
                engine=runtime.engine,
                ortools_available=runtime.ortools_available,
                status="NO_TASKS",
                message="No tasks were available to schedule for this run.",
                diagnostics={
                    "strategy": runtime.engine,
                    "task_order": [],
                    "task_traces": [],
                },
            ),
        )

    cp_sat_result = _build_schedule_cp_sat(task_list, event_list, week_start, workday_window)
    if cp_sat_result is not None:
        return cp_sat_result
    return _build_schedule_greedy(task_list, event_list, week_start, workday_window)
