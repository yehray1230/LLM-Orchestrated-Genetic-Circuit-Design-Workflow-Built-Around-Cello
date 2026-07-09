from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from application.notification_service import NotificationService


@pytest.fixture
def test_services(tmp_path: Path):
    services = create_application_services(tmp_path / "api_data")
    return services


@pytest.fixture
def client(test_services):
    app.dependency_overrides[get_services] = lambda: test_services
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_notification_service_flow(tmp_path: Path):
    # Mock RunStore
    mock_run_store = MagicMock()
    mock_run_store.list_runs.return_value = {
        "runs": [
            {
                "run_id": "run_1",
                "status": "completed",
                "updated_at": "2026-07-03T12:00:00Z"
            },
            {
                "run_id": "run_2",
                "status": "running",
                "updated_at": "2026-07-03T12:01:00Z"
            },
            {
                "run_id": "run_3",
                "status": "needs_human_input",
                "updated_at": "2026-07-03T12:02:00Z"
            }
        ]
    }

    read_state_file = tmp_path / "notifications_read_state.json"
    service = NotificationService(mock_run_store, read_state_file)

    # 1. Verify dynamic notifications mapping
    notifications = service.get_notifications()
    assert len(notifications) == 3
    assert notifications[0].notification_id == "run_run_1_completed"
    assert notifications[0].category == "success"
    assert notifications[0].read is False

    assert notifications[1].notification_id == "run_run_2_running"
    assert notifications[1].category == "info"

    assert notifications[2].notification_id == "run_run_3_needs_human_input"
    assert notifications[2].category == "warning"

    assert service.get_unread_count() == 3

    # 2. Mark one notification as read
    service.mark_as_read("run_run_1_completed")
    assert service.get_unread_count() == 2

    # Reload service to check persistence
    service2 = NotificationService(mock_run_store, read_state_file)
    notifs2 = service2.get_notifications()
    assert notifs2[0].read is True
    assert notifs2[1].read is False
    assert service2.get_unread_count() == 2

    # 3. Mark all as read
    service2.mark_all_as_read()
    assert service2.get_unread_count() == 0


def test_notification_api_endpoints(client, test_services):
    # Setup some mock runs in test_services.runs run_store
    # We pass a task that sleeps to keep status stable (e.g. running) during the first steps
    def slow_task():
        time.sleep(2)
        return {"status": "completed"}

    test_services.runs.run_store.start(
        task=slow_task,
        request={"user_intent": "Test Intent"},
        run_id="run_api_test"
    )

    # 1. GET notifications
    response = client.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["unread_count"] >= 1
    assert len(data["notifications"]) >= 1

    # We allow any active status since the background thread runs immediately
    notif_id = data["notifications"][0]["notification_id"]
    assert notif_id.startswith("run_run_api_test_")

    # 2. POST mark notification as read
    response = client.post(f"/api/v1/notifications/{notif_id}/read")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "success"

    # 3. POST mark all as read
    response = client.post("/api/v1/notifications/read-all")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "success"

    # Verify unread count is 0
    response = client.get("/api/v1/notifications")
    assert response.json()["data"]["unread_count"] == 0
