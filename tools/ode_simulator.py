from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import numpy as np

try:
    from scipy.integrate import solve_ivp
except ModuleNotFoundError:
    solve_ivp = None

try:
    from joblib import Memory
except ModuleNotFoundError:
    Memory = None

from agents.data_miner_agent import DEFAULT_BIOKINETIC_PARAMETERS
from schemas.simulation import (
    SIMULATION_MODEL_VERSION,
    SimulationResult,
    parse_logic_value,
    simulation_spec_from_topology,
    stable_seed,
)
from schemas.state import DesignState


@dataclass
class WarmStartResourceSolver:
    rnap_free: float
    ribosome_free: float
    fixed_point_iterations: int = 5
    bisection_iterations: int = 18
    tolerance: float = 1e-6

    def solve_rnap(self, total: float, demands: np.ndarray, km: float) -> tuple[float, float]:
        free = self._solve(total, demands, km, self.rnap_free)
        self.rnap_free = free
        occupancy = 1.0 - free / max(total, 1e-9)
        return free, _clamp01(occupancy)

    def solve_ribosome(self, total: float, mrna: np.ndarray, km: float) -> tuple[float, float]:
        free = self._solve(total, np.maximum(mrna, 0.0), km, self.ribosome_free)
        self.ribosome_free = free
        occupancy = 1.0 - free / max(total, 1e-9)
        return free, _clamp01(occupancy)

    def _solve(self, total: float, demands: np.ndarray, km: float, warm_start: float) -> float:
        total = max(float(total), 1e-9)
        km = max(float(km), 1e-9)
        x = min(max(float(warm_start), 0.0), total)

        for _ in range(self.fixed_point_iterations):
            f_value, derivative = self._constraint(x, total, demands, km)
            if abs(f_value) <= self.tolerance * total:
                return x
            step = f_value / max(derivative, 1e-9)
            x = min(max(x - step, 0.0), total)

        lo, hi = 0.0, total
        for _ in range(self.bisection_iterations):
            mid = 0.5 * (lo + hi)
            f_mid, _ = self._constraint(mid, total, demands, km)
            if f_mid > 0.0:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)

    @staticmethod
    def _constraint(x: float, total: float, demands: np.ndarray, km: float) -> tuple[float, float]:
        denom = km + x
        bound = float(np.sum(demands * x / denom))
        derivative = 1.0 + float(np.sum(demands * km / (denom * denom)))
        return x + bound - total, derivative


