from __future__ import annotations

from typing import Any


def explain_ode_topology(topology: dict[str, Any] | None) -> dict[str, Any]:
    if not topology:
        return {
            "status": "unavailable",
            "summary": "No topology is available for ODE explanation.",
            "key_readouts": {},
            "burden_readouts": {},
            "stability_readouts": {},
            "interpretation": ["No ODE result is available."],
            "coverage_warnings": ["No input scenario or ODE trace is available."],
            "next_checks": ["Run ODE simulation before interpreting dynamic behavior."],
        }

    ode_status = str(topology.get("ode_status", "unknown"))
    input_scenario = _input_scenario(topology)
    trace = topology.get("ode_trace")
    valid_trace = _valid_trace(trace)
    if ode_status == "disabled":
        return _not_simulated_response(
            "disabled",
            "ODE simulation was disabled for this topology.",
            input_scenario,
            ["Enable ODE simulation to estimate expression dynamics and burden signals."],
        )
    if ode_status in {"failed", "error"}:
        return _not_simulated_response(
            ode_status,
            "ODE simulation failed for this topology.",
            input_scenario,
            ["Inspect ODE parameters and topology structure before trusting dynamic behavior."],
        )
    if not valid_trace:
        return _not_simulated_response(
            ode_status,
            "ODE trace is missing or incomplete.",
            input_scenario,
            ["Rerun ODE simulation and persist the time-series trace for explanation."],
        )

    readouts = _key_readouts(trace)
    burden = _burden_readouts(trace)
    stability = _stability_readouts(topology)
    coverage = _coverage_warnings(topology, input_scenario, stability)
    interpretation = _interpretation(readouts, burden, stability, topology)
    next_checks = _next_checks(readouts, burden, stability, coverage, topology)
    return {
        "status": ode_status,
        "summary": _summary(readouts, burden, stability),
        "input_scenario": input_scenario,
        "units": {
            "time": "seconds",
            "output_protein": "arbitrary units",
            "total_mrna": "arbitrary units",
            "total_protein": "arbitrary units",
            "occupancy": "fraction 0-1",
        },
        "key_readouts": readouts,
        "burden_readouts": burden,
        "stability_readouts": stability,
        "interpretation": interpretation,
        "coverage_warnings": coverage,
        "model_limitations": _model_limitations(),
        "next_checks": next_checks,
    }


def _not_simulated_response(
    status: str,
    summary: str,
    input_scenario: dict[str, Any],
    next_checks: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "summary": summary,
        "input_scenario": input_scenario,
        "key_readouts": {},
        "burden_readouts": {},
        "stability_readouts": {"uncertainty_evaluated": False},
        "interpretation": [summary],
        "coverage_warnings": [
            "No trajectory readouts can be extracted without a valid ODE trace.",
            "ON/OFF ratio, leakage, and steady-state behavior remain untested.",
        ],
        "model_limitations": _model_limitations(),
        "next_checks": next_checks,
    }


def _input_scenario(topology: dict[str, Any]) -> dict[str, Any]:
    scenario = topology.get("input_scenario")
    if isinstance(scenario, dict):
        return scenario
    simulation_spec = topology.get("simulation_spec")
    if isinstance(simulation_spec, dict):
        scenarios = simulation_spec.get("scenarios")
        return {
            "scenario_id": "simulation_spec",
            "input_mode": "truth_table",
            "description": "Scenarios were read from the versioned SimulationSpec.",
            "simulated_cases": scenarios if isinstance(scenarios, list) else [],
            "missing_cases": [],
        }
    return {
        "scenario_id": "default_step",
        "input_mode": "default_step",
        "description": "Default simulator input assumptions were used; explicit external input scenario metadata is not available.",
        "simulated_cases": [],
        "missing_cases": [],
    }


def _valid_trace(trace: Any) -> bool:
    if not isinstance(trace, dict):
        return False
    time = trace.get("time")
    output = trace.get("output_protein")
    return isinstance(time, list) and isinstance(output, list) and len(time) == len(output) and len(time) > 1


def _key_readouts(trace: dict[str, list[Any]]) -> dict[str, Any]:
    time = _series(trace.get("time"))
    output = _series(trace.get("output_protein"))
    peak_index = max(range(len(output)), key=lambda index: output[index])
    peak_output = output[peak_index]
    initial_output = output[0]
    final_output = output[-1]
    fold_change = _safe_ratio(final_output, initial_output)
    final_peak_ratio = _safe_ratio(final_output, peak_output)
    response_time = _response_time(time, output, initial_output, peak_output)
    return {
        "initial_output_protein": round(initial_output, 6),
        "peak_output_protein": round(peak_output, 6),
        "time_to_peak": round(time[peak_index], 6),
        "final_output_protein": round(final_output, 6),
        "output_fold_change": fold_change,
        "final_to_peak_ratio": final_peak_ratio,
        "approx_response_time_to_90pct_peak": response_time,
        "steady_state_reached": _steady_state_status(time, output),
    }


