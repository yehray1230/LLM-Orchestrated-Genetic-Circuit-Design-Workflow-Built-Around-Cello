from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from schemas.state import DesignState


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


def test_elicitation_endpoints_flow(client, test_services):
    # 1. Initialize an active draft
    test_services.design_drafts.save({
        "current_step": 1,
        "user_intent": "Build an oscillator circuit"
    })

    # Mock call_pm_agent
    mock_state = DesignState(
        user_intent="Build an oscillator circuit",
        structured_spec={},
        pm_chat_history=[
            {"role": "assistant", "content": "Hello, what chassis do you want?"}
        ],
        pending_proposal={
            "missing_field": "chassis",
            "proposed_value": "Escherichia coli",
            "description": "Recommended host chassis organism"
        },
        pm_stage="elicitation"
    )

    with patch("agents.pm_agent.call_pm_agent", return_value=mock_state):
        # 2. Call elicitation/next
        response = client.post("/api/v1/designs/drafts/elicitation/next")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["pending_proposal"]["missing_field"] == "chassis"
        assert len(data["pm_chat_history"]) == 1

        # 3. Call elicitation/propose (agree)
        # We mock next call_pm_agent return value to ask for next field: inputs
        next_mock_state = DesignState(
            user_intent="Build an oscillator circuit",
            structured_spec={"chassis": "Escherichia coli"},
            pm_chat_history=[
                {"role": "assistant", "content": "Hello, what chassis do you want?"},
                {"role": "user", "content": "同意使用推薦值：\"Escherichia coli\""},
                {"role": "assistant", "content": "已儲存 chassis 設定。"},
                {"role": "assistant", "content": "What inputs do you need?"}
            ],
            pending_proposal={
                "missing_field": "inputs",
                "proposed_value": [{"name": "IPTG", "sensor_promoter": "pLac", "type": "input_sensor"}],
                "description": "Recommended inputs"
            },
            pm_stage="elicitation"
        )

        with patch("agents.pm_agent.call_pm_agent", return_value=next_mock_state):
            response = client.post("/api/v1/designs/drafts/elicitation/propose", json={
                "choice": "agree"
            })
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["structured_spec"]["chassis"] == "Escherichia coli"
            assert data["pending_proposal"]["missing_field"] == "inputs"
            assert len(data["pm_chat_history"]) == 4

        # 4. Call elicitation/propose (override)
        # We mock next call_pm_agent return value to finish
        final_mock_state = DesignState(
            user_intent="Build an oscillator circuit",
            structured_spec={
                "chassis": "Escherichia coli",
                "inputs": [{"name": "aTc", "sensor_promoter": "pTet", "type": "input_sensor"}]
            },
            pm_chat_history=[
                *next_mock_state.pm_chat_history,
                {"role": "user", "content": "我想要改為：[{\"name\": \"aTc\", \"sensor_promoter\": \"pTet\", \"type\": \"input_sensor\"}]"},
                {"role": "assistant", "content": "已自訂 inputs 為: ..."}
            ],
            pending_proposal={},
            pm_stage="completed"
        )

        with patch("agents.pm_agent.call_pm_agent", return_value=final_mock_state):
            response = client.post("/api/v1/designs/drafts/elicitation/propose", json={
                "choice": "override",
                "value": '[{"name": "aTc", "sensor_promoter": "pTet", "type": "input_sensor"}]'
            })
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["structured_spec"]["inputs"][0]["name"] == "aTc"
            assert data["pm_stage"] == "completed"

    # 5. Call elicitation/skip (reset draft first)
    test_services.design_drafts.clear()
    test_services.design_drafts.save({
        "current_step": 1,
        "user_intent": "Build an oscillator circuit"
    })

    response = client.post("/api/v1/designs/drafts/elicitation/skip")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["structured_spec"]["chassis"] == "Escherichia coli"
    assert data["structured_spec"]["copy_number"] == 15
    assert data["pm_stage"] == "completed"
    assert data["pending_proposal"] == {}
