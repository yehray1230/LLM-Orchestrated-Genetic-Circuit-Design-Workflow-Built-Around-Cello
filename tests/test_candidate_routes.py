from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

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


def test_candidates_run_not_found(client: TestClient) -> None:
    # 3. Run not found returns 404
    response = client.get("/web/runs/run_non_existent/candidates")
    assert response.status_code == 404
    assert "Run not found." in response.json()["error"]["message"]


def test_candidates_run_not_completed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # 4. Run not completed displays "not completed" state
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "running",
            "progress": 0.4,
            "summary": {"user_intent": "Test intent"}
        }
    )

    response = client.get("/web/runs/active_run/candidates")
    assert response.status_code == 200
    assert "執行尚未完成" in response.text
    assert "⏳" in response.text


def test_candidates_completed_but_empty(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # 5. Completed but no candidates
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "Test intent"}
        }
    )
    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": []
        }
    )

    response = client.get("/web/runs/empty_run/candidates")
    assert response.status_code == 200
    assert "已完成但沒有候選方案" in response.text
    assert "📂" in response.text


def test_candidates_unparseable_result(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "Test intent"}
        }
    )

    def fail_result(run_id):
        raise ValueError("Invalid JSON format")

    monkeypatch.setattr(services.runs, "result", fail_result)

    response = client.get("/web/runs/broken_run/candidates")
    assert response.status_code == 200
    assert "執行結果無法解析" in response.text
    assert "⚠️" in response.text


def test_candidates_all_failed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # 6. Cello mapping failure
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "Test intent"}
        }
    )
    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": [
                {
                    "score": 0.0,
                    "mapping_status": "MAPPING_FAILED",
                    "verilog": "module dummy; endmodule",
                    "cello_mode": "external",
                    "cello_claim_level": "external_mapping_failed"
                }
            ]
        }
    )

    response = client.get("/web/runs/failed_mapping_run/candidates")
    assert response.status_code == 200
    assert "所有候選方案均映射失敗" in response.text
    assert "❌" in response.text


def test_candidates_list_and_details_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Completed and has multiple candidates, correctly marks best
    # 7. No ODE trace / disabled simulation
    # 8. fallback/provisional warnings
    # 10. Same scores in detail and list
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "running" if run_id == "active_run" else "completed",
            "progress": 0.4 if run_id == "active_run" else 1.0,
            "summary": {
                "user_intent": "Express YFP in E. coli",
                "host_organism": "Escherichia coli",
                "tool_versions": {"Cello": "2.1", "ODE_Solver": "1.2"}
            }
        }
    )

    mock_topologies = [
        {
            "score": 0.88,
            "functional_score": 0.95,
            "kinetic_score": 0.72,
            "metabolic_burden_score": 0.90,
            "mapping_status": "mapped",
            "verilog_index": 0,
            "verilog": "module g(input A, output Y); assign Y = ~A; endmodule",
            "cello_mode": "mock",
            "cello_claim_level": "mock_only",
            "ode_status": "disabled",
            "part_assignments": [
                {"logic_node_id": "gate_1", "part_id": "DEMO_PhlF_CDS", "part_type": "CDS"}
            ]
        },
        {
            "score": 0.94,  # Best
            "functional_score": 0.98,
            "kinetic_score": 0.92,
            "metabolic_burden_score": 0.91,
            "mapping_status": "mapped",
            "verilog_index": 1,
            "verilog": "module g(input A, B, output Y); assign Y = ~(A & B); endmodule",
            "cello_mode": "external",
            "cello_claim_level": "externally_mapped",
            "ode_status": "simulated",
            "cello_fallback_used": True,
            "part_assignments": [
                {"logic_node_id": "gate_1", "part_id": "DEMO_AmtR_CDS", "part_type": "CDS"}
            ]
        }
    ]

    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": mock_topologies,
            "best_topology": mock_topologies[1]  # Score 0.94 is best
        }
    )

    # Test Candidates List
    response = client.get("/web/runs/success_run/candidates")
    assert response.status_code == 200
    assert "Candidate #1" in response.text
    assert "Candidate #2" in response.text
    assert "★ 目前最佳" in response.text
    assert "0.940" in response.text
    assert "0.880" in response.text
    assert "暫定結果" in response.text  # Candidate #1 mock
    assert "備援結果" in response.text  # Candidate #2 fallback
    assert "未啟用" in response.text         # Candidate #1 ODE disabled
    assert "✓ 已模擬" in response.text       # Candidate #2 ODE simulated

    response_en = client.get("/web/runs/success_run/candidates?lang=en")
    assert response_en.status_code == 200
    assert "Run Candidates" in response_en.text
    assert "Current Best" in response_en.text
    assert "Primary Limiting Factor" in response_en.text
    assert "執行候選設計列表" not in response_en.text

    # Test Candidate 2 Details (Best)
    detail_resp = client.get("/web/runs/success_run/candidates/1?lang=zh-Hant")
    assert detail_resp.status_code == 200
    assert "Candidate #2 詳細設計報告" in detail_resp.text
    assert "★ 最佳候選" in detail_resp.text
    assert "0.940" in detail_resp.text
    assert "Functional (功能正確性)" in detail_resp.text
    assert "表達卡匣 (gate_1)" in detail_resp.text
    assert "DEMO_AmtR_CDS" in detail_resp.text

    # Test Invalid Candidate Index returns 404
    # 2. Candidate index not found returns 404
    bad_index_resp = client.get("/web/runs/success_run/candidates/99")
    assert bad_index_resp.status_code == 404
    assert "Candidate index 99 is out of range." in bad_index_resp.json()["error"]["message"]

    # Test Unfinished Detail page returns 400
    unfinished_detail_resp = client.get("/web/runs/active_run/candidates/0")
    assert unfinished_detail_resp.status_code == 400
    assert "Run is not completed yet." in unfinished_detail_resp.json()["error"]["message"]


