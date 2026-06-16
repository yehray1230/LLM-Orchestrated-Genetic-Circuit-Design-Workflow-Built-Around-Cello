from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from benchmark_suite.benchmark_controller import evaluate_candidate
from benchmark_suite.scoring_profiles import get_scoring_profile
from schemas.design_ir import topology_to_design_ir
from schemas.design_migrations import migrate_design_ir_v1_to_v2
from schemas.run_manifest import (
    create_run_manifest,
    finalize_run_manifest,
)
from schemas.simulation import (
    SIMULATION_MODEL_VERSION,
    parse_logic_value,
    simulation_spec_from_design_ir_v2,
    simulation_spec_from_topology,
    stable_seed,
)
from tools.ode_simulator import BatchODESimulator


def _buffer_topology() -> dict:
    return {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
        "copy_number": 5,
    }


def test_logic_value_parser_handles_string_zero_and_low_states() -> None:
    assert parse_logic_value("0") is False
    assert parse_logic_value("false") is False
    assert parse_logic_value("off") is False
    assert parse_logic_value("1") is True
    assert parse_logic_value("high") is True


def test_simulation_spec_is_versioned_and_content_addressed() -> None:
    first = simulation_spec_from_topology(
        _buffer_topology(),
        input_signals=["A"],
        target_output="Y",
    )
    same = simulation_spec_from_topology(
        _buffer_topology(),
        input_signals=["A"],
        target_output="Y",
    )
    changed = simulation_spec_from_topology(
        {**_buffer_topology(), "copy_number": 10},
        input_signals=["A"],
        target_output="Y",
    )

    assert first.model_version == SIMULATION_MODEL_VERSION
    assert first.validate() == []
    assert first.configuration_hash == same.configuration_hash
    assert first.configuration_hash != changed.configuration_hash
    assert first.scenarios[0].inputs["A"] is False
    assert first.scenarios[0].expected_outputs["Y"] is False


def test_stable_seed_is_based_on_canonical_content() -> None:
    assert stable_seed({"b": 2, "a": 1}) == stable_seed({"a": 1, "b": 2})
    assert stable_seed({"a": 1}) != stable_seed({"a": 2})


def test_design_ir_v2_maps_chassis_copy_number_and_truth_table() -> None:
    design = migrate_design_ir_v1_to_v2(
        topology_to_design_ir(
            _buffer_topology(),
            host_organism="Escherichia coli",
            design_id="simulation_mapping",
        ).to_dict()
    ).design
    design.specification.truth_table = _buffer_topology()["truth_table"]
    design.extensions["verilog"] = _buffer_topology()["verilog"]
    design.plasmids = []

    spec = simulation_spec_from_design_ir_v2(design)

    assert spec.chassis == "Escherichia coli"
    assert spec.copy_number == 1.0
    assert spec.assumptions
    assert len(spec.scenarios) == 2


def test_ode_result_contains_reproducibility_contract() -> None:
    simulator = BatchODESimulator(
        simulation_time=40.0,
        sample_count=10,
        random_seed=17,
    )
    first = simulator.simulate_topology(_buffer_topology())
    second = simulator.simulate_topology(_buffer_topology())

    assert first["ode_status"] == "simulated"
    assert first["dynamic_margin"] > 0
    assert first["simulation_model_version"] == SIMULATION_MODEL_VERSION
    assert first["simulation_spec"]["configuration_hash"]
    assert first["simulation_result"]["result_hash"]
    assert (
        first["simulation_result"]["result_hash"]
        == second["simulation_result"]["result_hash"]
    )


def test_run_manifest_captures_simulation_hashes() -> None:
    candidate = BatchODESimulator(
        simulation_time=30.0,
        sample_count=8,
    ).simulate_topology(_buffer_topology())
    manifest = create_run_manifest("run_simulation", {"user_intent": "buffer"})
    finalized = finalize_run_manifest(
        manifest,
        status="completed",
        result={"best_topology": candidate},
        started_at="2026-06-14T00:00:00+00:00",
        finished_at="2026-06-14T00:01:00+00:00",
    )

    assert finalized.application_version == "1.9.0"
    assert finalized.simulation["model_version"] == SIMULATION_MODEL_VERSION
    assert finalized.simulation["configuration_hash"]
    assert finalized.simulation["result_hash"]


