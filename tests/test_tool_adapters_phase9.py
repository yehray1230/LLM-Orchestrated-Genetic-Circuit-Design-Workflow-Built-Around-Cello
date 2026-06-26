from __future__ import annotations

from schemas.run_manifest import create_run_manifest, finalize_run_manifest
from tools.tool_adapters import (
    CAPABILITY_LOGIC_SYNTHESIS,
    CAPABILITY_ODE_SIMULATION,
    CelloLogicSynthesisAdapter,
    ODESimulationAdapter,
    detect_cli_tool,
    inspect_capabilities,
)


def _buffer_topology() -> dict:
    return {
        "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        "truth_table": [
            {"A": "0", "Y": "0"},
            {"A": "1", "Y": "1"},
        ],
    }


def test_capability_registry_exposes_existing_tool_adapters() -> None:
    capabilities = inspect_capabilities()

    assert CAPABILITY_LOGIC_SYNTHESIS in capabilities["catalog"]
    assert CAPABILITY_ODE_SIMULATION in capabilities["capabilities"]
    assert {
        (tool["tool_name"], tool["adapter_name"])
        for tool in capabilities["tools"]
    } >= {
        ("cello", "cello_wrapper"),
        ("internal_ode_simulator", "batch_ode_simulator"),
    }


def test_missing_cli_dependency_is_normalized_without_crashing() -> None:
    availability = detect_cli_tool(
        "definitely_missing_phase9_tool",
        tool_name="missing-tool",
        adapter_name="missing_adapter",
        capability="rna_folding",
        fallback_available=True,
    )

    assert availability.status == "unavailable"
    assert availability.fallback_available is True
    assert availability.warnings[0].code == "TOOL_UNAVAILABLE"


def test_cello_adapter_reports_mock_fallback_for_unconfigured_cello() -> None:
    result = CelloLogicSynthesisAdapter().run(
        {"verilog": _buffer_topology()["verilog"]}
    )

    assert result.status == "fallback"
    assert result.availability.fallback_used is True
    assert result.output["topology"]["mapping_status"] == "unmapped"
    assert any(warning.code == "FALLBACK_USED" for warning in result.warnings)


def test_ode_adapter_runs_existing_simulator_and_normalizes_metrics() -> None:
    result = ODESimulationAdapter().run({"topology": _buffer_topology()})

    assert result.status == "ok"
    assert result.availability.capability == CAPABILITY_ODE_SIMULATION
    assert result.output["topology"]["ode_status"] == "simulated"
    assert "dynamic_margin" in result.metrics


def test_run_manifest_captures_normalized_tool_records() -> None:
    adapter_result = CelloLogicSynthesisAdapter().run(
        {"verilog": _buffer_topology()["verilog"]}
    )
    manifest = create_run_manifest("phase9_tools", {"user_intent": "buffer"})

    finalized = finalize_run_manifest(
        manifest,
        status="completed",
        result={"tools": [adapter_result.availability.to_dict()]},
        started_at="2026-06-24T00:00:00+00:00",
        finished_at="2026-06-24T00:01:00+00:00",
    )

    assert finalized.tools[0].tool_name == "cello"
    assert finalized.tools[0].capability == CAPABILITY_LOGIC_SYNTHESIS
    assert finalized.tools[0].fallback_used is True
    assert finalized.tools[0].warnings[0]["code"] == "FALLBACK_USED"