def test_candidates_special_characters_safety(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # 9. HTML Injection prevention
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "<script>alert('injection')</script>"}
        }
    )

    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": [
                {
                    "score": 0.85,
                    "mapping_status": "mapped",
                    "verilog": "module test;\n// <script>console.log('xss')</script>\nendmodule",
                    "cello_mode": "mock",
                    "cello_claim_level": "mock_only"
                }
            ]
        }
    )

    response = client.get("/web/runs/inject_run/candidates")
    assert response.status_code == 200
    # The script tag should be escaped and not appear as a raw HTML tag
    assert "<script>alert" not in response.text or "&lt;script&gt;alert" in response.text


def test_candidate_simulate_get(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "Express YFP"}
        }
    )
    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": [
                {
                    "score": 0.90,
                    "mapping_status": "mapped",
                    "verilog": "module g(input A, output Y); endmodule",
                    "cello_mode": "mock",
                    "cello_claim_level": "mock_only"
                }
            ]
        }
    )

    response = client.get("/web/runs/success_run/candidates/0/simulate")
    assert response.status_code == 200
    assert "動態動力學模擬工作台" in response.text
    assert "信號 A" in response.text
    assert "開始模擬運算" in response.text


def test_candidate_simulate_post_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    services = client.app.state.test_services

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "Express YFP"}
        }
    )
    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": [
                {
                    "score": 0.90,
                    "mapping_status": "mapped",
                    "verilog": "module g(input A, output Y); endmodule",
                    "cello_mode": "mock",
                    "cello_claim_level": "mock_only"
                }
            ]
        }
    )

    mock_sim_result = {
        "simulation_spec": {},
        "simulation_result": {},
        "candidate": {
            "score": 0.95,
            "robustness_score": 0.92,
            "signal_to_noise_ratio": 12.5,
            "resource_occupancy": {
                "rnap_max": 0.08,
                "ribosome_max": 0.12
            },
            "warnings": ["Warning 1"],
            "ode_trace": {
                "time": [0.0, 10.0, 20.0],
                "output_protein": [0.0, 5.0, 10.0],
                "total_protein": [0.0, 8.0, 15.0],
                "total_mrna": [0.0, 2.0, 4.0],
                "rnap_occupancy": [0.0, 0.02, 0.04],
                "ribosome_occupancy": [0.0, 0.03, 0.06]
            }
        }
    }

    monkeypatch.setattr(
        services.simulations,
        "simulate",
        lambda *args, **kwargs: mock_sim_result
    )

    response = client.post(
        "/web/runs/success_run/candidates/0/simulate",
        data={
            "simulation_time": "300",
            "sample_count": "50",
            "noise_fraction": "0.1",
            "random_seed": "42",
            "input_type_A": "constant",
            "input_value_A": "2.0"
        }
    )
    assert response.status_code == 200
    assert "軌跡響應模擬圖" in response.text
    assert "0.950" in response.text
    assert "12.50" in response.text
    assert "8.0%" in response.text
    assert "Warning 1" in response.text
    assert "simulation_spec" in response.text


