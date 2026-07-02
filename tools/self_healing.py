from __future__ import annotations

import math
from typing import Any


SELF_HEALING_ACTIONS = {
    "adjust_copy_number",
    "mutate_intergenic_spacer",
    "insert_insulator",
    "swap_part_by_affinity",
    "append_degradation_tag",
}
TARGETED_SELF_HEALING_ACTIONS = SELF_HEALING_ACTIONS - {"adjust_copy_number"}


def validate_self_healing_recommendation(
    topology: dict[str, Any],
    recommendation: Any,
) -> list[str]:
    if not isinstance(recommendation, dict):
        return ["recommendation must be a dictionary."]

    errors: list[str] = []
    action = recommendation.get("recommended_action")
    if action not in SELF_HEALING_ACTIONS:
        errors.append(f"unsupported recommended_action: {action!r}.")

    parameters = recommendation.get("parameters", {})
    if not isinstance(parameters, dict):
        errors.append("recommendation.parameters must be a dictionary.")
        parameters = {}

    target = recommendation.get("target_node")
    if action in TARGETED_SELF_HEALING_ACTIONS:
        if not isinstance(target, str) or not target.strip():
            errors.append(f"{action} requires a non-empty target_node.")
        else:
            known_targets = set((topology.get("rbs_sequences") or {}).keys())
            verilog = topology.get("verilog")
            if isinstance(verilog, str) and verilog.strip():
                from tools.ode_simulator import parse_verilog_netlist

                signals, _ = parse_verilog_netlist(verilog)
                known_targets.update(
                    name
                    for name, signal_type in signals.items()
                    if signal_type in {"wire", "output"}
                )
            if target not in known_targets:
                errors.append(f"target_node {target!r} is not present in the topology.")

    if action == "adjust_copy_number":
        try:
            scale = float(parameters.get("scale", 0.5))
        except (TypeError, ValueError):
            scale = float("nan")
        if not math.isfinite(scale) or scale <= 0.0:
            errors.append("adjust_copy_number requires a finite scale greater than zero.")
    elif action == "swap_part_by_affinity":
        affinity = str(parameters.get("affinity", "low")).lower()
        if affinity not in {"low", "medium", "high"}:
            errors.append("swap_part_by_affinity requires low, medium, or high affinity.")
    elif action == "append_degradation_tag":
        tag_type = str(parameters.get("tag_type", "LVA")).upper()
        if tag_type not in {"LVA", "AAV", "ASV"}:
            errors.append("append_degradation_tag requires an LVA, AAV, or ASV tag_type.")
    return errors


def adjust_copy_number(topology: dict[str, Any], scale: float) -> dict[str, Any]:
    """Scales plasmid copy number to trade off expression strength vs. retroactivity."""
    updated = dict(topology)
    current = float(updated.get("copy_number", 1.0))
    updated["copy_number"] = max(1.0, current * scale)
    return updated


def mutate_intergenic_sequence(topology: dict[str, Any], target_gene: str) -> dict[str, Any]:
    """Synonymously mutates the RBS spacer of the target gene to break hairpins."""
    updated = dict(topology)
    rbs_seqs = dict(updated.get("rbs_sequences", {}))

    if target_gene in rbs_seqs:
        seq = rbs_seqs[target_gene]
        # Standard Shine-Dalgarno is AGGAGG. Find it and mutate the spacer after it to be AT-rich
        sd_idx = seq.find("AGGAGG")
        if sd_idx != -1:
            prefix = seq[:sd_idx + 6]
            # Replace spacer with AT-rich nucleotides (e.g., AAAA)
            suffix = "AAAAATG"
            rbs_seqs[target_gene] = prefix + suffix
        else:
            # If no SD consensus is found, replace the entire sequence with a standard low-folding RBS
            rbs_seqs[target_gene] = "AGGAGGAAAAATG"

    updated["rbs_sequences"] = rbs_seqs
    return updated


