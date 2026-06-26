from __future__ import annotations

from typing import Any
from copy import deepcopy
import numpy as np

from tools.ode_simulator import (
    BatchODESimulator,
    parse_verilog_netlist,
    _flatten_parameters,
    _infer_gene_count,
)
from schemas.host_profile import (
    HostProfile,
    apply_host_profile_to_topology,
    default_ecoli_profile,
    host_profile_from_dict,
)


PARAMETER_ALIASES = {
    "growth_dilution": "growth_rate_dilution",
    "km_ribo": "km_ribosome",
    "ribo_total": "ribosome_total",
}
SENSITIVITY_RESULT_SCHEMA_VERSION = "1.0.0"


def run_parameter_sweep(
    topology: dict[str, Any],
    parameter_name: str,
    sweep_values: list[float],
    host_profile_id: str | None = None,
    host_profiles: Any | None = None,
) -> dict[str, Any]:
    profile = _resolve_host_profile(host_profile_id, host_profiles)
    selected_parameter = _normalize_parameter_name(parameter_name)
        
    base_topology = apply_host_profile_to_topology(topology, profile)
    
    results = []
    for val in sweep_values:
        swept_topo = deepcopy(base_topology)
        
        # Inject parameter
        if "biokinetic_parameters" not in swept_topo:
            swept_topo["biokinetic_parameters"] = {}
        if "parameters" not in swept_topo["biokinetic_parameters"]:
            swept_topo["biokinetic_parameters"]["parameters"] = {}
            
        swept_topo["biokinetic_parameters"]["parameters"][selected_parameter] = {
            "value": val,
            "parameter_origin": "inferred",
            "confidence_category": "inferred",
            "data_boundary": "public",
            "source": f"sweep:{selected_parameter}={val}"
        }
        swept_topo["biokinetic_parameters"][selected_parameter] = val
        if selected_parameter == "copy_number":
            swept_topo["copy_number"] = val
            
        # Run simulation
        simulator = BatchODESimulator(monte_carlo_samples=1)
        sim_result = simulator.simulate_topology(swept_topo)
        
        results.append({
            "schema_version": SENSITIVITY_RESULT_SCHEMA_VERSION,
            "value": val,
            "dynamic_margin": sim_result.get("dynamic_margin", 0.0),
            "signal_to_noise_ratio": sim_result.get("signal_to_noise_ratio", 0.0),
            "kinetic_score": sim_result.get("kinetic_score", 0.0),
            "max_burden_nM": sim_result.get(
                "metrics_max_burden",
                sim_result.get("max_burden_nM", 0.0),
            ),
        })
        
    return {
        "report_type": "parameter_sensitivity_sweep",
        "schema_version": SENSITIVITY_RESULT_SCHEMA_VERSION,
        "parameter_name": selected_parameter,
        "requested_parameter_name": parameter_name,
        "host_profile_id": profile.profile_id,
        "sweep_values": sweep_values,
        "results": results
    }


def run_bifurcation_sweep(
    topology: dict[str, Any],
    input_name: str,
    input_values: list[float],
    host_profile_id: str | None = None,
    host_profiles: Any | None = None,
) -> dict[str, Any]:
    profile = _resolve_host_profile(host_profile_id, host_profiles)
        
    base_topology = apply_host_profile_to_topology(topology, profile)
    
    verilog = str(base_topology.get("verilog") or "")
    signals, deps = parse_verilog_netlist(verilog)
    dynamic_signals = [name for name in sorted(signals.keys()) if signals[name] in ("wire", "output")]
    gene_count = len(dynamic_signals)
    
    if gene_count == 0:
        fallback_count = _infer_gene_count(base_topology)
        signals = {f"G_{i}": "wire" for i in range(fallback_count)}
        signals["G_0"] = "input"
        signals[f"G_{fallback_count-1}"] = "output"
        deps = {f"G_{i}": ("not", [f"G_{i-1}"]) for i in range(1, fallback_count)}
        dynamic_signals = [name for name in sorted(signals.keys()) if signals[name] in ("wire", "output")]
        gene_count = len(dynamic_signals)
        
    output_signals = [name for name in sorted(signals.keys()) if signals[name] == "output"]
    target_output = output_signals[0] if output_signals else (dynamic_signals[-1] if dynamic_signals else None)
    target_idx = dynamic_signals.index(target_output) if target_output in dynamic_signals else -1
    
    biokinetic_parameters = base_topology.get("biokinetic_parameters", {})
    params = _flatten_parameters(biokinetic_parameters)
    params["promoter_resource_demand"] = max(1.0, params["km_rnap"] * 0.35)
    params["copy_number"] = float(base_topology.get("copy_number", params.get("copy_number", 1.0)))
    
    simulator = BatchODESimulator(monte_carlo_samples=1)
    t_eval = np.linspace(0.0, simulator.simulation_time, simulator.sample_count)
    
    results = []
    for val in input_values:
        row_params = params.copy()
        row_params[f"input_{input_name}"] = val
        
        simulation, result = simulator._run_single_simulation(signals, deps, row_params, t_eval)
        if result is not None and result.success:
            final_val = float(result.y[2 * gene_count + target_idx, -1]) if target_idx != -1 else 0.0
            max_burden = float(np.sum(result.y[:, -1]))  # Sum of all species at steady state
        else:
            final_val = 0.0
            max_burden = 0.0
            
        results.append({
            "schema_version": SENSITIVITY_RESULT_SCHEMA_VERSION,
            "input_value": val,
            "output_value": final_val,
            "burden_nM": max_burden,
        })
        
    return {
        "report_type": "bifurcation_sweep",
        "schema_version": SENSITIVITY_RESULT_SCHEMA_VERSION,
        "input_name": input_name,
        "host_profile_id": profile.profile_id,
        "target_output": target_output,
        "results": results
    }


def _normalize_parameter_name(parameter_name: str) -> str:
    selected = str(parameter_name or "").strip()
    return PARAMETER_ALIASES.get(selected, selected)


def _resolve_host_profile(
    host_profile_id: str | None,
    host_profiles: Any | None,
) -> HostProfile:
    profile = None
    if host_profiles and host_profile_id:
        if isinstance(host_profiles, dict):
            profile = host_profiles.get(host_profile_id)
        elif hasattr(host_profiles, "get"):
            profile = host_profiles.get(host_profile_id)
    if isinstance(profile, dict):
        profile = host_profile_from_dict(profile)
    if isinstance(profile, HostProfile):
        return profile
    return default_ecoli_profile()
