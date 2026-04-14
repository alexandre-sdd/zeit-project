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
            "title": "Prepare visitor walkthrough",
            "est_duration_min": 45,
            "priority": 2,
        },
    )

    assert create_response.status_code == 201
    created_task = create_response.json()
    assert created_task["title"] == "Prepare visitor walkthrough"
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


def test_delete_task_removes_it_from_task_list(client: TestClient) -> None:
    created_task = client.post(
        "/tasks",
        json={
            "user_id": 1,
            "title": "Delete me",
            "est_duration_min": 60,
            "priority": 2,
        },
    ).json()

    delete_response = client.delete(f"/tasks/{created_task['id']}")
    assert delete_response.status_code == 204

    list_response = client.get("/tasks", params={"user_id": 1})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_task_form_route_removes_task_and_redirects(client: TestClient) -> None:
    created_task = client.post(
        "/tasks",
        json={
            "user_id": 1,
            "title": "Delete me with form",
            "est_duration_min": 60,
            "priority": 2,
        },
    ).json()

    delete_response = client.post(f"/tasks/{created_task['id']}/delete", follow_redirects=False)
    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/"

    list_response = client.get("/tasks", params={"user_id": 1})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_task_link_route_removes_task_and_redirects(client: TestClient) -> None:
    created_task = client.post(
        "/tasks",
        json={
            "user_id": 1,
            "title": "Delete me with link",
            "est_duration_min": 60,
            "priority": 2,
        },
    ).json()

    delete_response = client.get(f"/tasks/{created_task['id']}/remove", follow_redirects=False)
    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/"

    list_response = client.get("/tasks", params={"user_id": 1})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_event_removes_it_from_event_list(client: TestClient) -> None:
    created_event = client.post(
        "/events",
        json={
            "user_id": 1,
            "title": "Delete this event",
            "starts_at": "2026-04-13T11:00:00",
            "ends_at": "2026-04-13T12:00:00",
            "location": "Studio",
        },
    ).json()

    delete_response = client.delete(f"/events/{created_event['id']}")
    assert delete_response.status_code == 204

    list_response = client.get("/events", params={"user_id": 1})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_event_link_route_removes_event_and_redirects(client: TestClient) -> None:
    created_event = client.post(
        "/events",
        json={
            "user_id": 1,
            "title": "Delete this event with link",
            "starts_at": "2026-04-13T11:00:00",
            "ends_at": "2026-04-13T12:00:00",
            "location": "Studio",
        },
    ).json()

    delete_response = client.get(f"/events/{created_event['id']}/remove", follow_redirects=False)
    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/"

    list_response = client.get("/events", params={"user_id": 1})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_event_form_route_removes_event_and_redirects(client: TestClient) -> None:
    created_event = client.post(
        "/events",
        json={
            "user_id": 1,
            "title": "Delete this event with form",
            "starts_at": "2026-04-13T11:00:00",
            "ends_at": "2026-04-13T12:00:00",
            "location": "Studio",
        },
    ).json()

    delete_response = client.post(f"/events/{created_event['id']}/delete", follow_redirects=False)
    assert delete_response.status_code == 303
    assert delete_response.headers["location"] == "/"

    list_response = client.get("/events", params={"user_id": 1})
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_delete_task_also_removes_linked_scheduled_blocks(client: TestClient) -> None:
    reset_payload = client.post("/demo/reset", json={}).json()
    schedule_payload = client.post(
        "/schedule/generate",
        json={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
        },
    ).json()
    scheduled_task_id = schedule_payload["blocks"][0]["task_id"]

    delete_response = client.delete(f"/tasks/{scheduled_task_id}")
    assert delete_response.status_code == 204

    blocks_response = client.get(
        "/blocks",
        params={"user_id": reset_payload["user_id"], "week_start": reset_payload["week_start"]},
    )
    assert blocks_response.status_code == 200
    assert all(block["task_id"] != scheduled_task_id for block in blocks_response.json())


def test_calendar_export_returns_ics_with_events_and_blocks(client: TestClient) -> None:
    reset_payload = client.post("/demo/reset", json={}).json()
    schedule_payload = client.post(
        "/schedule/generate",
        json={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
        },
    ).json()

    export_response = client.get(
        "/calendar/export.ics",
        params={"user_id": reset_payload["user_id"], "week_start": reset_payload["week_start"]},
    )

    assert export_response.status_code == 200
    assert "text/calendar" in export_response.headers["content-type"]
    assert "attachment;" in export_response.headers["content-disposition"]
    assert "Weekly Standup" in export_response.text
    assert schedule_payload["blocks"][0]["task_title"] in export_response.text


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
    assert first_payload["solver_run"]["engine"] in {"or_tools_cp_sat", "greedy_fallback"}
    assert first_payload["solver_run"]["status"]
    assert first_payload["solver_run"]["message"]
    assert first_payload["solver_run"]["diagnostics"]["task_order"]
    assert first_payload["solver_run"]["diagnostics"]["task_traces"]
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


def test_schedule_generation_persists_run_log(client: TestClient) -> None:
    reset_payload = client.post("/demo/reset", json={}).json()

    generate_response = client.post(
        "/schedule/generate",
        json={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
            "workday_start": "09:00",
            "workday_end": "21:00",
        },
    )

    assert generate_response.status_code == 200
    logs_response = client.get(
        "/schedule/runs",
        params={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
            "limit": 5,
        },
    )

    assert logs_response.status_code == 200
    payload = logs_response.json()
    assert len(payload) == 1
    latest_log = payload[0]
    assert latest_log["constraints"]["workday_start"] == "09:00:00"
    assert latest_log["constraints"]["workday_end"] == "21:00:00"
    assert len(latest_log["tasks_to_plan"]) > 0
    assert latest_log["solver"]["engine"] in {"or_tools_cp_sat", "greedy_fallback"}
    assert latest_log["solver"]["diagnostics"]["task_order"]
    assert latest_log["solver"]["diagnostics"]["task_traces"]
    assert latest_log["solution"]["scheduled_count"] == latest_log["scheduled_count"]
    assert latest_log["solution"]["unscheduled_count"] == latest_log["unscheduled_count"]
    assert len(latest_log["planned_tasks"]) == latest_log["scheduled_count"]
    assert len(latest_log["unplanned_tasks"]) == latest_log["unscheduled_count"]


def test_schedule_generation_accepts_custom_workday_window(client: TestClient) -> None:
    task_response = client.post(
        "/tasks",
        json={
            "user_id": 1,
            "title": "Morning focus",
            "est_duration_min": 240,
            "priority": 4,
        },
    )
    assert task_response.status_code == 201

    response = client.post(
        "/schedule/generate",
        json={
            "user_id": 1,
            "week_start": "2026-04-13",
            "workday_start": "08:00",
            "workday_end": "12:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduled_count"] == 1
    assert payload["blocks"][0]["starts_at"] == "2026-04-13T08:00:00"
    assert payload["blocks"][0]["ends_at"] == "2026-04-13T12:00:00"


def test_schedule_generation_rejects_invalid_workday_window(client: TestClient) -> None:
    response = client.post(
        "/schedule/generate",
        json={
            "user_id": 1,
            "week_start": "2026-04-13",
            "workday_start": "08:15",
            "workday_end": "12:00",
        },
    )

    assert response.status_code == 422
