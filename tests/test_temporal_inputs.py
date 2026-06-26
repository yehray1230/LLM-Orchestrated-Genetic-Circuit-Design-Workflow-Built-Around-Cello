from __future__ import annotations

import math
import pytest
from pydantic import ValidationError

from api.schemas import SimulationRequest, temporal_inputs_to_dict
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


def test_temporal_step_input() -> None:
    temporal_inputs = {
        "A": {
            "type": "step",
            "time": 200.0,
            "start_value": 0.0,
            "end_value": 200.0,
        }
    }
    simulator = BatchODESimulator(
        simulation_time=600.0,
        sample_count=61,
        monte_carlo_samples=1,
        temporal_inputs=temporal_inputs,
    )
    result = simulator.simulate_topology(_buffer_topology())
    
    assert result["ode_status"] == "simulated"
    trace = result["ode_trace"]
    
    times = trace["time"]
    outputs = trace["output_protein"]
    assert len(times) == 61
    
    for t, val in zip(times, outputs):
        if t < 150.0:
            assert val < 1.0
        elif t > 550.0:
            assert val > 50.0


def test_temporal_pulse_input() -> None:
    temporal_inputs = {
        "A": {
            "type": "pulse",
            "start_time": 150.0,
            "end_time": 300.0,
            "active_value": 200.0,
            "basal_value": 0.0,
        }
    }
    simulator = BatchODESimulator(
        simulation_time=600.0,
        sample_count=61,
        monte_carlo_samples=1,
        temporal_inputs=temporal_inputs,
    )
    result = simulator.simulate_topology(_buffer_topology())
    
    assert result["ode_status"] == "simulated"
    trace = result["ode_trace"]
    
    times = trace["time"]
    mrnas = trace["total_mrna"]
    
    # Find max mRNA concentration
    max_val = max(mrnas)
    max_idx = mrnas.index(max_val)
    max_t = times[max_idx]
    
    # Peak of mRNA should occur during or shortly after the active pulse (150 to 350)
    assert 150.0 < max_t < 350.0
    # Final value at t=600 should be significantly lower than peak because mRNA degrades quickly after pulse ends
    assert mrnas[-1] < 0.5 * max_val


def test_temporal_sine_input() -> None:
    temporal_inputs = {
        "A": {
            "type": "sine",
            "amplitude": 100.0,
            "frequency": 0.005,
            "bias": 100.0,
        }
    }
    simulator = BatchODESimulator(
        simulation_time=600.0,
        sample_count=61,
        monte_carlo_samples=1,
        temporal_inputs=temporal_inputs,
    )
    result = simulator.simulate_topology(_buffer_topology())
    
    assert result["ode_status"] == "simulated"
    trace = result["ode_trace"]
    
    times = trace["time"]
    assert len(times) == 61


def test_temporal_inputs_change_simulation_configuration_hash() -> None:
    first = BatchODESimulator(
        simulation_time=120.0,
        sample_count=12,
        temporal_inputs={
            "A": {
                "type": "step",
                "time": 30.0,
                "start_value": 0.0,
                "end_value": 200.0,
            }
        },
    ).simulate_topology(_buffer_topology())
    second = BatchODESimulator(
        simulation_time=120.0,
        sample_count=12,
        temporal_inputs={
            "A": {
                "type": "step",
                "time": 90.0,
                "start_value": 0.0,
                "end_value": 200.0,
            }
        },
    ).simulate_topology(_buffer_topology())

    assert first["simulation_spec"]["configuration_hash"] != second["simulation_spec"]["configuration_hash"]
    assert first["simulation_result"]["configuration_hash"] != second["simulation_result"]["configuration_hash"]


def test_temporal_input_api_schema_normalizes_patterns() -> None:
    request = SimulationRequest(
        topology=_buffer_topology(),
        temporal_inputs={
            "A": {
                "type": "step",
                "time": 30.0,
                "start_value": 0.0,
                "end_value": 200.0,
            },
            "B": [
                {"start": 0.0, "end": 10.0, "value": 0.0},
                {"start": 10.0, "end": 20.0, "value": 50.0},
            ],
        },
    )

    payload = temporal_inputs_to_dict(request.temporal_inputs)

    assert payload["A"]["type"] == "step"
    assert payload["A"]["end_value"] == 200.0
    assert payload["B"][1]["value"] == 50.0


def test_temporal_input_api_schema_rejects_incomplete_pulse() -> None:
    with pytest.raises(ValidationError):
        SimulationRequest(
            topology=_buffer_topology(),
            temporal_inputs={
                "A": {
                    "type": "pulse",
                    "start_time": 10.0,
                    "active_value": 200.0,
                    "basal_value": 0.0,
                }
            },
        )