def test_candidate_compare_get(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    services = client.app.state.test_services

    mock_topologies = [
        {
            "score": 0.88,
            "functional_score": 0.95,
            "kinetic_score": 0.72,
            "metabolic_burden_score": 0.90,
            "mapping_status": "mapped",
            "verilog_index": 0,
            "verilog": "module g(input A, output Y); assign Y = ~A; endmodule",
            "cello_mode": "mock",
            "cello_claim_level": "mock_only",
            "ode_status": "disabled",
            "part_assignments": [
                {"logic_node_id": "gate_1", "part_id": "DEMO_PhlF_CDS", "part_type": "CDS"}
            ]
        },
        {
            "score": 0.94,
            "functional_score": 0.98,
            "kinetic_score": 0.92,
            "metabolic_burden_score": 0.91,
            "mapping_status": "mapped",
            "verilog_index": 1,
            "verilog": "module g(input A, B, output Y); assign Y = ~(A & B); endmodule",
            "cello_mode": "external",
            "cello_claim_level": "externally_mapped",
            "ode_status": "simulated",
            "part_assignments": [
                {"logic_node_id": "gate_1", "part_id": "DEMO_AmtR_CDS", "part_type": "CDS"}
            ]
        }
    ]

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "summary": {
                "user_intent": "Express YFP in E. coli",
                "host_organism": "Escherichia coli",
            }
        }
    )
    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": mock_topologies,
            "best_topology": mock_topologies[1]
        }
    )

    # 1. Successful comparison (Candidate 1 and 2)
    response = client.get("/web/runs/success_run/candidates/compare?indexes=0,1")
    assert response.status_code == 200
    assert "候選方案多維度對比" in response.text
    assert "Candidate #1" in response.text
    assert "Candidate #2" in response.text
    assert "0.880" in response.text
    assert "0.940" in response.text
    assert "系統推薦 Candidate #2" in response.text
    assert "Escherichia coli" in response.text

    # 2. Validation error: invalid indexes format
    response2 = client.get("/web/runs/success_run/candidates/compare?indexes=invalid")
    assert response2.status_code == 400
    assert "Invalid indexes parameter format" in response2.json()["error"]["message"]

    # 3. Validation error: index out of range
    response3 = client.get("/web/runs/success_run/candidates/compare?indexes=0,5")
    assert response3.status_code == 400
    assert "index 5 is out of range" in response3.json()["error"]["message"]


def test_candidate_promote_post(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    services = client.app.state.test_services

    mock_topologies = [
        {
            "score": 0.88,
            "functional_score": 0.95,
            "verilog": "module g(input A, output Y); assign Y = ~A; endmodule",
            "part_assignments": [
                {"logic_node_id": "gate_1", "part_id": "DEMO_PhlF_CDS", "part_type": "CDS"}
            ]
        }
    ]

    monkeypatch.setattr(
        services.runs,
        "status",
        lambda run_id: {
            "run_id": run_id,
            "status": "completed",
            "summary": {
                "user_intent": "Express YFP in E. coli",
                "host_organism": "Escherichia coli",
            }
        }
    )
    monkeypatch.setattr(
        services.runs,
        "result",
        lambda run_id: {
            "status": "completed",
            "candidate_topologies": mock_topologies,
        }
    )

    saved_design = []
    def fake_save(design_ir):
        saved_design.append(design_ir)
        return design_ir

    monkeypatch.setattr(services.designs, "save", fake_save)

    # Promote Candidate 1
    response = client.post("/web/runs/success_run/candidates/0/promote", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/web/designs/design_")

    # Verify design was converted and saved
    assert len(saved_design) == 1
    design = saved_design[0]
    assert design.name == "Design from Run success_ Candidate #1"
    assert design.parts[0].host_compatibility == ["Escherichia coli"]
