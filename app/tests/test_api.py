from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient


def test_health_check_returns_app_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app_name"]
    assert payload["environment"] in {"dev", "prod", "test"}


def test_create_and_list_tasks_round_trip(client: TestClient) -> None:
    create_response = client.post(
        "/tasks",
        json={
            "user_id": 1,
            "title": "Prepare recruiter walkthrough",
            "est_duration_min": 45,
            "priority": 2,
        },
    )

    assert create_response.status_code == 201
    created_task = create_response.json()
    assert created_task["title"] == "Prepare recruiter walkthrough"
    assert created_task["priority"] == 2

    list_response = client.get("/tasks", params={"user_id": 1})

    assert list_response.status_code == 200
    assert list_response.json() == [created_task]


def test_create_task_rejects_invalid_payload(client: TestClient) -> None:
    response = client.post(
        "/tasks",
        json={
            "user_id": 0,
            "title": "",
            "est_duration_min": 0,
            "priority": -1,
        },
    )

    assert response.status_code == 422


def test_create_and_list_events_round_trip(client: TestClient) -> None:
    create_response = client.post(
        "/events",
        json={
            "user_id": 1,
            "title": "Planning meeting",
            "starts_at": "2026-04-13T11:00:00",
            "ends_at": "2026-04-13T12:00:00",
            "location": "Studio",
        },
    )

    assert create_response.status_code == 201
    created_event = create_response.json()
    assert created_event["lock_level"] == "hard"

    list_response = client.get("/events", params={"user_id": 1})

    assert list_response.status_code == 200
    assert list_response.json() == [created_event]


def test_demo_reset_and_schedule_generation_replace_prior_blocks(client: TestClient) -> None:
    reset_response = client.post("/demo/reset", json={})
    assert reset_response.status_code == 200
    reset_payload = reset_response.json()

    first_run = client.post(
        "/schedule/generate",
        json={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
        },
    )
    assert first_run.status_code == 200
    first_payload = first_run.json()
    assert first_payload["scheduled_count"] > 0
    assert first_payload["unscheduled_count"] > 0
    assert {item["reason"] for item in first_payload["unscheduled_tasks"]} >= {
        "hard_due_conflict",
        "outside_work_window",
        "no_capacity",
    }

    blocks_response = client.get(
        "/blocks",
        params={"user_id": reset_payload["user_id"], "week_start": reset_payload["week_start"]},
    )
    assert blocks_response.status_code == 200
    blocks_payload = blocks_response.json()
    assert len(blocks_payload) == first_payload["scheduled_count"]

    ordered_times = [
        (
            datetime.fromisoformat(block["starts_at"]),
            datetime.fromisoformat(block["ends_at"]),
        )
        for block in blocks_payload
    ]
    for previous, current in zip(ordered_times, ordered_times[1:]):
        assert previous[1] <= current[0]

    second_run = client.post(
        "/schedule/generate",
        json={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
        },
    )
    assert second_run.status_code == 200
    second_payload = second_run.json()
    assert second_payload["scheduled_count"] == first_payload["scheduled_count"]
