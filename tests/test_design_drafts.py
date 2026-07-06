from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services


@pytest.fixture
def test_services(tmp_path: Path):
    services = create_application_services(tmp_path / "api_data")
    return services


@pytest.fixture
def client(test_services):
    app.state.test_services = test_services
    app.dependency_overrides[get_services] = lambda: test_services
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_design_draft_service_load_save_clear(test_services):
    service = test_services.design_drafts
    
    # 1. No active draft initially
    assert service.get_active() is None

    # 2. Save active draft
    payload = {
        "current_step": 2,
        "user_intent": "Make a toggle switch",
        "host_organism": "E. coli",
        "compute_budget": 12,
        "enable_rag": True,
        "enable_ode": False,
        "enable_skill_extraction": True,
        "model_name": "custom-gpt",
        "api_base": "http://custom"
    }
    saved = service.save(payload)
    assert saved["current_step"] == 2
    assert saved["user_intent"] == "Make a toggle switch"
    assert saved["host_organism"] == "E. coli"
    assert saved["compute_budget"] == 12
    assert saved["enable_rag"] is True
    assert saved["enable_ode"] is False
    assert saved["model_name"] == "custom-gpt"
    assert saved["api_base"] == "http://custom"
    assert "last_saved" in saved
    assert "draft_id" in saved

    # 3. Retrieve draft
    active = service.get_active()
    assert active is not None
    assert active["draft_id"] == saved["draft_id"]
    assert active["user_intent"] == "Make a toggle switch"

    # 4. Save updates (preserves draft_id)
    updated = service.save({
        "current_step": 3,
        "user_intent": "Updated Intent"
    })
    assert updated["draft_id"] == saved["draft_id"]
    assert updated["current_step"] == 3
    assert updated["user_intent"] == "Updated Intent"
    assert updated["host_organism"] == "E. coli"  # Preserved!

    # 5. Clear draft
    service.clear()
    assert service.get_active() is None


def test_design_draft_api_endpoints(client):
    # 1. GET active (empty)
    response = client.get("/api/v1/designs/drafts/active")
    assert response.status_code == 200
    assert response.json()["data"] is None

    # 2. POST save
    payload = {
        "current_step": 1,
        "user_intent": "Build an oscillator"
    }
    response = client.post("/api/v1/designs/drafts", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_intent"] == "Build an oscillator"
    assert data["current_step"] == 1

    # 3. GET active (exists)
    response = client.get("/api/v1/designs/drafts/active")
    assert response.status_code == 200
    assert response.json()["data"]["user_intent"] == "Build an oscillator"

    # 4. DELETE active
    response = client.delete("/api/v1/designs/drafts/active")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cleared"

    # 5. GET active (empty again)
    response = client.get("/api/v1/designs/drafts/active")
    assert response.status_code == 200
    assert response.json()["data"] is None


def test_design_draft_cleared_on_run_start(client, test_services):
    # Save draft
    test_services.design_drafts.save({
        "user_intent": "Draft Intent",
        "current_step": 4
    })
    assert test_services.design_drafts.get_active() is not None

    # Simulate successful run start via /web/runs
    with patch("application.services.start_design_run") as mock_start:
        mock_start.return_value = {"run_id": "run_wizard_test", "status": "queued"}
        
        response = client.post(
            "/web/runs",
            data={
                "user_intent": "Form Intent",
                "host_organism": "E. coli",
                "compute_budget": 6,
                "model_name": "",
                "enable_rag": "on",
                "enable_ode": "on"
            },
            follow_redirects=False
        )
        assert response.status_code == 303  # Redirects
        # Draft should be cleared!
        assert test_services.design_drafts.get_active() is None
