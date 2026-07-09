from __future__ import annotations

from pathlib import Path
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
    app.dependency_overrides[get_services] = lambda: test_services
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_e2e_design_intake_and_elicitation_skip(client, test_services) -> None:
    # 1. Initialize draft
    test_services.design_drafts.save({
        "current_step": 1,
        "user_intent": "Build an oscillator circuit"
    })

    # 2. Skip elicitation flow (offline fallback)
    response = client.post("/api/v1/designs/drafts/elicitation/skip")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["structured_spec"]["chassis"] == "Escherichia coli"
    assert data["structured_spec"]["copy_number"] == 15
    assert data["pm_stage"] == "completed"
    assert data["pending_proposal"] == {}


def test_e2e_run_monitor_lifecycle(client, test_services) -> None:
    # 1. Start a design run
    result = test_services.runs.start({
        "user_intent": "Build an OR gate",
        "host_organism": "E. coli",
        "compute_budget": 5,
    })
    run_id = result["run_id"]

    # 2. Get details page /web/runs/{run_id}
    response = client.get(f"/web/runs/{run_id}")
    assert response.status_code == 200
    assert b"Design run monitor" in response.content

    # 3. Post cancel request
    response_cancel = client.post(f"/web/runs/{run_id}/cancel", follow_redirects=False)
    assert response_cancel.status_code == 303
    assert response_cancel.headers["location"].endswith(f"/web/runs/{run_id}")

    # 4. Post retry request (creates a new run)
    response_retry = client.post(f"/web/runs/{run_id}/retry", follow_redirects=False)
    assert response_retry.status_code == 303
    assert "/web/runs/run_" in response_retry.headers["location"]


def test_e2e_candidate_workbench_compare_promote(client, test_services, monkeypatch) -> None:
    # 1. Configure completed run with multiple candidates
    run_id = "run_completed_test"
    monkeypatch.setattr(
        test_services.runs,
        "status",
        lambda r_id: {
            "run_id": r_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {
                "user_intent": "Express YFP in E. coli",
                "host_organism": "Escherichia coli",
            }
        }
    )

    mock_topologies = [
        {
            "score": 0.85,
            "functional_score": 0.90,
            "kinetic_score": 0.70,
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
            "score": 0.95,
            "functional_score": 0.99,
            "kinetic_score": 0.90,
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
        test_services.runs,
        "result",
        lambda r_id: {
            "status": "completed",
            "candidate_topologies": mock_topologies,
            "best_topology": mock_topologies[1]
        }
    )

    # 2. Get Candidates List
    response = client.get(f"/web/runs/{run_id}/candidates")
    assert response.status_code == 200
    assert "Candidate #1" in response.text
    assert "Candidate #2" in response.text

    # 3. Compare Candidates
    compare_resp = client.get(f"/web/runs/{run_id}/candidates/compare?indexes=0,1")
    assert compare_resp.status_code == 200
    assert "候選方案多維度對比" in compare_resp.text
    assert "Candidate #1" in compare_resp.text
    assert "Candidate #2" in compare_resp.text

    # 4. Promote Candidate 1
    saved_design = []
    monkeypatch.setattr(test_services.designs, "save", lambda design: saved_design.append(design))

    promote_resp = client.post(f"/web/runs/{run_id}/candidates/0/promote", follow_redirects=False)
    assert promote_resp.status_code == 303
    assert promote_resp.headers["location"].startswith("/web/designs/design_")
    assert len(saved_design) == 1
    assert saved_design[0].name == f"Design from Run {run_id[:8]} Candidate #1"


def test_e2e_candidate_simulation_and_warnings(client, test_services, monkeypatch) -> None:
    # 1. Setup completed run with a simulated candidate
    run_id = "run_sim_test"
    monkeypatch.setattr(
        test_services.runs,
        "status",
        lambda r_id: {
            "run_id": r_id,
            "status": "completed",
            "progress": 1.0,
            "summary": {"user_intent": "Express YFP"}
        }
    )
    mock_topology = {
        "score": 0.90,
        "mapping_status": "mapped",
        "verilog": "module g(input A, output Y); endmodule",
        "cello_mode": "mock",
        "cello_claim_level": "mock_only"
    }
    monkeypatch.setattr(
        test_services.runs,
        "result",
        lambda r_id: {
            "status": "completed",
            "candidate_topologies": [mock_topology]
        }
    )

    # 2. Get Simulation Page
    response = client.get(f"/web/runs/{run_id}/candidates/0/simulate")
    assert response.status_code == 200
    assert "動態動力學模擬工作台" in response.text

    # 3. Post Simulation Run and Check Warnings
    mock_sim_result = {
        "simulation_spec": {},
        "simulation_result": {},
        "candidate": {
            "score": 0.92,
            "robustness_score": 0.88,
            "signal_to_noise_ratio": 10.5,
            "resource_occupancy": {"rnap_max": 0.05, "ribosome_max": 0.10},
            "warnings": [
                "Retroactivity warning: regulator Q has high load sequestration",
                "RBS blocking warning: gene Q has low RBS accessibility"
            ],
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
        test_services.simulations,
        "simulate",
        lambda *args, **kwargs: mock_sim_result
    )

    response_sim = client.post(
        f"/web/runs/{run_id}/candidates/0/simulate",
        data={
            "simulation_time": "100",
            "sample_count": "20",
            "noise_fraction": "0.1",
            "input_type_A": "constant",
            "input_value_A": "1.5"
        }
    )
    assert response_sim.status_code == 200
    assert "軌跡響應模擬圖" in response_sim.text
    assert "Retroactivity warning" in response_sim.text
    assert "RBS blocking warning" in response_sim.text
