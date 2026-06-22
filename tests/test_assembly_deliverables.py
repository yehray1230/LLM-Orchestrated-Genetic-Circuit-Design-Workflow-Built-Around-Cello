from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from tests.test_assembly_planner import _services
from tools.primer_designer import design_assembly_primers


def _request() -> dict[str, object]:
    return {
        "plasmid_id": "plasmid_1",
        "backbone_id": "planner_backbone",
        "backbone_version": "1.0.0",
        "insertion_region_id": "mcs",
        "insertion_start": 100,
        "insertion_end": 120,
        "method": "gibson",
        "restriction_enzymes": ["EcoRI", "BsaI", "BsmBI"],
        "gibson_overlap_length": 20,
        "golden_gate_enzyme": "BsaI",
        "golden_gate_overhangs": None,
    }


def test_primer_design_uses_adapters_and_marks_short_fragments_for_synthesis(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)
    planned = services.assembly_plans.plan("planner_design", **_request())

    result = design_assembly_primers(planned["plan"]).to_dict()

    assert result["status"] == "ready"
    by_id = {
        item["fragment_id"]: item
        for item in result["fragment_primer_sets"]
    }
    backbone = by_id["backbone_fragment"]
    insert = by_id["insert_fragment"]
    assert backbone["preparation"] == "pcr"
    assert backbone["forward_primer"]["sequence"].startswith(
        planned["plan"]["fragments"][0]["left_adapter"]
    )
    assert 57 <= backbone["forward_primer"]["tm"] <= 63
    assert insert["preparation"] == "direct_synthesis"
    assert insert["forward_primer"] is None
    assert insert["warnings"][0]["code"] == "DIRECT_SYNTHESIS_RECOMMENDED"


def test_deliverable_service_writes_complete_package(tmp_path: Path) -> None:
    services = _services(tmp_path)

    result = services.assembly_deliverables.create(
        "planner_design",
        **_request(),
    )

    assert result["ok"] is True
    assert result["readiness"]["readiness_status"] == "primer_ready"
    assert {"genbank", "csv", "json", "report", "opentrons", "echo"}.issubset(result["artifacts"])
    for key in ("genbank", "csv", "json", "report", "opentrons", "echo"):
        artifact = services.assembly_deliverables.artifact(
            result["deliverable_id"],
            key,
        )
        assert artifact is not None
        assert artifact[0].is_file()
        
    opentrons_artifact = services.assembly_deliverables.artifact(
        result["deliverable_id"],
        "opentrons",
    )
    assert "opentrons" in opentrons_artifact[0].read_text("utf-8")
    
    echo_artifact = services.assembly_deliverables.artifact(
        result["deliverable_id"],
        "echo",
    )
    assert "Source Plate Name" in echo_artifact[0].read_text("utf-8")
    csv_artifact = services.assembly_deliverables.artifact(
        result["deliverable_id"],
        "csv",
    )
    assert csv_artifact is not None
    rows = list(csv.DictReader(StringIO(csv_artifact[0].read_text("utf-8"))))
    assert {row["preparation"] for row in rows} == {"pcr", "direct_synthesis"}
    json_artifact = services.assembly_deliverables.artifact(
        result["deliverable_id"],
        "json",
    )
    assert json_artifact is not None
    package = json.loads(json_artifact[0].read_text("utf-8"))
    assert package["plan"]["method"] == "gibson"
    assert package["primers"]["status"] == "ready"


def test_deliverable_api_and_artifact_download(tmp_path: Path) -> None:
    services = _services(tmp_path)
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v2/designs/planner_design/assembly-deliverables",
                json=_request(),
            )
            assert response.status_code == 200
            result = response.json()["data"]
            download = client.get(
                "/api/v2/assembly-deliverables/"
                f"{result['deliverable_id']}/artifacts/csv"
            )
    finally:
        app.dependency_overrides.clear()

    assert download.status_code == 200
    assert "fragment_id" in download.text
    assert "text/csv" in download.headers["content-type"]


def test_html_assembly_workspace_renders_report_and_downloads(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)
    result = services.assembly_deliverables.create(
        "planner_design",
        **_request(),
    )
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            legacy = client.get(
                "/web/assembly",
                params={"deliverable_id": result["deliverable_id"]},
                follow_redirects=False,
            )
            page = client.get(
                f"/web/assembly/deliverables/{result['deliverable_id']}",
            )
            downloads = client.get(
                "/web/assembly/deliverables/"
                f"{result['deliverable_id']}/downloads",
            )
            download = client.get(
                "/web/assembly/deliverables/"
                f"{result['deliverable_id']}/artifacts/genbank"
            )
    finally:
        app.dependency_overrides.clear()

    assert legacy.status_code == 303
    assert legacy.headers["location"] == (
        f"/web/assembly/deliverables/{result['deliverable_id']}"
    )
    assert page.status_code == 200
    assert "Assembly report" in page.text
    assert "Fragment and primer table" in page.text
    assert result["deliverable_id"] in page.text
    assert downloads.status_code == 200
    assert "Download deliverables" in downloads.text
    assert download.status_code == 200
    assert "LOCUS" in download.text
