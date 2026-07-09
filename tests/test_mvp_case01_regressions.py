from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.dependencies as api_dependencies
from api.dependencies import get_services
from api.main import app
from application.services import create_application_services


@pytest.fixture
def client(tmp_path: Path):
    services = create_application_services(tmp_path / "api_data")
    app.state.test_services = services
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_skip_elicitation_only_applies_safe_defaults(client: TestClient) -> None:
    services = client.app.state.test_services
    services.design_drafts.save(
        {
            "current_step": 1,
            "user_intent": "Build a circuit where GFP = A AND NOT B",
        }
    )

    response = client.post("/api/v1/designs/drafts/elicitation/skip")

    assert response.status_code == 200
    data = response.json()["data"]
    structured_spec = data["structured_spec"]
    assert structured_spec["chassis"] == "Escherichia coli"
    assert structured_spec["copy_number"] == 15
    assert "inputs" not in structured_spec
    assert "outputs" not in structured_spec
    assert "logic_relation" not in structured_spec


def test_dashboard_status_bar_accepts_run_id_only_jobs(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    services = client.app.state.test_services
    monkeypatch.setattr(api_dependencies, "get_services", lambda: services)
    monkeypatch.setattr(
        services.runs,
        "list",
        lambda limit=100: {
            "runs": [
                {
                    "run_id": "run_bg_only",
                    "kind": "design",
                    "status": "queued",
                    "stage": "planner",
                    "progress": 0.2,
                }
            ]
        },
    )

    response = client.get("/web")

    assert response.status_code == 200
    assert "/web/runs/run_bg_only" in response.text
    assert "run_bg_o" in response.text