def _strip_verilog_comments(verilog: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", verilog, flags=re.DOTALL)
    return re.sub(r"//.*", "", without_block)


def _clean_signal_name(value: str) -> str:
    value = re.sub(r"\b(?:input|output|wire|reg)\b", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\[[^\]]+\]", "", value)
    match = re.search(r"[A-Za-z_]\w*", value.strip())
    return match.group(0) if match else ""


def _extract_verilog_signals(code: str) -> tuple[set[str], set[str], set[str]]:
    signals: dict[str, set[str]] = {"input": set(), "output": set(), "wire": set()}
    for keyword in signals:
        for match in re.finditer(rf"\b{keyword}\b\s*(?:\[[^\]]+\]\s*)?([^;);]+)", code, flags=re.IGNORECASE):
            declaration = re.split(r"\b(?:input|output|wire|module|endmodule)\b", match.group(1), flags=re.IGNORECASE)[0]
            for name in re.split(r",", declaration):
                signal = _clean_signal_name(name)
                if signal:
                    signals[keyword].add(signal)
        for match in re.finditer(rf"\b{keyword}\b\s*(?:\[[^\]]+\]\s*)?([A-Za-z_]\w*)", code, flags=re.IGNORECASE):
            signals[keyword].add(match.group(1))
    return signals["input"], signals["output"], signals["wire"]


def parse_verilog_netlist(verilog: str) -> tuple[dict[str, str], dict[str, tuple[str, list[str]]]]:
    code = _strip_verilog_comments(verilog)
    inputs, outputs, wires = _extract_verilog_signals(code)

    signals = {}
    for inp in inputs:
        signals[inp] = "input"
    for out in outputs:
        signals[out] = "output"
    for w in wires:
        signals.setdefault(w, "wire")

    deps = {}

    # 1. Parse primitive gates
    for gate, body in re.findall(
        r"\b(and|or|not|nand|nor|xor|xnor|buf)\s+(?:[A-Za-z_]\w*\s*)?\(([^;]+?)\)\s*;",
        code,
        flags=re.IGNORECASE | re.DOTALL
    ):
        parts = [_clean_signal_name(p) for p in body.split(",") if p.strip()]
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            out_sig = parts[0]
            in_sigs = parts[1:]
            deps[out_sig] = (gate.lower(), in_sigs)
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            for sig in in_sigs:
                if sig not in signals:
                    signals[sig] = "wire"

    # 2. Parse assign statements
    for lhs, rhs in re.findall(
        r"\bassign\s+([^=;]+?)\s*=\s*([^;]+?)\s*;",
        code,
        flags=re.IGNORECASE | re.DOTALL
    ):
        out_sig = _clean_signal_name(lhs)
        if not out_sig:
            continue
        rhs_expr = rhs.strip()
        rhs_expr_clean = re.sub(r"\s+", "", rhs_expr)

        # NOR pattern
        nor_match = re.match(r"^[~!]\(([^|)]+)(?:\|\||\|)([^|)]+)\)$", rhs_expr_clean)
        if nor_match:
            in1 = _clean_signal_name(nor_match.group(1))
            in2 = _clean_signal_name(nor_match.group(2))
            deps[out_sig] = ("nor", [in1, in2])
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            continue

        # NAND pattern
        nand_match = re.match(r"^[~!]\(([^&)]+)(?:&&|&)([^&)]+)\)$", rhs_expr_clean)
        if nand_match:
            in1 = _clean_signal_name(nand_match.group(1))
            in2 = _clean_signal_name(nand_match.group(2))
            deps[out_sig] = ("nand", [in1, in2])
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            continue

        # NOT pattern
        not_match = re.match(r"^[~!]([A-Za-z_]\w*)$", rhs_expr_clean)
        if not_match:
            in1 = _clean_signal_name(not_match.group(1))
            deps[out_sig] = ("not", [in1])
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            continue

        # AND pattern
        and_match = re.match(r"^([A-Za-z_]\w*)(?:&&|&)([A-Za-z_]\w*)$", rhs_expr_clean)
        if and_match:
            in1 = _clean_signal_name(and_match.group(1))
            in2 = _clean_signal_name(and_match.group(2))
            deps[out_sig] = ("and", [in1, in2])
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            continue

        # OR pattern
        or_match = re.match(r"^([A-Za-z_]\w*)(?:\|\||\|)([A-Za-z_]\w*)$", rhs_expr_clean)
        if or_match:
            in1 = _clean_signal_name(or_match.group(1))
            in2 = _clean_signal_name(or_match.group(2))
            deps[out_sig] = ("or", [in1, in2])
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            continue

        # Buffer pattern
        buf_match = re.match(r"^([A-Za-z_]\w*)$", rhs_expr_clean)
        if buf_match:
            in1 = _clean_signal_name(buf_match.group(1))
            deps[out_sig] = ("buf", [in1])
            signals.setdefault(out_sig, "wire" if out_sig not in outputs else "output")
            continue

    for name in inputs:
        signals[name] = "input"
    for name in outputs:
        signals[name] = "output"

    return signals, deps


@dataclass
class ResourceAwareSimulation:
    signals: dict[str, str]
    deps: dict[str, tuple[str, list[str]]]
    params: dict[str, float]
    solver: WarmStartResourceSolver
    resource_trace: list[dict[str, float]] = field(default_factory=list)

    def __post_init__(self):
        self.dynamic_signals = [name for name in sorted(self.signals.keys()) if self.signals[name] in ("wire", "output")]
        self.signal_idx = {name: idx for idx, name in enumerate(self.dynamic_signals)}

    def rhs(self, _time: float, y: np.ndarray) -> np.ndarray:
        y = np.maximum(y, 0.0)
        n = len(self.dynamic_signals)
        mrna = y[:n]
        protein_immature = y[n:2*n]
        protein_mature = y[2*n:]

        protein_env = {}
        for name, sig_type in self.signals.items():
            if sig_type == "input":
                protein_env[name] = self.params.get(f"input_{name}", 0.0)
            else:
                idx = self.signal_idx.get(name)
                protein_env[name] = protein_mature[idx] if idx is not None else 0.0

        regulation = np.ones(n)
        promoter_demand = np.zeros(n)
        
        kd_vec = np.zeros(n)
        hill_vec = np.zeros(n)
        leak_vec = np.zeros(n)
        
        default_kd = self.params["kd"]
        default_hill = self.params["hill_coefficient"]
        default_leak = self.params["leak_fraction"]
        
        for idx, name in enumerate(self.dynamic_signals):
            kd_vec[idx] = self.params.get(f"kd_{name}", default_kd)
            hill_vec[idx] = self.params.get(f"hill_coefficient_{name}", default_hill)
            leak_vec[idx] = self.params.get(f"leak_fraction_{name}", default_leak)
            
        base_demand = self.params.get("promoter_resource_demand", max(1.0, self.params["km_rnap"] * 0.35))
        copy_number = self.params.get("copy_number", 1.0)

        for idx, name in enumerate(self.dynamic_signals):
            gate_type, gate_inputs = self.deps.get(name, (None, []))
            reg_val = 1.0

            kd = max(kd_vec[idx], 1e-9)
            hill = max(hill_vec[idx], 1.0)
            leak = max(0.0, min(1.0, leak_vec[idx]))

            if gate_type and gate_inputs:
                gate_type = gate_type.lower()
                if gate_type == "not" and len(gate_inputs) == 1:
                    rep_p = protein_env.get(gate_inputs[0], 0.0)
                    reg_val = leak + (1.0 - leak) / (1.0 + np.power(rep_p / kd, hill))
                elif gate_type == "nor" and len(gate_inputs) >= 1:
                    for inp in gate_inputs:
                        rep_p = protein_env.get(inp, 0.0)
                        reg_val *= (leak + (1.0 - leak) / (1.0 + np.power(rep_p / kd, hill)))
                elif gate_type == "nand" and len(gate_inputs) >= 1:
                    active_frac = 1.0
                    for inp in gate_inputs:
                        rep_p = protein_env.get(inp, 0.0)
                        active_frac *= (np.power(rep_p, hill) / (np.power(kd, hill) + np.power(rep_p, hill)))
                    reg_val = 1.0 - (1.0 - leak) * active_frac
                elif gate_type == "and" and len(gate_inputs) >= 1:
                    active_frac = 1.0
                    for inp in gate_inputs:
                        rep_p = protein_env.get(inp, 0.0)
                        active_frac *= (np.power(rep_p, hill) / (np.power(kd, hill) + np.power(rep_p, hill)))
                    reg_val = leak + (1.0 - leak) * active_frac
                elif gate_type == "or" and len(gate_inputs) >= 1:
                    inactive_frac = 1.0
                    for inp in gate_inputs:
                        rep_p = protein_env.get(inp, 0.0)
                        inactive_frac *= (1.0 - (np.power(rep_p, hill) / (np.power(kd, hill) + np.power(rep_p, hill))))
                    reg_val = leak + (1.0 - leak) * (1.0 - inactive_frac)
                elif gate_type in ("buf", "bufif1", "bufif0") and len(gate_inputs) == 1:
                    rep_p = protein_env.get(gate_inputs[0], 0.0)
                    reg_val = leak + (1.0 - leak) * (np.power(rep_p, hill) / (np.power(kd, hill) + np.power(rep_p, hill)))
                else:
                    if len(gate_inputs) == 1:
                        rep_p = protein_env.get(gate_inputs[0], 0.0)
                        reg_val = leak + (1.0 - leak) / (1.0 + np.power(rep_p / kd, hill))
                    else:
                        for inp in gate_inputs:
                            rep_p = protein_env.get(inp, 0.0)
                            reg_val *= (leak + (1.0 - leak) / (1.0 + np.power(rep_p / kd, hill)))

            regulation[idx] = reg_val
            promoter_demand[idx] = base_demand * reg_val * copy_number

        rnap_free, rnap_occupancy = self.solver.solve_rnap(
            self.params["rnap_total"], promoter_demand, self.params["km_rnap"]
        )
        ribo_free, ribo_occupancy = self.solver.solve_ribosome(
            self.params["ribosome_total"], mrna, self.params["km_ribosome"]
        )

        rnap_factor = rnap_free / (self.params["km_rnap"] + rnap_free)
        ribo_factor = ribo_free / (self.params["km_ribosome"] + ribo_free)

        mu_max = self.params.get("growth_rate_dilution", 0.0004)
        ribo_total = self.params.get("ribosome_total", 20000.0)
        mu = mu_max * (ribo_free / max(ribo_total, 1e-9))
        k_mat = self.params.get("maturation_rate", 0.0011)

        mrna_deg = np.zeros(n)
        protein_deg = np.zeros(n)
        default_mrna_deg = self.params["mrna_degradation_rate"]
        default_protein_deg = self.params["protein_degradation_rate"]
        for idx, name in enumerate(self.dynamic_signals):
            mrna_deg[idx] = self.params.get(f"mrna_degradation_rate_{name}", default_mrna_deg)
            protein_deg[idx] = self.params.get(f"protein_degradation_rate_{name}", default_protein_deg)

        d_mrna = (
            self.params["transcription_rate"] * copy_number * regulation * rnap_factor
            - (mrna_deg + mu) * mrna
        )
        d_protein_immature = (
            self.params["translation_rate"] * mrna * ribo_factor
            - (protein_deg + k_mat + mu) * protein_immature
        )
        d_protein_mature = (
            k_mat * protein_immature
            - (protein_deg + mu) * protein_mature
        )

        self.resource_trace.append(
            {
                "rnap_free": rnap_free,
                "ribosome_free": ribo_free,
                "rnap_occupancy": rnap_occupancy,
                "ribosome_occupancy": ribo_occupancy,
                "burden_nM": float(np.sum(mrna) + np.sum(protein_immature) + np.sum(protein_mature)),
            }
        )
        return np.concatenate([d_mrna, d_protein_immature, d_protein_mature])


class BatchODESimulator:
    def __init__(
        self,
        simulation_time: float = 600.0,
        sample_count: int = 80,
        monte_carlo_samples: int = 1,
        noise_fraction: float = 0.15,
        noise_level: float | None = None,
        cache_dir: str | None = None,
        random_seed: int | None = None,
    ):
        self.simulation_time = simulation_time
        self.sample_count = sample_count
        self.monte_carlo_samples = max(1, int(monte_carlo_samples))
        selected_noise = noise_fraction if noise_level is None else noise_level
        self.noise_fraction = max(0.0, float(selected_noise))
        self.random_seed = random_seed
        self._memory = Memory(cache_dir, verbose=0) if cache_dir and Memory is not None else None
        self._local_cache: dict[tuple, dict[str, Any]] = {}

    def run(self, state: DesignState) -> DesignState:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        topologies = node.candidate_topologies if node else state.candidate_topologies
        for index, topology in enumerate(topologies):
            self._simulate_topology(topology, index)
        if node:
            node.candidate_topologies = topologies
        state.candidate_topologies = topologies
        return state

    def simulate_topology(self, topology: dict[str, Any]) -> dict[str, Any]:
        selected = deepcopy(topology)
        self._simulate_topology(selected, 0)
        return selected

    def _simulate_topology(self, topology: dict[str, Any], index: int) -> None:
        verilog = str(topology.get("verilog") or "")
        signals, deps = parse_verilog_netlist(verilog)
        dynamic_signals = [name for name in sorted(signals.keys()) if signals[name] in ("wire", "output")]
        gene_count = len(dynamic_signals)

        if gene_count == 0:
            fallback_count = _infer_gene_count(topology)
            signals = {f"G_{i}": "wire" for i in range(fallback_count)}
            signals["G_0"] = "input"
            signals[f"G_{fallback_count-1}"] = "output"
            deps = {f"G_{i}": ("not", [f"G_{i-1}"]) for i in range(1, fallback_count)}
            dynamic_signals = [name for name in sorted(signals.keys()) if signals[name] in ("wire", "output")]
            gene_count = len(dynamic_signals)

        output_signals = [name for name in sorted(signals.keys()) if signals[name] == "output"]
        target_output = output_signals[0] if output_signals else (dynamic_signals[-1] if dynamic_signals else None)
        target_idx = dynamic_signals.index(target_output) if target_output in dynamic_signals else -1
        input_signals = [name for name in sorted(signals.keys()) if signals[name] == "input"]
        spec = simulation_spec_from_topology(
            topology,
            simulation_time=self.simulation_time,
            sample_count=self.sample_count,
            monte_carlo_samples=self.monte_carlo_samples,
            noise_fraction=self.noise_fraction,
            input_signals=input_signals,
            target_output=target_output,
            random_seed=self.random_seed,
        )

        truth_table = topology.get("truth_table") or topology.get("truth_table_or_logic_matrix") or topology.get("logic_matrix") or []
        if not isinstance(truth_table, list) or len(truth_table) == 0:
            default_row = {inp: 1 for inp in input_signals}
            default_row["Y"] = 1
            truth_table = [default_row]

        biokinetic_parameters = topology.get("biokinetic_parameters", {})
        params = _flatten_parameters(biokinetic_parameters)
        params["copy_number"] = spec.copy_number
        parameter_provenance = _parameter_provenance(biokinetic_parameters)
        params["promoter_resource_demand"] = max(1.0, params["km_rnap"] * 0.35)
        physical_assignment_metrics = _physical_assignment_metrics(topology)

        cache_key = _cache_key(
            topology,
            index,
            gene_count,
            params,
            self.simulation_time,
            self.sample_count,
            self.monte_carlo_samples,
            self.noise_fraction,
            spec.configuration_hash,
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            topology.update(deepcopy(cached))
            return

        t_eval = np.linspace(0.0, self.simulation_time, self.sample_count)
        all_row_metrics = []
        on_values = []
        off_values = []
        best_result = None
        best_resource_trace = None
        best_final_val = -1.0
        success = True
        error_msg = ""

        first_row = truth_table[0] if truth_table else {}
        output_key = None
        for key in ("Y", "OUT", "OUTPUT", "Z", "output", "out"):
            if key in first_row:
                output_key = key
                break
        if not output_key:
            other_keys = [k for k in first_row.keys() if k not in input_signals]
            output_key = other_keys[0] if other_keys else None

        for row in truth_table:
            row_params = params.copy()
            for inp in input_signals:
                val = row.get(inp, row.get(inp.upper(), row.get(inp.lower(), 1)))
                is_high = False
                if isinstance(val, str):
                    is_high = val.strip().lower() in ("1", "true", "yes", "high", "on")
                else:
                    is_high = bool(val)
                row_params[f"input_{inp}"] = 200.0 if is_high else 0.0

            simulation, result = self._run_single_simulation(signals, deps, row_params, t_eval)
            if result is None or not result.success:
                success = False
                error_msg = getattr(result, "message", "ODE simulation failed.")
                break

            row_metrics = _simulation_metrics(result.y, simulation.resource_trace, row_params, target_idx)
            all_row_metrics.append(row_metrics)

            final_val = float(result.y[2 * gene_count + target_idx, -1]) if target_idx != -1 else 0.0
            expected_out = parse_logic_value(row[output_key], True) if output_key is not None else True
            if expected_out:
                on_values.append(final_val)
            else:
                off_values.append(final_val)

            if final_val > best_final_val or best_result is None:
                best_final_val = final_val
                best_result = result
                best_resource_trace = simulation.resource_trace

        if not success or best_result is None:
            simulation_result = SimulationResult(
                status="failed",
                configuration_hash=spec.configuration_hash,
                parameter_set_hash=spec.parameter_set_hash,
                scenario_set_hash=spec.scenario_set_hash,
                error=error_msg,
                solver={"methods": spec.solver_methods},
            )
            updates = {
                "ode_status": "failed",
                "kinetic_score": 0.0,
                "robustness_score": 0.0,
                "signal_to_noise_ratio": 0.0,
                "monte_carlo_runs": self.monte_carlo_samples,
                "score": 0.0,
                "simulation_model_version": SIMULATION_MODEL_VERSION,
                "simulation_spec": spec.to_dict(),
                "simulation_result": simulation_result.to_dict(),
                "benchmark_report": {
                    "score": 0.0,
                    "robustness_score": 0.0,
                    "signal_to_noise_ratio": 0.0,
                    "monte_carlo_runs": self.monte_carlo_samples,
                    **physical_assignment_metrics,
                    "details": [{"metric": "kinetic", "status": "ode_failed", "error": error_msg}],
                },
            }
            topology.update(updates)
            self._set_cached(cache_key, updates)
            return

        max_burden = max(m["max_burden_nM"] for m in all_row_metrics)
        max_rnap_occ = max(m["rnap_occupancy_max"] for m in all_row_metrics)
        max_ribo_occ = max(m["ribosome_occupancy_max"] for m in all_row_metrics)
        min_rnap_free = min(m["rnap_free_min"] for m in all_row_metrics)
        min_ribo_free = min(m["ribosome_free_min"] for m in all_row_metrics)
        avg_cv = float(np.mean([m["output_cv"] for m in all_row_metrics]))
        avg_snr = float(np.mean([m["signal_to_noise_ratio"] for m in all_row_metrics]))

        min_on = min(on_values) if on_values else 0.0
        max_off = max(off_values) if off_values else 0.0
        dynamic_margin = min_on - max_off

        metrics = {
            "max_burden_nM": max_burden,
            "output_cv": avg_cv,
            "signal_to_noise_ratio": avg_snr,
            "dynamic_margin": dynamic_margin,
            "rnap_occupancy_max": max_rnap_occ,
            "ribosome_occupancy_max": max_ribo_occ,
            "rnap_free_min": min_rnap_free,
            "ribosome_free_min": min_ribo_free,
            "resource_capacity_factor": min(
                1.0,
                0.5 * params["rnap_total"] / DEFAULT_BIOKINETIC_PARAMETERS["rnap_total"]["value"]
                + 0.5 * params["ribosome_total"] / DEFAULT_BIOKINETIC_PARAMETERS["ribosome_total"]["value"],
            ),
            "burden_penalty": _sigmoid_penalty(max_burden, params["burden_soft_limit"], 0.00018),
            "toxicity_penalty": _sigmoid_penalty(max_burden, params["toxicity_threshold"], 0.00022),
        }

        ode_trace = _simulation_trace(t_eval, best_result.y, best_resource_trace, target_idx)
        if self.monte_carlo_samples > 1:
            metrics.update(self._monte_carlo_metrics(signals, deps, params, t_eval, target_idx, input_signals, truth_table))

        kinetic_score = _kinetic_score(metrics)
        robustness_score = kinetic_score
        base_score = float(topology.get("score", 0.65 + index * 0.02))
        final_score = max(0.0, min(1.0, 0.35 * base_score + 0.65 * kinetic_score))

        resource_occupancy = {
            "rnap_max": metrics["rnap_occupancy_max"],
            "ribosome_max": metrics["ribosome_occupancy_max"],
            "rnap_free_min": metrics["rnap_free_min"],
            "ribosome_free_min": metrics["ribosome_free_min"],
        }

        details = [
            {"metric": "kinetic", "score": kinetic_score},
            {"metric": "robustness", "score": robustness_score},
            {"metric": "signal_to_noise_ratio", "value": metrics["signal_to_noise_ratio"]},
            {"metric": "max_burden", "value": metrics["max_burden_nM"], "unit": "nM"},
            {"metric": "output_cv", "value": metrics["output_cv"]},
            {"metric": "resource_occupancy", "value": resource_occupancy},
            {"metric": "parameter_provenance", "value": parameter_provenance},
        ]
        if self.monte_carlo_samples > 1:
            details.append(
                {
                    "metric": "monte_carlo",
                    "samples": self.monte_carlo_samples,
                    "noise_fraction": self.noise_fraction,
                    "terminal_output_cv": metrics["monte_carlo_terminal_output_cv"],
                    "failure_rate": metrics["monte_carlo_failure_rate"],
                }
            )
        simulation_result = SimulationResult(
            status="simulated",
            configuration_hash=spec.configuration_hash,
            parameter_set_hash=spec.parameter_set_hash,
            scenario_set_hash=spec.scenario_set_hash,
            metrics=metrics,
            solver={"methods": spec.solver_methods},
        )
        updates = {
            "ode_status": "simulated",
            "gene_count": gene_count,
            "kinetic_score": kinetic_score,
            "robustness_score": robustness_score,
            "signal_to_noise_ratio": metrics["signal_to_noise_ratio"],
            "monte_carlo_runs": self.monte_carlo_samples,
            "score": final_score,
            "metrics_max_burden": metrics["max_burden_nM"],
            "metrics_cv": metrics["output_cv"],
            "dynamic_margin": metrics["dynamic_margin"],
            "ode_trace": ode_trace,
            "resource_occupancy": resource_occupancy,
            "parameter_provenance": parameter_provenance,
            "monte_carlo_samples": self.monte_carlo_samples,
            "monte_carlo_noise_fraction": self.noise_fraction,
            "simulation_model_version": SIMULATION_MODEL_VERSION,
            "simulation_spec": spec.to_dict(),
            "simulation_result": simulation_result.to_dict(),
            "benchmark_report": {
                "score": final_score,
                "robustness_score": robustness_score,
                "signal_to_noise_ratio": metrics["signal_to_noise_ratio"],
                "monte_carlo_runs": self.monte_carlo_samples,
                **physical_assignment_metrics,
                "details": details,
            },
        }
        if self.monte_carlo_samples > 1:
            updates["monte_carlo_failure_rate"] = metrics["monte_carlo_failure_rate"]
            updates["monte_carlo_terminal_output_cv"] = metrics["monte_carlo_terminal_output_cv"]
        topology.update(updates)
        self._set_cached(cache_key, updates)

    def _run_single_simulation(
        self,
        signals: dict[str, str],
        deps: dict[str, tuple[str, list[str]]],
        params: dict[str, float],
        t_eval: np.ndarray,
        initial_state: np.ndarray | None = None,
    ) -> tuple[ResourceAwareSimulation, Any]:
        solver = WarmStartResourceSolver(
            rnap_free=params["rnap_total"],
            ribosome_free=params["ribosome_total"],
        )
        simulation = ResourceAwareSimulation(signals=signals, deps=deps, params=params, solver=solver)
        gene_count = len(simulation.dynamic_signals)
        if initial_state is None:
            initial_state = np.zeros(gene_count * 3)
        return simulation, self._integrate(simulation, initial_state, t_eval)

    def simulate_noisy_response(
        self,
        topology: dict[str, Any],
        noise_level: float | None = None,
        rng: np.random.Generator | None = None,
    ) -> dict[str, float | bool | str]:
        verilog = str(topology.get("verilog") or "")
        signals, deps = parse_verilog_netlist(verilog)
        dynamic_signals = [name for name in sorted(signals.keys()) if signals[name] in ("wire", "output")]
        gene_count = len(dynamic_signals)

        if gene_count == 0:
            fallback_count = _infer_gene_count(topology)
            signals = {f"G_{i}": "wire" for i in range(fallback_count)}
            signals["G_0"] = "input"
            signals[f"G_{fallback_count-1}"] = "output"
            deps = {f"G_{i}": ("not", [f"G_{i-1}"]) for i in range(1, fallback_count)}
            dynamic_signals = [name for name in sorted(signals.keys()) if signals[name] in ("wire", "output")]
            gene_count = len(dynamic_signals)

        output_signals = [name for name in sorted(signals.keys()) if signals[name] == "output"]
        target_output = output_signals[0] if output_signals else (dynamic_signals[-1] if dynamic_signals else None)
        target_idx = dynamic_signals.index(target_output) if target_output in dynamic_signals else -1
        input_signals = [name for name in sorted(signals.keys()) if signals[name] == "input"]

        truth_table = topology.get("truth_table") or topology.get("truth_table_or_logic_matrix") or topology.get("logic_matrix") or []
        if not isinstance(truth_table, list) or len(truth_table) == 0:
            default_row = {inp: 1 for inp in input_signals}
            default_row["Y"] = 1
            truth_table = [default_row]

        params = _flatten_parameters(topology.get("biokinetic_parameters", {}))
        params["copy_number"] = float(topology.get("copy_number", 1.0))
        params["promoter_resource_demand"] = max(1.0, params["km_rnap"] * 0.35)

        sample_params = _perturb_biokinetic_parameters(
            params,
            self.noise_fraction if noise_level is None else max(0.0, float(noise_level)),
            rng or np.random.default_rng(),
        )

        on_values = []
        off_values = []
        first_row = truth_table[0] if truth_table else {}
        output_key = None
        for key in ("Y", "OUT", "OUTPUT", "Z", "output", "out"):
            if key in first_row:
                output_key = key
                break
        if not output_key:
            other_keys = [k for k in first_row.keys() if k not in input_signals]
            output_key = other_keys[0] if other_keys else None

        t_eval = np.linspace(0.0, self.simulation_time, self.sample_count)
        success = True
        error_msg = ""

        for row in truth_table:
            row_params = sample_params.copy()
            for inp in input_signals:
                val = row.get(inp, row.get(inp.upper(), row.get(inp.lower(), 1)))
                is_high = False
                if isinstance(val, str):
                    is_high = val.strip().lower() in ("1", "true", "yes", "high", "on")
                else:
                    is_high = bool(val)
                row_params[f"input_{inp}"] = 200.0 if is_high else 0.0

            simulation, result = self._run_single_simulation(signals, deps, row_params, t_eval)
            if result is None or not result.success:
                success = False
                error_msg = getattr(result, "message", "ODE simulation failed.")
                break

            final_val = float(result.y[2 * gene_count + target_idx, -1]) if target_idx != -1 else 0.0
            expected_out = parse_logic_value(row[output_key], True) if output_key is not None else True
            if expected_out:
                on_values.append(final_val)
            else:
                off_values.append(final_val)

        if not success:
            return {
                "success": False,
                "on_value": 0.0,
                "off_value": float("inf"),
                "error": error_msg,
            }

        min_on = min(on_values) if on_values else 0.0
        max_off = max(off_values) if off_values else 0.0

        return {
            "success": True,
            "on_value": min_on,
            "off_value": max_off,
            "signal_to_noise_ratio": min_on / max(max_off, 1e-9),
        }

    def _monte_carlo_metrics(
        self,
        signals: dict[str, str],
        deps: dict[str, tuple[str, list[str]]],
        params: dict[str, float],
        t_eval: np.ndarray,
        target_idx: int,
        input_signals: list[str],
        truth_table: list[dict[str, Any]],
    ) -> dict[str, float]:
        gene_count = len([s for s in signals if signals[s] in ("wire", "output")])
        rng = np.random.default_rng(
            self.random_seed
            if self.random_seed is not None
            else _stable_seed(gene_count, params, self.simulation_time, self.sample_count)
        )
        terminal_outputs: list[float] = []
        failures = 0
        perturbable = [
            "transcription_rate",
            "translation_rate",
            "kd",
            "hill_coefficient",
            "leak_fraction",
            "mrna_degradation_rate",
            "protein_degradation_rate",
            "y_min",
            "ymax",
            "y_max",
            "copy_number",
        ]

        first_row = truth_table[0] if truth_table else {}
        output_key = None
        for key in ("Y", "OUT", "OUTPUT", "Z", "output", "out"):
            if key in first_row:
                output_key = key
                break
        if not output_key:
            other_keys = [k for k in first_row.keys() if k not in input_signals]
            output_key = other_keys[0] if other_keys else None

        for _ in range(self.monte_carlo_samples):
            sample_params = _perturb_biokinetic_parameters(
                params,
                self.noise_fraction,
                rng,
                perturbable,
            )

            row_outputs = []
            row_expected = []

            for row in truth_table:
                row_params = sample_params.copy()
                for inp in input_signals:
                    val = row.get(inp, row.get(inp.upper(), row.get(inp.lower(), 1)))
                    is_high = False
                    if isinstance(val, str):
                        is_high = val.strip().lower() in ("1", "true", "yes", "high", "on")
                    else:
                        is_high = bool(val)
                    row_params[f"input_{inp}"] = 200.0 if is_high else 0.0

                simulation, result = self._run_single_simulation(signals, deps, row_params, t_eval)
                if result is None or not result.success:
                    continue

                final_val = float(result.y[2 * gene_count + target_idx, -1]) if target_idx != -1 else 0.0
                row_outputs.append(final_val)
                expected_out = parse_logic_value(row[output_key], True) if output_key is not None else True
                row_expected.append(expected_out)

            if len(row_outputs) < len(truth_table):
                failures += 1
                continue

            ons = [v for v, exp in zip(row_outputs, row_expected) if exp]
            offs = [v for v, exp in zip(row_outputs, row_expected) if not exp]

            if ons and offs:
                if min(ons) <= max(offs):
                    failures += 1

            terminal_outputs.append(row_outputs[-1] if row_outputs else 0.0)

        mean_output = float(np.mean(terminal_outputs)) if terminal_outputs else 0.0
        cv = float(np.std(terminal_outputs)) / max(mean_output, 1e-9) if terminal_outputs else 1.0
        return {
            "monte_carlo_terminal_output_cv": cv,
            "monte_carlo_failure_rate": failures / max(1, self.monte_carlo_samples),
        }

    def _integrate(
        self,
        simulation: ResourceAwareSimulation,
        initial_state: np.ndarray,
        t_eval: np.ndarray,
    ) -> Any:
        if solve_ivp is not None:
            for method in ("BDF", "Radau"):
                try:
                    result = solve_ivp(
                        simulation.rhs,
                        (0.0, self.simulation_time),
                        initial_state,
                        method=method,
                        t_eval=t_eval,
                        rtol=1e-5,
                        atol=1e-8,
                    )
                except Exception:
                    result = None
                if result is not None and result.success:
                    return result
        return _rk4_integrate(simulation.rhs, initial_state, t_eval)

    def _get_cached(self, key: tuple) -> dict[str, Any] | None:
        if self._memory is None:
            return deepcopy(self._local_cache.get(key))
        return _cached_lookup(self._memory, key, self._local_cache)

    def _set_cached(self, key: tuple, value: dict[str, Any]) -> None:
        self._local_cache[key] = deepcopy(value)


def _flatten_parameters(raw: dict[str, Any]) -> dict[str, float]:
    params = {key: float(value["value"]) for key, value in DEFAULT_BIOKINETIC_PARAMETERS.items()}
    records = raw.get("parameters", raw) if isinstance(raw, dict) else {}
    for key, value in records.items():
        if isinstance(value, dict) and "value" in value:
            try:
                params[key] = float(value["value"])
            except (TypeError, ValueError):
                continue
        else:
            try:
                params[key] = float(value)
            except (TypeError, ValueError):
                continue
    return params


def _parameter_provenance(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"source_summary": {"conservative_default": len(DEFAULT_BIOKINETIC_PARAMETERS)}, "unit_system": "nM and seconds"}
    summary = raw.get("mining_summary", {})
    if isinstance(summary, dict) and summary:
        return {
            "source_summary": summary.get("source_summary", {}),
            "records_used": summary.get("records_used", []),
            "all_parameters_have_external_source": summary.get("all_parameters_have_external_source", False),
            "unit_system": summary.get("unit_system", "nM and seconds"),
        }
    parameters = raw.get("parameters", raw)
    source_summary: dict[str, int] = {}
    if isinstance(parameters, dict):
        for parameter in parameters.values():
            source = parameter.get("source", "unknown") if isinstance(parameter, dict) else "unknown"
            source_summary[str(source)] = source_summary.get(str(source), 0) + 1
    return {"source_summary": source_summary, "unit_system": "nM and seconds"}


def _perturb_biokinetic_parameters(
    params: dict[str, float],
    noise_level: float,
    rng: np.random.Generator,
    perturbable: list[str] | None = None,
) -> dict[str, float]:
    sample_params = params.copy()
    keys = perturbable or [
        "transcription_rate",
        "translation_rate",
        "kd",
        "hill_coefficient",
        "leak_fraction",
        "mrna_degradation_rate",
        "protein_degradation_rate",
        "y_min",
        "ymax",
        "y_max",
        "copy_number",
    ]
    for key in keys:
        if key not in sample_params:
            continue
        original = float(sample_params[key])
        if key == "copy_number":
            if original > 0.0:
                cv = max(0.0, float(noise_level))
                s = math.sqrt(math.log(1.0 + cv * cv))
                sample_params[key] = original * math.exp(rng.normal(0.0, s) - 0.5 * s * s)
            else:
                sample_params[key] = 0.0
        else:
            sigma = abs(original) * max(0.0, float(noise_level))
            sample_params[key] = max(0.0, float(rng.normal(original, sigma)))
    return sample_params


def _rk4_integrate(rhs, initial_state: np.ndarray, t_eval: np.ndarray) -> Any:
    y = np.zeros((len(initial_state), len(t_eval)))
    y[:, 0] = initial_state
    current = initial_state.copy()
    for index in range(1, len(t_eval)):
        t0 = float(t_eval[index - 1])
        dt = float(t_eval[index] - t_eval[index - 1])
        k1 = rhs(t0, current)
        k2 = rhs(t0 + 0.5 * dt, np.maximum(current + 0.5 * dt * k1, 0.0))
        k3 = rhs(t0 + 0.5 * dt, np.maximum(current + 0.5 * dt * k2, 0.0))
        k4 = rhs(t0 + dt, np.maximum(current + dt * k3, 0.0))
        current = np.maximum(current + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4), 0.0)
        y[:, index] = current
    return SimpleNamespace(success=True, y=y, message="internal RK4 fallback")


def _infer_gene_count(topology: dict[str, Any]) -> int:
    if topology.get("biokinetic_parameters", {}).get("gene_count"):
        return max(1, int(topology["biokinetic_parameters"]["gene_count"]))
    if topology.get("gate_count"):
        return max(1, int(topology["gate_count"]))
    verilog = str(topology.get("verilog") or "")
    primitive_count = len(re.findall(r"\b(and|or|not|nand|nor|xor|xnor)\s*\(", verilog))
    assign_count = len(re.findall(r"\bassign\b", verilog))
    return max(1, primitive_count + assign_count)


def _simulation_metrics(
    y: np.ndarray,
    trace: list[dict[str, float]],
    params: dict[str, float],
    target_idx: int,
) -> dict[str, float]:
    gene_count = y.shape[0] // 3
    protein = np.maximum(y[2 * gene_count:, :], 0.0)
    output = protein[target_idx, :] if (protein.size and target_idx != -1) else np.zeros(y.shape[1])
    output_mean = float(np.mean(output))
    output_std = float(np.std(output))
    burden_values = [entry["burden_nM"] for entry in trace] or [0.0]
    rnap_occupancies = [entry["rnap_occupancy"] for entry in trace] or [0.0]
    ribo_occupancies = [entry["ribosome_occupancy"] for entry in trace] or [0.0]
    rnap_free = [entry["rnap_free"] for entry in trace] or [params["rnap_total"]]
    ribo_free = [entry["ribosome_free"] for entry in trace] or [params["ribosome_total"]]
    max_burden = float(max(burden_values))
    return {
        "max_burden_nM": max_burden,
        "output_cv": output_std / max(output_mean, 1e-9),
        "signal_to_noise_ratio": output_mean / max(output_std, 1e-9),
        "rnap_occupancy_max": float(max(rnap_occupancies)),
        "ribosome_occupancy_max": float(max(ribo_occupancies)),
        "rnap_free_min": float(min(rnap_free)),
        "ribosome_free_min": float(min(ribo_free)),
    }


def _simulation_trace(
    t_eval: np.ndarray,
    y: np.ndarray,
    trace: list[dict[str, float]],
    target_idx: int,
) -> dict[str, list[float]]:
    midpoint = y.shape[0] // 3
    mrna = np.maximum(y[:midpoint, :], 0.0)
    protein_immature = np.maximum(y[midpoint:2*midpoint, :], 0.0)
    protein_mature = np.maximum(y[2*midpoint:, :], 0.0)
    output = protein_mature[target_idx, :] if (protein_mature.size and target_idx != -1) else np.zeros(y.shape[1])
    sampled_trace = _resample_resource_trace(trace, len(t_eval))
    return {
        "time": _round_series(t_eval),
        "output_protein": _round_series(output),
        "total_mrna": _round_series(np.sum(mrna, axis=0) if mrna.size else np.zeros(len(t_eval))),
        "total_protein": _round_series(np.sum(protein_immature + protein_mature, axis=0) if (protein_immature.size or protein_mature.size) else np.zeros(len(t_eval))),
        "rnap_occupancy": _round_series([entry.get("rnap_occupancy", 0.0) for entry in sampled_trace]),
        "ribosome_occupancy": _round_series([entry.get("ribosome_occupancy", 0.0) for entry in sampled_trace]),
    }


def _resample_resource_trace(trace: list[dict[str, float]], target_count: int) -> list[dict[str, float]]:
    if target_count <= 0:
        return []
    if not trace:
        return [{"rnap_occupancy": 0.0, "ribosome_occupancy": 0.0} for _ in range(target_count)]
    if len(trace) == target_count:
        return trace
    if target_count == 1:
        return [trace[-1]]
    positions = np.linspace(0, len(trace) - 1, target_count)
    return [trace[int(round(position))] for position in positions]


def _round_series(values: Any) -> list[float]:
    array = np.asarray(values, dtype=float)
    return [round(float(value), 6) for value in array.tolist()]


def _kinetic_score(metrics: dict[str, float]) -> float:
    stability = 1.0 / (1.0 + metrics["output_cv"])
    if "monte_carlo_terminal_output_cv" in metrics:
        stability *= 1.0 / (1.0 + metrics["monte_carlo_terminal_output_cv"])
    resource_penalty = 1.0 - 0.5 * (metrics["rnap_occupancy_max"] + metrics["ribosome_occupancy_max"])
    failure_penalty = 1.0 - metrics.get("monte_carlo_failure_rate", 0.0)
    score = (
        0.4 * stability
        + 0.3 * metrics.get("burden_penalty", 1.0)
        + 0.3 * _clamp01(resource_penalty)
    )
    return _clamp01(score * failure_penalty * (0.35 + 0.65 * metrics["resource_capacity_factor"]))


def _sigmoid_penalty(value: float, soft_limit: float, steepness: float) -> float:
    exponent = steepness * (value - soft_limit)
    exponent = min(60.0, max(-60.0, exponent))
    return 1.0 / (1.0 + math.exp(exponent))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _coerce_float(value: Any, default: float) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
        return default
    return bool(value)


def _physical_assignment_metrics(topology: dict[str, Any]) -> dict[str, float | bool]:
    benchmark_report = topology.get("benchmark_report")
    if not isinstance(benchmark_report, dict):
        benchmark_report = {}
    return {
        "orthogonality_score": _coerce_float(
            topology.get("orthogonality_score", benchmark_report.get("orthogonality_score")),
            1.0,
        ),
        "cello_assignment_score": _coerce_float(
            topology.get("cello_assignment_score", benchmark_report.get("cello_assignment_score")),
            0.0,
        ),
        "cello_buildable": _coerce_bool(
            topology.get("cello_buildable", benchmark_report.get("cello_buildable")),
            False,
        ),
        "toxicity": _coerce_float(
            topology.get("toxicity", benchmark_report.get("toxicity")),
            0.0,
        ),
        "toxicity_score": _coerce_float(
            topology.get("toxicity_score", benchmark_report.get("toxicity_score")),
            1.0,
        ),
    }


def _cache_key(
    topology: dict[str, Any],
    index: int,
    gene_count: int,
    params: dict[str, float],
    simulation_time: float,
    sample_count: int,
    monte_carlo_samples: int,
    noise_fraction: float,
    configuration_hash: str = "",
) -> tuple:
    return (
        SIMULATION_MODEL_VERSION,
        configuration_hash,
        str(topology.get("verilog", "")),
        int(topology.get("gate_count", gene_count)),
        index,
        tuple(sorted((key, round(float(value), 9)) for key, value in params.items())),
        tuple(sorted(_physical_assignment_metrics(topology).items())),
        round(float(simulation_time), 6),
        int(sample_count),
        int(monte_carlo_samples),
        round(float(noise_fraction), 6),
    )


def _stable_seed(gene_count: int, params: dict[str, float], simulation_time: float, sample_count: int) -> int:
    return stable_seed(
        {
            "model_version": SIMULATION_MODEL_VERSION,
            "gene_count": gene_count,
            "parameters": {
                key: round(float(value), 6)
                for key, value in sorted(params.items())
            },
            "simulation_time": round(float(simulation_time), 6),
            "sample_count": sample_count,
        }
    )


def _cached_lookup(_memory, key: tuple, local_cache: dict[tuple, dict[str, Any]]) -> dict[str, Any] | None:
    return deepcopy(local_cache.get(key))
