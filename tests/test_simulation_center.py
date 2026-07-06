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
        specification=DesignSpecification(
            inputs=["A"],
            outputs=["Y"],
            truth_table=[
                {"input": {"A": 0}, "output": {"Y": 1}},
                {"input": {"A": 1}, "output": {"Y": 0}},
            ]
        ),
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
        extensions={
            "verilog": "module test(A, Y); input A; output Y; not(Y, A); endmodule",
            "biokinetic_parameters": {
                "transcription_rate": 1.0,
                "kd": 1.0,
                "translation_rate": 1.0,
                "copy_number": 1.0,
            }
        }
    )


def test_simulation_ode_routes(client, test_services):
    # Save a design first
    design = _create_sample_design("design_test_sim")
    test_services.designs.save_v2(design)
    
    # 1. GET ODE page
    response = client.get("/web/designs/design_test_sim/simulation/ode")
    assert response.status_code == 200
    assert b"ODE" in response.content

    # 2. POST ODE simulation
    response = client.post(
        "/web/designs/design_test_sim/simulation/ode",
        data={
            "simulation_time": "300",
            "sample_count": "50",
            "noise_fraction": "0.1",
            "input_type_A": "constant",
            "input_value_A": "1.5",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/web/designs/design_test_sim/simulation/ode?run_id=research_" in response.headers["location"]


def test_simulation_ssa_routes(client, test_services):
    design = _create_sample_design("design_test_ssa")
    test_services.designs.save_v2(design)

    # 1. GET SSA page
    response = client.get("/web/designs/design_test_ssa/simulation/ssa")
    assert response.status_code == 200
    assert b"SSA" in response.content

    # 2. POST SSA simulation
    response = client.post(
        "/web/designs/design_test_ssa/simulation/ssa",
        data={
            "runs": "5",
            "scale_factor": "5.0",
            "max_steps": "1000",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/web/designs/design_test_ssa/simulation/ssa?run_id=research_" in response.headers["location"]


def test_simulation_sweep_and_bifurcation(client, test_services):
    design = _create_sample_design("design_test_sweep")
    test_services.designs.save_v2(design)

    # 1. Parameter sweep POST
    response = client.post(
        "/web/designs/design_test_sweep/simulation/sweep",
        data={
            "parameter_name": "transcription_rate",
            "sweep_values": "0.2, 1.0, 5.0",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/web/designs/design_test_sweep/simulation/sweep?run_id=research_" in response.headers["location"]

    # 2. Bifurcation POST
    response = client.post(
        "/web/designs/design_test_sweep/simulation/bifurcation",
        data={
            "input_name": "A",
            "input_values": "0.0, 0.5, 1.0",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/web/designs/design_test_sweep/simulation/bifurcation?run_id=research_" in response.headers["location"]


def test_parameter_fit_comparison(client, test_services):
    design = _create_sample_design("design_test_fit")
    test_services.designs.save_v2(design)

    # Create a parameter fit snapshot first
    snapshot_id = "snap_1"
    test_services.simulations.parameter_fit_repository.save(
        snapshot_id,
        {
            "snapshot_id": snapshot_id,
            "part_id": "part_1",
            "source": "plate_reader",
            "override": {
                "parameters": {
                    "transcription_rate": {
                        "value": 2.5,
                        "parameter_origin": "fitted",
                        "confidence_category": "measured",
                        "data_boundary": "local_private",
                        "source": "plate_reader",
                    }
                }
            },
        },
    )

    # 1. GET Fit page
    response = client.get("/web/designs/design_test_fit/simulation/fit")
    assert response.status_code == 200
    assert b"snap_1" in response.content

    # 2. POST Fit comparison
    response = client.post(
        "/web/designs/design_test_fit/simulation/fit",
        data={
            "snapshot_id": "snap_1",
            "simulation_time": "100",
            "sample_count": "10",
        },
    )
    assert response.status_code == 200
    assert b"Theoretical" in response.content or b"default_run" in response.content or b"metric_deltas" in response.content

