from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_page_renders_seeded_demo(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Visitor Demo" in response.text
    assert "Build timeline demo" in response.text
    assert "Generate Schedule" in response.text
    assert "Download ICS" in response.text
    assert "Optimisation calendar" in response.text
    assert "Allocated time by priority level" in response.text
    assert "Solver status and recent runs" in response.text
    assert "Working Window" in response.text
    assert 'id="workday-start"' in response.text
    assert 'id="workday-end"' in response.text
    assert "Urgent" in response.text
    assert "Important" in response.text
    assert "When possible" in response.text
    assert "Next steps" in response.text
    assert "Google Calendar, Slack" in response.text
    assert "cannot break tasks into smaller blocks" in response.text
    assert "Remove" in response.text


def test_root_page_shows_planned_blocks_after_schedule_run(client: TestClient) -> None:
    reset_payload = client.post("/demo/reset", json={}).json()
    client.post(
        "/schedule/generate",
        json={
            "user_id": reset_payload["user_id"],
            "week_start": reset_payload["week_start"],
        },
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "Task placements" in response.text
    assert "planned blocks are already layered onto the weekly calendar" in response.text
    assert "Run #" in response.text


def test_root_page_does_not_reseed_after_all_tasks_are_deleted(client: TestClient) -> None:
    reset_payload = client.post("/demo/reset", json={}).json()
    tasks = client.get("/tasks", params={"user_id": reset_payload["user_id"]}).json()
    for task in tasks:
        delete_response = client.delete(f"/tasks/{task['id']}")
        assert delete_response.status_code == 204

    response = client.get("/")

    assert response.status_code == 200
    assert "Build timeline demo" not in response.text
    assert "Weekly Standup" in response.text


def test_root_page_does_not_reseed_after_all_events_are_deleted(client: TestClient) -> None:
    reset_payload = client.post("/demo/reset", json={}).json()
    events = client.get("/events", params={"user_id": reset_payload["user_id"]}).json()
    for event in events:
        delete_response = client.delete(f"/events/{event['id']}")
        assert delete_response.status_code == 204

    response = client.get("/")

    assert response.status_code == 200
    assert "Weekly Standup" not in response.text
    assert "Build timeline demo" in response.text