def test_preview_scoring_profile_links_simulation_version() -> None:
    candidate = BatchODESimulator(
        simulation_time=30.0,
        sample_count=8,
    ).simulate_topology(_buffer_topology())
    result = evaluate_candidate(candidate, profile_id="research-v2-preview")

    assert get_scoring_profile("research-v2-preview").version == "1.9.0"
    assert result["simulation_model_version"] == SIMULATION_MODEL_VERSION
    assert result["simulation_configuration_hash"]


def test_simulation_api_and_design_spec_endpoint(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save(
        topology_to_design_ir(
            _buffer_topology(),
            host_organism="Escherichia coli",
            design_id="simulation_api_design",
        )
    )
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            models = client.get("/api/v1/simulation/models")
            simulated = client.post(
                "/api/v1/simulations",
                json={
                    "topology": _buffer_topology(),
                    "simulation_time": 30,
                    "sample_count": 8,
                    "random_seed": 11,
                },
            )
            spec = client.get(
                "/api/v1/designs/simulation_api_design/simulation-spec"
            )
    finally:
        app.dependency_overrides.clear()

    assert models.status_code == 200
    assert models.json()["data"]["items"][0]["version"] == SIMULATION_MODEL_VERSION
    assert simulated.status_code == 200
    assert simulated.json()["data"]["simulation_result"]["status"] == "simulated"
    assert spec.status_code == 200
    assert spec.json()["data"]["model_version"] == SIMULATION_MODEL_VERSION


def test_simulation_with_ucf_and_copy_number_perturbation(tmp_path: Path) -> None:
    # 1. Create a mock UCF file
    ucf_content = [
        {
            "collection": "gates",
            "name": "P1_PhlF",
            "gate_type": "NOR",
            "response_function": {
                "function": "hill_function",
                "parameters": {
                    "ymin": 0.02,
                    "ymax": 2.0,
                    "K": 0.45,
                    "n": 2.5
                }
            },
            "regulator": "PhlF",
            "promoter": "P_PhlF"
        }
    ]
    import json
    ucf_file = tmp_path / "test_ucf.json"
    ucf_file.write_text(json.dumps(ucf_content), encoding="utf-8")

    # 2. Test parse_ucf_gate_parameters
    from tools.cello_artifact_parser import parse_ucf_gate_parameters
    gate_params = parse_ucf_gate_parameters(ucf_file)
    assert "PhlF" in gate_params
    assert gate_params["PhlF"]["ymin"] == 0.02
    assert gate_params["PhlF"]["ymax"] == 2.0
    assert gate_params["PhlF"]["K"] == 0.45
    assert gate_params["PhlF"]["n"] == 2.5

    # 3. Test simulation_spec_from_design_ir_v2 mapping
    design = migrate_design_ir_v1_to_v2(
        topology_to_design_ir(
            _buffer_topology(),
            host_organism="Escherichia coli",
            design_id="simulation_mapping",
        ).to_dict()
    ).design
    design.specification.truth_table = _buffer_topology()["truth_table"]
    design.extensions["verilog"] = _buffer_topology()["verilog"]
    design.extensions["ucf_path"] = str(ucf_file.resolve())
    
    from schemas.design_ir import PartAssignment
    design.assignments = [
        PartAssignment(
            logic_node_id="g1",
            part_id="DEMO_PhlF_CDS",
            part_name="PhlF regulator",
            part_type="CDS"
        )
    ]
    
    spec = simulation_spec_from_design_ir_v2(design)
    assert spec.parameters.get("kd_g1") == 0.45
    assert spec.parameters.get("hill_coefficient_g1") == 2.5
    assert spec.parameters.get("leak_fraction_g1") == 0.02 / 2.0

    # 4. Test log-normal perturbation of copy_number
    from tools.ode_simulator import _perturb_biokinetic_parameters
    import numpy as np
    rng = np.random.default_rng(42)
    perturbed = _perturb_biokinetic_parameters(
        {"copy_number": 5.0},
        noise_level=0.15,
        rng=rng,
        perturbable=["copy_number"]
    )
    assert perturbed["copy_number"] > 0.0
    assert perturbed["copy_number"] != 5.0
