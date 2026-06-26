from __future__ import annotations

from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from mcp_server.service import list_tool_capabilities
from tools.tool_adapters import CAPABILITY_LOGIC_SYNTHESIS, CAPABILITY_ODE_SIMULATION


def test_api_exposes_tool_capability_status(tmp_path) -> None:
    services = create_application_services(tmp_path / "api_data")
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/tool-capabilities")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert CAPABILITY_LOGIC_SYNTHESIS in payload["data"]["catalog"]
    assert CAPABILITY_ODE_SIMULATION in payload["data"]["capabilities"]
    assert payload["data"]["tools"]
    assert any(
        tool["tool_name"] == "cello" and tool["status"] == "fallback"
        for tool in payload["data"]["tools"]
    )


def test_mcp_service_exposes_tool_capability_status() -> None:
    result = list_tool_capabilities()

    assert result["status"] == "completed"
    assert result["summary"]["tool_count"] >= 2
    assert CAPABILITY_LOGIC_SYNTHESIS in result["catalog"]
    assert CAPABILITY_ODE_SIMULATION in result["capabilities"]