def _burden_readouts(trace: dict[str, list[Any]]) -> dict[str, Any]:
    time = _series(trace.get("time"))
    total_mrna = _series(trace.get("total_mrna"))
    total_protein = _series(trace.get("total_protein"))
    rnap = _series(trace.get("rnap_occupancy"))
    ribosome = _series(trace.get("ribosome_occupancy"))
    max_burden_values = [max(total_mrna or [0.0]), max(total_protein or [0.0])]
    max_burden = max(max_burden_values)
    burden_peak_time = _time_of_max(time, total_protein or total_mrna)
    max_rnap = max(rnap) if rnap else None
    max_ribosome = max(ribosome) if ribosome else None
    return {
        "max_total_mrna": _round_or_none(max(total_mrna) if total_mrna else None),
        "max_total_protein": _round_or_none(max(total_protein) if total_protein else None),
        "max_rnap_occupancy": _round_or_none(max_rnap),
        "max_ribosome_occupancy": _round_or_none(max_ribosome),
        "burden_peak_time": _round_or_none(burden_peak_time),
        "burden_risk_level": _burden_risk(max_rnap, max_ribosome, max_burden),
    }


def _stability_readouts(topology: dict[str, Any]) -> dict[str, Any]:
    runs = _int_or_none(topology.get("monte_carlo_runs", topology.get("monte_carlo_samples")))
    failure_rate = _number(topology.get("monte_carlo_failure_rate"))
    terminal_cv = _number(topology.get("monte_carlo_terminal_output_cv"))
    output_cv = _number(topology.get("metrics_cv"))
    robustness = _number(topology.get("robustness_score"))
    uncertainty_evaluated = bool(runs and runs > 1)
    return {
        "uncertainty_evaluated": uncertainty_evaluated,
        "monte_carlo_runs": runs,
        "monte_carlo_failure_rate": _round_or_none(failure_rate),
        "monte_carlo_terminal_output_cv": _round_or_none(terminal_cv),
        "output_cv": _round_or_none(output_cv),
        "robustness_score": _round_or_none(robustness),
    }


def _coverage_warnings(
    topology: dict[str, Any],
    input_scenario: dict[str, Any],
    stability: dict[str, Any],
) -> list[str]:
    warnings = []
    mode = str(input_scenario.get("input_mode", ""))
    simulated_cases = input_scenario.get("simulated_cases")
    missing_cases = input_scenario.get("missing_cases")
    if mode == "default_step":
        warnings.append("Input scenario metadata is missing; the result cannot be tied to explicit inducer or truth-table conditions.")
    if not simulated_cases:
        warnings.append("No explicit truth-table coverage is recorded, so ON/OFF coverage cannot be verified.")
    if missing_cases:
        warnings.append(f"Missing truth-table cases: {', '.join(str(case) for case in missing_cases)}.")
    if not topology.get("off_state_trace") and not topology.get("on_off_ratio"):
        warnings.append("OFF-state trajectory is not available; leakage and ON/OFF ratio remain untested.")
    if not stability.get("uncertainty_evaluated"):
        warnings.append("Parameter uncertainty was not evaluated with Monte Carlo perturbation.")
    return warnings


