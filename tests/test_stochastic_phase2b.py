from __future__ import annotations

import pytest

from tools.tool_adapters import StochasticSimulationAdapter
from tools.ode_simulator import BatchODESimulator


def test_stochastic_simulation_adapter_registration() -> None:
    adapter = StochasticSimulationAdapter()
    availability = adapter.available()
    assert availability.status in ("available", "fallback")
    assert availability.capability == "stochastic_simulation"


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        ({"topology": {}}, "MISSING_INPUT"),
        (
            {
                "topology": {
                    "verilog": "module buffer(input A, output Y); assign Y = A; endmodule"
                },
                "runs": 0,
            },
            "INVALID_RUNS",
        ),
        (
            {
                "topology": {
                    "verilog": "module buffer(input A, output Y); assign Y = A; endmodule"
                },
                "scale_factor": 0,
            },
            "INVALID_SCALE_FACTOR",
        ),
    ],
)
def test_stochastic_adapter_rejects_invalid_inputs(
    payload: dict,
    expected_code: str,
) -> None:
    result = StochasticSimulationAdapter().run(payload)

    assert result.status == "failed"
    assert expected_code in {warning.code for warning in result.warnings}
    assert result.metrics == {}


def test_stochastic_simulator_rejects_invalid_scale_before_numpy() -> None:
    topology = {
        "verilog": "module buffer(input A, output Y); assign Y = A; endmodule"
    }

    with pytest.raises(ValueError, match="scale_factor"):
        BatchODESimulator().simulate_stochastic(
            topology,
            runs=1,
            scale_factor=0,
        )


def test_stochastic_simulation_buffer() -> None:
    # A simple buffer circuit: A -> Y
    topology = {
        "verilog": "module buffer(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "1", "Y": "1"}
        ]
    }

    # Run stochastic simulation
    simulator = BatchODESimulator(simulation_time=100.0, sample_count=11)
    res = simulator.simulate_stochastic(topology, runs=5, scale_factor=5.0)

    assert "runs" in res
    assert "mean_trajectory" in res
    assert "fano_factors" in res
    assert "memory_stability" in res

    # 5 runs returned for plotting
    assert len(res["runs"]) == 5
    # The time points count should match sample_count (11)
    assert len(res["mean_trajectory"]["time"]) == 11

    # Check that Y is in fano_factors
    assert "Y" in res["fano_factors"]
    assert res["fano_factors"]["Y"] >= 0.0
    assert res["simulation_status"] == "completed"
    assert res["truncated_run_count"] == 0


def test_stochastic_step_limit_is_reported_as_truncated() -> None:
    topology = {
        "verilog": "module buffer(input A, output Y); assign Y = A; endmodule",
        "copy_number": 100.0,
        "biokinetic_parameters": {
            "transcription_rate": {"value": 100.0, "unit": "nM s-1"},
        },
    }

    direct = BatchODESimulator(
        simulation_time=100.0,
        sample_count=11,
    ).simulate_stochastic(
        topology,
        runs=2,
        scale_factor=5.0,
        max_steps=1,
    )
    adapted = StochasticSimulationAdapter().run(
        {
            "topology": topology,
            "runs": 2,
            "scale_factor": 5.0,
            "max_steps": 1,
        }
    )

    assert direct["simulation_status"] == "truncated"
    assert direct["truncated_run_count"] >= 1
    assert any(item["status"] == "truncated" for item in direct["run_statuses"])
    assert adapted.status == "failed"
    assert "SSA_STEP_LIMIT_REACHED" in {
        warning.code for warning in adapted.warnings
    }


def test_stochastic_latch_memory_retention() -> None:
    # NOR-based SR Latch
    topology = {
        "verilog": """
        module sr_latch(input S, input R, output Q, output Qbar);
          nor g1(Q, R, Qbar);
          nor g2(Qbar, S, Q);
        endmodule
        """,
        "operons": [["Q"], ["Qbar"]],
    }

    simulator = BatchODESimulator(simulation_time=150.0, sample_count=16)

    # We want to start in a state where Q is high and Qbar is low
    # Initialize Q = 20 nM (200 molecules at scale = 10), Qbar = 0
    topology["initial_molecules"] = {
        "protein_mature_Q": 200.0,
        "protein_mature_Qbar": 0.0,
    }

    res = simulator.simulate_stochastic(topology, runs=10, scale_factor=10.0)

    assert "runs" in res
    assert "mean_trajectory" in res
    # Memory retention stability should be reported
    assert "memory_stability" in res
    assert 0.0 <= res["memory_stability"] <= 1.0
