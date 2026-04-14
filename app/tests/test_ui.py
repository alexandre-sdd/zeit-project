from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_page_renders_seeded_demo(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Recruiter Demo" in response.text
    assert "Build timeline demo" in response.text
    assert "Generate Schedule" in response.text
    assert "Optimisation calendar" in response.text
    assert "Allocated time by priority" in response.text
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