def _interpretation(
    readouts: dict[str, Any],
    burden: dict[str, Any],
    stability: dict[str, Any],
    topology: dict[str, Any],
) -> list[str]:
    interpretation = []
    fold_change = _number(readouts.get("output_fold_change"))
    if fold_change is None:
        interpretation.append("Output fold-change cannot be estimated because the initial output is near zero or unavailable.")
    elif fold_change >= 5.0:
        interpretation.append("The simulated output increases strongly over the time window.")
    elif fold_change >= 1.5:
        interpretation.append("The simulated output increases, but the response is moderate.")
    else:
        interpretation.append("The simulated output shows limited activation over the time window.")

    steady = readouts.get("steady_state_reached")
    if steady is True:
        interpretation.append("The trajectory appears close to steady state near the end of the simulation window.")
    elif steady is False:
        interpretation.append("The trajectory is still changing near the end; final output may not represent steady state.")
    else:
        interpretation.append("Steady-state status is uncertain from the available trace.")

    risk = burden.get("burden_risk_level")
    if risk == "high":
        interpretation.append("Resource occupancy suggests a high burden risk that may affect host growth or expression reliability.")
    elif risk == "moderate":
        interpretation.append("Resource occupancy suggests a moderate burden risk; compare against lower-burden alternatives.")
    else:
        interpretation.append("No immediate high resource-occupancy signal is visible in the stored trace.")

    dynamic_margin = _number(topology.get("dynamic_margin"))
    if dynamic_margin is not None and dynamic_margin < 0.2:
        interpretation.append("Dynamic margin is low, so ON/OFF separation may be weak.")

    if stability.get("uncertainty_evaluated"):
        interpretation.append("Monte Carlo perturbation was recorded, so robustness evidence is available.")
    else:
        interpretation.append("No Monte Carlo perturbation evidence is available; kinetic uncertainty should be interpreted conservatively.")
    return interpretation


def _next_checks(
    readouts: dict[str, Any],
    burden: dict[str, Any],
    stability: dict[str, Any],
    coverage: list[str],
    topology: dict[str, Any],
) -> list[str]:
    checks = []
    if any("OFF-state" in warning or "ON/OFF" in warning for warning in coverage):
        checks.append("Add OFF-state or truth-table-sweep simulations to estimate leakage and ON/OFF ratio.")
    if not stability.get("uncertainty_evaluated"):
        checks.append("Increase Monte Carlo samples to evaluate parameter sensitivity.")
    if burden.get("burden_risk_level") in {"moderate", "high"}:
        checks.append("Compare against a lower gate-count or lower-expression topology to reduce resource burden.")
    if readouts.get("steady_state_reached") is False:
        checks.append("Extend the simulation time window to verify steady-state expression.")
    if topology.get("input_scenario") is None:
        checks.append("Record an explicit input scenario before using ODE results for biological claims.")
    if not checks:
        checks.append("Compare this candidate against alternative topologies under the same input scenario.")
    return checks


def _summary(readouts: dict[str, Any], burden: dict[str, Any], stability: dict[str, Any]) -> str:
    peak = readouts.get("peak_output_protein")
    time_to_peak = readouts.get("time_to_peak")
    burden_risk = burden.get("burden_risk_level")
    uncertainty = "with" if stability.get("uncertainty_evaluated") else "without"
    return (
        f"Peak output protein is {peak} a.u. at {time_to_peak} s; "
        f"burden risk is {burden_risk}; interpreted {uncertainty} Monte Carlo uncertainty evidence."
    )


def _model_limitations() -> list[str]:
    return [
        "The ODE model is a reduced resource-aware screening model, not a calibrated in vivo prediction.",
        "Output protein values are arbitrary units unless explicitly calibrated.",
        "Copy number, growth dilution, and maturation are simplified approximations; toxicity feedback, codon usage, degradation tags, and condition-specific calibration remain incomplete.",
    ]


def _series(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    series = []
    for value in values:
        number = _number(value)
        if number is not None:
            series.append(number)
    return series


def _response_time(time: list[float], output: list[float], initial: float, peak: float) -> float | None:
    if not time or not output or peak <= initial:
        return None
    threshold = initial + 0.9 * (peak - initial)
    for point, value in zip(time, output):
        if value >= threshold:
            return round(point, 6)
    return None


def _steady_state_status(time: list[float], output: list[float]) -> bool | str:
    if len(time) < 5 or len(output) < 5:
        return "uncertain"
    window = max(3, len(output) // 10)
    recent = output[-window:]
    duration = max(time[-1] - time[-window], 1e-9)
    slope = abs(recent[-1] - recent[0]) / duration
    scale = max(abs(max(output) - min(output)), 1.0)
    return slope <= 0.01 * scale


def _time_of_max(time: list[float], values: list[float]) -> float | None:
    if not time or not values:
        return None
    index = max(range(min(len(time), len(values))), key=lambda idx: values[idx])
    return time[index]


def _burden_risk(max_rnap: float | None, max_ribosome: float | None, max_burden: float) -> str:
    occupancy = max(value for value in [max_rnap, max_ribosome, 0.0] if value is not None)
    if occupancy >= 0.80:
        return "high"
    if occupancy >= 0.60:
        return "moderate"
    if max_burden > 0:
        return "low"
    return "unknown"


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if abs(denominator) < 1e-9:
        return None
    return round(numerator / denominator, 6)


def _round_or_none(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), -float("inf")}:
        return None
    return number
