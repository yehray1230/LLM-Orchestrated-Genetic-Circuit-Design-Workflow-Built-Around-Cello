from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from repositories.json_repository import JsonRepository, RepositoryError
from schemas.import_draft import ImportDraft


def _draft_payload(draft_id: str = "external_design_1") -> dict:
    return {
        "draft_id": draft_id,
        "name": f"External design {draft_id}",
        "source_type": "literature",
        "source_uri": "https://doi.org/10.0000/example",
        "citation": "Example et al.",
        "host_organism": "Escherichia coli",
        "inputs": ["A", "B"],
        "outputs": ["GFP"],
        "logic_expression": "GFP = A AND NOT B",
        "validation_status": "experimentally_validated",
        "validation_notes": "Reported in the source publication.",
        "parts": [
            {
                "id": "promoter_a",
                "name": "Promoter A",
                "part_type": "promoter",
                "role": "Input promoter",
                "sequence": "AAAAAA",
                "host_compatibility": ["Escherichia coli"],
                "evidence": {
                    "field_path": "parts.promoter_a",
                    "status": "explicit",
                    "locator": "Figure 1",
                },
            },
            {
                "id": "gfp",
                "name": "GFP",
                "part_type": "CDS",
                "role": "Reporter",
                "sequence": "ATGAAATAA",
                "host_compatibility": ["Escherichia coli"],
                "evidence": {
                    "field_path": "parts.gfp",
                    "status": "explicit",
                    "locator": "Methods",
                },
            },
        ],
        "interactions": [
            {
                "source": "promoter_a",
                "target": "gfp",
                "interaction_type": "expression",
                "label": "Promoter drives GFP",
            }
        ],
        "evidence": [
            {
                "field_path": "design_summary",
                "status": "explicit",
                "locator": "Figure 1",
            }
        ],
        "notes": "",
        "created_at": "2026-06-14T00:00:00+00:00",
        "schema_version": "1.0",
    }


@pytest.fixture
def client(tmp_path: Path):
    services = create_application_services(tmp_path / "api_data")
    app.state.test_services = services
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_json_repository_writes_and_rejects_path_traversal(tmp_path: Path) -> None:
    repository = JsonRepository(tmp_path / "records")

    repository.save("design_1", {"design_id": "design_1"})

    assert repository.get("design_1") == {"design_id": "design_1"}
    assert not list((tmp_path / "records").glob("*.tmp"))
    with pytest.raises(RepositoryError):
        repository.get("../outside")


