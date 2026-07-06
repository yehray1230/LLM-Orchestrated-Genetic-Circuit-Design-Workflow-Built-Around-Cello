from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from schemas.design_ir_v2 import DesignIRV2, DesignSpecification, BiologicalPartV2


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


def _create_sample_design(design_id: str) -> DesignIRV2:
    return DesignIRV2(
        design_id=design_id,
        name="Test Design",
        specification=DesignSpecification(outputs=["Y"]),
        parts=[
            BiologicalPartV2(
                id="part_1",
                name="Part 1",
                part_type="CDS",
                role="reporter",
                sequence="ATGAAATAA",
                evidence_level="experimentally_characterized",
            )
        ],
        interactions=[],
        constructs=[],
    )


def test_revisions_comparison_logic(test_services):
    design_id = "rev_test_1"
    design_v2 = _create_sample_design(design_id)
    
    # Save first revision
    test_services.designs.save_v2(design_v2)
    
    # Add a part for revision 2
    design_v2.parts.append(
        BiologicalPartV2(
            id="part_2",
            name="Part 2",
            part_type="terminator",
            role="termination",
            sequence="GCCGCC",
            evidence_level="literature_supported",
        )
    )
    test_services.designs.save_v2(design_v2)

    # 1. Verify revision count
    revisions = test_services.designs.revisions(design_id)
    assert len(revisions) == 2
    assert revisions[0]["revision_number"] == 2
    assert revisions[1]["revision_number"] == 1

    # 2. Compare revisions
    diff = test_services.comparisons.compare_revisions(design_id, 1, 2)
    assert diff["left_design_id"] == design_id
    assert len(diff["part_changes"]) == 1
    assert diff["part_changes"][0]["part_id"] == "part_2"
    assert diff["part_changes"][0]["change_type"] == "added"


def test_revisions_api_endpoints(client, test_services):
    design_id = "rev_api_test"
    design_v2 = _create_sample_design(design_id)
    
    # Save first revision
    test_services.designs.save_v2(design_v2)
    
    # Add a part for revision 2
    design_v2.parts.append(
        BiologicalPartV2(
            id="part_2",
            name="Part 2",
            part_type="terminator",
            role="termination",
            sequence="GCCGCC",
            evidence_level="literature_supported",
        )
    )
    test_services.designs.save_v2(design_v2)

    # GET revisions compare
    response = client.get(f"/api/v1/designs/{design_id}/revisions/compare?left=1&right=2")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["left_design_id"] == design_id
    assert len(data["part_changes"]) == 1
    assert data["part_changes"][0]["part_id"] == "part_2"
    assert data["part_changes"][0]["change_type"] == "added"


def test_revisions_web_history_snapshot(client, test_services):
    design_id = "rev_web_test"
    design_v2 = _create_sample_design(design_id)
    
    test_services.designs.save_v2(design_v2)

    # GET default web design detail (latest)
    response = client.get(f"/web/designs/{design_id}")
    assert response.status_code == 200
    assert "正在查看版本" not in response.text

    # GET historical revision web snapshot
    response = client.get(f"/web/designs/{design_id}?rev=1")
    assert response.status_code == 200
    assert "正在查看版本" in response.text
    assert "Rev 1" in response.text
