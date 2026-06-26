from __future__ import annotations

from tools.sensitivity_analysis import run_parameter_sweep, run_bifurcation_sweep
from schemas.host_profile import default_yeast_profile


def _buffer_topology() -> dict:
    return {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
        "copy_number": 5.0,
    }


def test_run_parameter_sweep() -> None:
    topology = _buffer_topology()
    sweep_values = [1.0, 5.0, 10.0]
    
    res = run_parameter_sweep(
        topology=topology,
        parameter_name="copy_number",
        sweep_values=sweep_values,
    )
    
    assert res["parameter_name"] == "copy_number"
    assert res["report_type"] == "parameter_sensitivity_sweep"
    assert res["schema_version"] == "1.0.0"
    assert res["host_profile_id"] == "ecoli_k12_default"
    assert res["sweep_values"] == sweep_values
    assert len(res["results"]) == 3
    for r in res["results"]:
        assert r["schema_version"] == "1.0.0"
        assert "value" in r
        assert "dynamic_margin" in r
        assert "signal_to_noise_ratio" in r
        assert "kinetic_score" in r
        assert "max_burden_nM" in r


def test_parameter_sweep_supports_profile_dicts_and_aliases() -> None:
    topology = _buffer_topology()
    profile = default_yeast_profile().to_dict()

    res = run_parameter_sweep(
        topology=topology,
        parameter_name="ribo_total",
        sweep_values=[1000.0, 120000.0],
        host_profile_id="yeast_sc_default",
        host_profiles={"yeast_sc_default": profile},
    )

    assert res["requested_parameter_name"] == "ribo_total"
    assert res["parameter_name"] == "ribosome_total"
    assert res["host_profile_id"] == "yeast_sc_default"
    assert len(res["results"]) == 2
    assert all(item["max_burden_nM"] > 0 for item in res["results"])


def test_run_bifurcation_sweep() -> None:
    topology = _buffer_topology()
    input_values = [0.0, 50.0, 100.0, 200.0]
    
    res = run_bifurcation_sweep(
        topology=topology,
        input_name="A",
        input_values=input_values,
    )
    
    assert res["input_name"] == "A"
    assert res["report_type"] == "bifurcation_sweep"
    assert res["schema_version"] == "1.0.0"
    assert res["host_profile_id"] == "ecoli_k12_default"
    assert "results" in res
    assert len(res["results"]) == 4
    for r in res["results"]:
        assert r["schema_version"] == "1.0.0"
        assert "input_value" in r
        assert "output_value" in r
        assert "burden_nM" in r
