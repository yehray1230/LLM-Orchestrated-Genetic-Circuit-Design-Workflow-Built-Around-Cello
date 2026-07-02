from __future__ import annotations

from tools.tool_adapters import StochasticSimulationAdapter


def test_stochastic_adapter_available_reporting() -> None:
    adapter = StochasticSimulationAdapter()
    availability = adapter.available()
    assert availability.status == "available"
    assert availability.tool_name == "internal_stochastic_simulator"
    assert availability.adapter_name == "batch_stochastic_simulator"
    assert availability.capability == "stochastic_simulation"
    assert availability.fallback_available is False
    assert availability.fallback_used is False

    # Check that warning about internal simulator is present
    warning_codes = {warning.code for warning in availability.warnings}
    assert "INTERNAL_SIMULATOR_USED" in warning_codes
    assert not any("FALLBACK_USED" in code for code in warning_codes)


def test_stochastic_adapter_parameter_validation() -> None:
    topology = {"verilog": "module buffer(input A, output Y); assign Y = A; endmodule"}

    # Invalid random_seed
    res = StochasticSimulationAdapter().run(
        {"topology": topology, "random_seed": "not-an-integer"}
    )
    assert res.status == "failed"
    assert "INVALID_RANDOM_SEED" in {warning.code for warning in res.warnings}

    # Invalid simulation_time
    res = StochasticSimulationAdapter().run(
        {"topology": topology, "simulation_time": -10.0}
    )
    assert res.status == "failed"
    assert "INVALID_SIMULATION_TIME" in {warning.code for warning in res.warnings}

    # Invalid sample_count
    res = StochasticSimulationAdapter().run({"topology": topology, "sample_count": 0})
    assert res.status == "failed"
    assert "INVALID_SAMPLE_COUNT" in {warning.code for warning in res.warnings}

    # Invalid temporal_inputs
    res = StochasticSimulationAdapter().run(
        {"topology": topology, "temporal_inputs": "not-a-dict"}
    )
    assert res.status == "failed"
    assert "INVALID_TEMPORAL_INPUTS" in {warning.code for warning in res.warnings}


def test_stochastic_reproducibility() -> None:
    topology = {"verilog": "module buffer(input A, output Y); assign Y = A; endmodule"}

    payload1 = {
        "topology": topology,
        "runs": 5,
        "scale_factor": 5.0,
        "random_seed": 42,
        "simulation_time": 80.0,
        "sample_count": 10,
    }

    payload2 = {
        "topology": topology,
        "runs": 5,
        "scale_factor": 5.0,
        "random_seed": 42,
        "simulation_time": 80.0,
        "sample_count": 10,
    }

    res1 = StochasticSimulationAdapter().run(payload1)
    res2 = StochasticSimulationAdapter().run(payload2)

    assert res1.status == "ok"
    assert res2.status == "ok"

    stoch1 = res1.output["stochastic_result"]
    stoch2 = res2.output["stochastic_result"]

    # Verify Fano factors are exactly identical
    assert stoch1["fano_factors"] == stoch2["fano_factors"]

    # Verify memory stability is identical
    assert stoch1["memory_stability"] == stoch2["memory_stability"]

    # Verify mean trajectory values are exactly identical
    mean1 = stoch1["mean_trajectory"]
    mean2 = stoch2["mean_trajectory"]
    assert mean1["time"] == mean2["time"]
    for key in mean1:
        assert mean1[key] == mean2[key]

    # Verify all single cell runs trajectories are exactly identical
    runs1 = stoch1["runs"]
    runs2 = stoch2["runs"]
    assert len(runs1) == len(runs2)
    for r1, r2 in zip(runs1, runs2):
        assert r1["time"] == r2["time"]
        for key in r1:
            assert r1[key] == r2[key]


def test_stochastic_seed_variation() -> None:
    topology = {"verilog": "module buffer(input A, output Y); assign Y = A; endmodule"}

    payload_seed_42 = {
        "topology": topology,
        "runs": 5,
        "scale_factor": 5.0,
        "random_seed": 42,
        "simulation_time": 80.0,
        "sample_count": 10,
    }

    payload_seed_99 = {
        "topology": topology,
        "runs": 5,
        "scale_factor": 5.0,
        "random_seed": 99,
        "simulation_time": 80.0,
        "sample_count": 10,
    }

    res1 = StochasticSimulationAdapter().run(payload_seed_42)
    res2 = StochasticSimulationAdapter().run(payload_seed_99)

    assert res1.status == "ok"
    assert res2.status == "ok"

    stoch1 = res1.output["stochastic_result"]
    stoch2 = res2.output["stochastic_result"]

    # Different seeds should produce different mean trajectories due to stochasticity
    assert stoch1["mean_trajectory"] != stoch2["mean_trajectory"]


def test_stochastic_provenance() -> None:
    topology = {"verilog": "module buffer(input A, output Y); assign Y = A; endmodule"}

    payload = {
        "topology": topology,
        "runs": 5,
        "scale_factor": 5.0,
        "random_seed": 12345,
        "simulation_time": 150.0,
        "sample_count": 25,
        "temporal_inputs": {
            "A": [
                {"start": 0.0, "end": 50.0, "value": 10.0},
                {"start": 50.0, "end": 150.0, "value": 0.0},
            ]
        },
    }

    res = StochasticSimulationAdapter().run(payload)
    assert res.status == "ok"

    stoch = res.output["stochastic_result"]
    metrics = res.metrics

    # Check provenance in stoch output
    assert stoch["random_seed"] == 12345
    assert stoch["simulation_time"] == 150.0
    assert stoch["sample_count"] == 25
    assert stoch["temporal_inputs"] == {
        "A": [
            {"start": 0.0, "end": 50.0, "value": 10.0},
            {"start": 50.0, "end": 150.0, "value": 0.0},
        ]
    }

    # Check provenance in metrics
    assert metrics["random_seed"] == 12345
    assert metrics["simulation_time"] == 150.0
    assert metrics["sample_count"] == 25
    assert metrics["temporal_inputs"] == {
        "A": [
            {"start": 0.0, "end": 50.0, "value": 10.0},
            {"start": 50.0, "end": 150.0, "value": 0.0},
        ]
    }