def test_import_service_persists_draft_and_confirmed_design(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    draft = services.imports.import_json(_draft_payload())

    design = services.imports.confirm_by_id(draft.draft_id)

    assert services.imports.get_draft(draft.draft_id) is not None
    assert services.designs.get(design.design_id) is not None
    assert design.validation_status["experimental_validation"] == (
        "experimentally_validated"
    )


def test_health_and_openapi_are_available(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
    assert client.get("/openapi.json").status_code == 200


def test_validate_import_confirm_and_list_design(client: TestClient) -> None:
    payload = _draft_payload()

    validation = client.post("/api/v1/imports/drafts/validate", json=payload)
    imported = client.post("/api/v1/imports/json", json={"draft": payload})
    confirmed = client.post(
        f"/api/v1/imports/{payload['draft_id']}/confirm"
    )
    listed = client.get("/api/v1/designs")
    fetched = client.get(f"/api/v1/designs/{payload['draft_id']}")

    assert validation.status_code == 200
    assert validation.json()["data"]["can_import"] is True
    assert imported.status_code == 201
    assert confirmed.status_code == 201
    assert confirmed.json()["data"]["design_id"] == payload["draft_id"]
    assert listed.json()["data"]["count"] == 1
    assert fetched.json()["data"]["name"] == payload["name"]


def test_genbank_import_creates_reviewable_incomplete_draft(
    client: TestClient,
) -> None:
    content = """LOCUS       API_TEST                 18 bp    DNA
SOURCE      synthetic construct
  ORGANISM  Escherichia coli
FEATURES             Location/Qualifiers
     promoter        1..6
                     /label="pTest"
     CDS             7..15
                     /gene="gfp"
ORIGIN
        1 aaaaaaatgaaataaacc
//
"""
    response = client.post(
        "/api/v1/imports/genbank",
        json={"filename": "api_test.gb", "content": content},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["draft"]["parts"][0]["name"] == "pTest"
    assert data["validation"]["can_import"] is False
    assert "inputs" in data["validation"]["missing_fields"]


def test_comparison_evaluation_and_bom_export(client: TestClient) -> None:
    for draft_id in ("design_a", "design_b"):
        payload = _draft_payload(draft_id)
        assert client.post(
            "/api/v1/imports/json",
            json={"draft": payload},
        ).status_code == 201
        assert client.post(
            f"/api/v1/imports/{draft_id}/confirm"
        ).status_code == 201

    comparison = client.post(
        "/api/v1/comparisons",
        json={
            "left_design_id": "design_a",
            "right_design_id": "design_b",
            "left_metrics": {"score": 0.6},
            "right_metrics": {"score": 0.8},
        },
    )
    evaluation = client.post(
        "/api/v1/evaluations",
        json={"candidate": {"verilog": "assign Y = A;", "gate_count": 1}},
    )
    export = client.get("/api/v1/designs/design_a/exports/bom")

    assert comparison.status_code == 200
    assert comparison.json()["data"]["metric_changes"][0]["delta"] == pytest.approx(
        0.2
    )
    assert evaluation.status_code == 200
    assert "weighted_total_score" in evaluation.json()["data"]
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv")
    assert "design_id" in export.text


def test_api_rejects_invalid_ids_and_unknown_resources(client: TestClient) -> None:
    invalid = client.get("/api/v1/designs/..%2Foutside")
    missing = client.get("/api/v1/designs/missing_design")

    assert invalid.status_code in {400, 404}
    assert missing.status_code == 404


def test_export_blocks_incomplete_genbank(client: TestClient) -> None:
    draft = ImportDraft.empty()
    payload = _draft_payload("incomplete_export")
    payload["parts"][1]["sequence"] = None
    assert client.post(
        "/api/v1/imports/json",
        json={"draft": payload},
    ).status_code == 201
    assert client.post(
        "/api/v1/imports/incomplete_export/confirm"
    ).status_code == 201

    response = client.get(
        "/api/v1/designs/incomplete_export/exports/genbank"
    )

    assert draft.draft_id.startswith("external_")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXPORT_BLOCKED"


def test_request_validation_uses_stable_error_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/imports/genbank",
        json={"filename": "empty.gb", "content": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"


def test_run_api_contract_without_executing_llm(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    services = client.app.state.test_services
    monkeypatch.setattr(
        services.runs,
        "start",
        lambda request: {
            "run_id": "run_api_test",
            "status": "queued",
            "progress": 0.0,
            "request_model": request.get("model_name"),
        },
    )
    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "running",
            "stage": "builder",
            "progress": 0.25,
        },
    )
    monkeypatch.setattr(
        services.runs,
        "events",
        lambda run_id, after_event_id=0, limit=100: {
            "run_id": run_id,
            "status": "running",
            "events": [
                {
                    "event_id": 1,
                    "stage": "builder",
                    "status": "running",
                    "progress": 0.25,
                    "message": "Generating logic proposals.",
                }
            ],
        },
    )

    started = client.post(
        "/api/v1/runs",
        json={
            "user_intent": "Express GFP when A is present.",
            "model_name": "test-model",
        },
    )
    status_response = client.get("/api/v1/runs/run_api_test")
    events = client.get("/api/v1/runs/run_api_test/events")

    assert started.status_code == 202
    assert started.json()["data"]["run_id"] == "run_api_test"
    assert status_response.json()["data"]["progress"] == 0.25
    assert events.json()["data"]["events"][0]["stage"] == "builder"


def test_run_api_rejects_path_traversal_ids(client: TestClient) -> None:
    response = client.get("/api/v1/runs/..%2Foutside")

    assert response.status_code in {400, 404}


def test_run_service_does_not_forward_browser_api_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_start_design_run(**kwargs):
        captured.update(kwargs)
        return {"run_id": "run_safe", "status": "queued"}

    monkeypatch.setattr(
        "application.services.start_design_run",
        fake_start_design_run,
    )
    services = create_application_services(tmp_path / "api_data")

    result = services.runs.start(
        {
            "user_intent": "Test",
            "api_key": "must-not-be-forwarded",
        }
    )

    assert result["run_id"] == "run_safe"
    assert "api_key" not in captured


def test_server_rendered_web_pages_are_available(client: TestClient) -> None:
    expected = {
        "/web": "研究工作台",
        "/web/new-design": "建立新設計",
        "/web/runs": "設計執行",
        "/web/imports": "外部設計導入",
        "/web/designs": "設計資料庫",
        "/web/compare": "設計比較",
    }
    for path, text in expected.items():
        response = client.get(path)
        assert response.status_code == 200
        assert text in response.text


def test_guided_web_import_review_and_confirm(client: TestClient) -> None:
    created = client.post(
        "/web/imports/guided",
        data={
            "name": "Web imported circuit",
            "source_type": "literature",
            "source_uri": "https://doi.org/10.0000/web",
            "host_organism": "Escherichia coli",
            "inputs": "A, B",
            "outputs": "GFP",
            "logic_expression": "GFP = A AND NOT B",
            "validation_status": "experimentally_validated",
            "evidence_status": "explicit",
        },
        follow_redirects=False,
    )

    assert created.status_code == 303
    review_url = created.headers["location"]
    review = client.get(review_url)
    assert review.status_code == 200
    assert "Web imported circuit" in review.text
    assert "確認並建立 DesignIR" in review.text

    draft_id = review_url.rsplit("/", 1)[-1]
    confirmed = client.post(
        f"/web/imports/{draft_id}/confirm",
        follow_redirects=False,
    )
    assert confirmed.status_code == 303
    detail = client.get(confirmed.headers["location"])
    assert detail.status_code == 200
    assert "Web imported circuit" in detail.text


def test_web_run_form_redirects_to_background_run(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    services = client.app.state.test_services
    monkeypatch.setattr(
        services.runs,
        "start",
        lambda request: {
            "run_id": "run_web_test",
            "status": "queued",
            "progress": 0.0,
        },
    )

    response = client.post(
        "/web/runs",
        data={
            "user_intent": "Express GFP.",
            "host_organism": "Escherichia coli",
            "compute_budget": "3",
            "enable_rag": "on",
            "enable_ode": "on",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/web/runs/run_web_test"