def insert_insulator(topology: dict[str, Any], target_gene: str) -> dict[str, Any]:
    """Prepends a RiboJ insulator sequence upstream of the RBS for target_gene."""
    updated = dict(topology)
    rbs_seqs = dict(updated.get("rbs_sequences", {}))

    # Standard RiboJ sequence
    riboj_seq = "AGCTGTCACCGGATGTGCTTTCCGGTCTGATGAGTCCGTGAGGACGAAACAGCCTCTACAAATAATTTTGTTTAA"

    if target_gene in rbs_seqs:
        rbs_seqs[target_gene] = riboj_seq + rbs_seqs[target_gene]
    else:
        rbs_seqs[target_gene] = riboj_seq + "AGGAGGAAAAATG"

    updated["rbs_sequences"] = rbs_seqs
    return updated


def swap_part_by_affinity(topology: dict[str, Any], target_gene: str, affinity: str) -> dict[str, Any]:
    """Swaps promoter/RBS parameters for target_gene to adjust binding/translation affinity."""
    updated = dict(topology)
    params = dict(updated.get("biokinetic_parameters", {}))

    # Map affinity class to relative scaling factors
    factors = {
        "high": 5.0,
        "medium": 1.0,
        "low": 0.2
    }
    scale = factors.get(affinity.lower(), 1.0)

    # Scale translation rate parameter
    rbs_key = f"translation_rate_{target_gene}"
    if rbs_key in params:
        if isinstance(params[rbs_key], dict) and "value" in params[rbs_key]:
            params[rbs_key] = dict(params[rbs_key], value=params[rbs_key]["value"] * scale)
        else:
            params[rbs_key] = float(params[rbs_key]) * scale
    else:
        params[rbs_key] = {"value": 120.0 * scale, "unit": "hr-1"}

    updated["biokinetic_parameters"] = params
    return updated


def append_degradation_tag(topology: dict[str, Any], target_gene: str, tag_type: str = "LVA") -> dict[str, Any]:
    """Appends a degradation tag by increasing the protein degradation rate of target_gene."""
    updated = dict(topology)
    params = dict(updated.get("biokinetic_parameters", {}))

    # Tag types and degradation multiplier factors
    factors = {
        "LVA": 8.0,  # Fast degradation
        "AAV": 4.0,  # Medium degradation
        "ASV": 2.0   # Slow degradation
    }
    multiplier = factors.get(tag_type.upper(), 5.0)

    deg_key = f"protein_degradation_rate_{target_gene}"
    if deg_key in params:
        if isinstance(params[deg_key], dict) and "value" in params[deg_key]:
            params[deg_key] = dict(params[deg_key], value=params[deg_key]["value"] * multiplier)
        else:
            params[deg_key] = float(params[deg_key]) * multiplier
    else:
        # Default E. coli protein degradation rate is ~0.012 min-1 or 0.7 hr-1
        params[deg_key] = {"value": 0.7 * multiplier, "unit": "hr-1"}

    updated["biokinetic_parameters"] = params
    return updated


def run_self_healing_action(topology: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    """Targeted Repair Router that executes the programmatic self-healing action."""
    validation_errors = validate_self_healing_recommendation(topology, recommendation)
    if validation_errors:
        raise ValueError("Invalid self-healing recommendation: " + " ".join(validation_errors))

    action = recommendation.get("recommended_action")
    target = recommendation.get("target_node")
    params = recommendation.get("parameters", {})

    if action == "adjust_copy_number":
        scale = float(params.get("scale", 0.5))
        return adjust_copy_number(topology, scale)
    if action == "mutate_intergenic_spacer":
        return mutate_intergenic_sequence(topology, target)
    elif action == "insert_insulator":
        return insert_insulator(topology, target)
    elif action == "swap_part_by_affinity":
        affinity = str(params.get("affinity", "low"))
        return swap_part_by_affinity(topology, target, affinity)
    elif action == "append_degradation_tag":
        tag_type = str(params.get("tag_type", "LVA"))
        return append_degradation_tag(topology, target, tag_type)

    raise ValueError(f"Unsupported self-healing action: {action!r}.")
