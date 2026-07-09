from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from web.job_views import build_job_view


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


def test_job_view_building(test_services):
    # Start a design run
    result = test_services.runs.start({
        "user_intent": "Build an AND gate",
        "host_organism": "E. coli",
        "compute_budget": 5,
    })
    run_id = result["run_id"]

    # Build design job view
    job_view = build_job_view(run_id, "design", test_services)
    assert job_view.id == run_id
    assert job_view.kind == "design"
    assert job_view.status in ["queued", "running", "needs_human_input", "completed"]
    assert job_view.progress >= 0.0
    assert not job_view.terminal
    assert job_view.can_cancel
    assert not job_view.can_retry

    # Cancel the run
    test_services.runs.cancel(run_id)
    job_view = build_job_view(run_id, "design", test_services)
    assert job_view.status in ["cancelled", "cancellation_requested"]


def test_web_routes_lifecycle(client, test_services):
    # Start a run
    result = test_services.runs.start({
        "user_intent": "Build an OR gate",
        "host_organism": "E. coli",
        "compute_budget": 5,
    })
    run_id = result["run_id"]

    # 1. Detail page
    response = client.get(f"/web/runs/{run_id}")
    assert response.status_code == 200
    assert b"Design run monitor" in response.content
    assert b"decision-history" in response.content

    # 2. Decision history page
    response = client.get(f"/web/runs/{run_id}/decision-history")
    assert response.status_code == 200
    assert b"AI Search Tree" in response.content

    # 3. Cancel the run
    response = client.post(f"/web/runs/{run_id}/cancel", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith(f"/web/runs/{run_id}")

    # 4. Retry the run
    response = client.post(f"/web/runs/{run_id}/retry", follow_redirects=False)
    assert response.status_code == 303
    assert "/web/runs/run_" in response.headers["location"]
