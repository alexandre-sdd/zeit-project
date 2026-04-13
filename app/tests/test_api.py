from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.base import Base
import app.db.session as db_session
from app.main import app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.sqlite3"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(db_session, "SessionLocal", testing_session_local)

    Base.metadata.create_all(bind=test_engine)
    with testing_session_local() as session:
        session.add(models.User(email="test@example.com"))
        session.commit()

    with TestClient(app) as test_client:
        yield test_client

    test_engine.dispose()


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
