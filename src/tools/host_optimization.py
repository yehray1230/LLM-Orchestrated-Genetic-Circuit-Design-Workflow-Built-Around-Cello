from __future__ import annotations

import math
from statistics import mean
from typing import Any
from uuid import uuid4

from exporters.sequence_utils import normalize_dna
from schemas.design_ir_v2 import DesignIRV2
from schemas.host_optimization import (
    ExperimentalMeasurement,
    HostCalibrationResult,
    HostOptimizationCandidate,
    HostOptimizationResult,
)
from schemas.host_profile import HostProfile
from tools.sequence_analyzer import analyze_part_sequence
from tools.sequence_optimization import generate_host_optimized_sequences



DEFAULT_OBJECTIVE_WEIGHTS = {
    "expression": 0.35,
    "low_burden": 0.30,
    "sequence_quality": 0.20,
    "stability": 0.15,
}


def rank_host_optimization_candidates(
    design: DesignIRV2,
    host_profile: HostProfile,
    *,
    part_ids: list[str] | None = None,
    objective_weights: dict[str, float] | None = None,
) -> HostOptimizationResult:
    weights = _normalized_weights(objective_weights or DEFAULT_OBJECTIVE_WEIGHTS)
    optimized_sequences = generate_host_optimized_sequences(
        design,
        host_profile,
        part_ids=part_ids,
    )
    if not optimized_sequences:
        return HostOptimizationResult(
            status="blocked",
            design_id=design.design_id,
            host_profile_id=host_profile.profile_id,
            objective_weights=weights,
            candidates=[],
            limitations=[
                "No CDS sequence was available for host optimization candidate ranking."
            ],
        )

    candidates = [
        _candidate(
            design,
            host_profile,
            candidate_id="host_candidate_high_expression",
            strategy="high_expression",
            sequence_overrides=optimized_sequences,
            settings={
                "copy_number_class": "medium_high",
                "promoter_strength": "strong",
                "rbs_strength": "strong",
            },
            weights=weights,
        ),
        _candidate(
            design,
            host_profile,
            candidate_id="host_candidate_low_burden",
            strategy="low_burden",
            sequence_overrides=_low_burden_sequences(design, optimized_sequences),
            settings={
                "copy_number_class": "low_medium",
                "promoter_strength": "moderate",
                "rbs_strength": "moderate",
            },
            weights=weights,
        ),
        _candidate(
            design,
            host_profile,
            candidate_id="host_candidate_balanced",
            strategy="balanced",
            sequence_overrides=optimized_sequences,
            settings={
                "copy_number_class": "medium",
                "promoter_strength": "moderate_strong",
                "rbs_strength": "moderate_strong",
            },
            weights=weights,
        ),
    ]
    candidates = sorted(candidates, key=lambda item: item.aggregate_score, reverse=True)
    return HostOptimizationResult(
        status="ready",
        design_id=design.design_id,
        host_profile_id=host_profile.profile_id,
        objective_weights=weights,
        candidates=candidates,
        selected_candidate_id=candidates[0].candidate_id,
        limitations=[
            "Scores are computational ranking signals, not calibrated in vivo expression predictions.",
            "Promoter, RBS, copy-number, toxicity, and growth effects require experimental calibration.",
        ],
    )


def summarize_host_calibration(
    *,
    calibration_id: str | None,
    design_id: str,
    host_profile_id: str | None,
    measurements: list[ExperimentalMeasurement],
) -> HostCalibrationResult:
    selected_id = calibration_id or f"host_calibration_{uuid4().hex[:12]}"
    expression_values = [
        item.expression_value for item in measurements if item.expression_value is not None
    ]
    growth_values = [
        item.growth_rate for item in measurements if item.growth_rate is not None
    ]
    burden_values = [
        item.burden_value for item in measurements if item.burden_value is not None
    ]
    on_off_values = [
        item.on_off_ratio for item in measurements if item.on_off_ratio is not None
    ]
    summary = {
        "mean_expression": _mean_or_none(expression_values),
        "mean_growth_rate": _mean_or_none(growth_values),
        "mean_burden": _mean_or_none(burden_values),
        "mean_on_off_ratio": _mean_or_none(on_off_values),
        "coverage": {
            "expression": len(expression_values),
            "growth_rate": len(growth_values),
            "burden": len(burden_values),
            "on_off_ratio": len(on_off_values),
        },
    }
    recommendations = _calibration_recommendations(summary)
    status = "completed" if measurements and expression_values else "needs_more_data"
    return HostCalibrationResult(
        calibration_id=selected_id,
        status=status,
        design_id=design_id,
        host_profile_id=host_profile_id,
        measurement_count=len(measurements),
        summary=summary,
        recommendations=recommendations,
        measurements=measurements,
    )


def calculate_cai(sequence: str, host_profile: HostProfile) -> float:
    sequence = sequence.upper().strip()
    if len(sequence) < 3:
        return 0.0
    codons = [sequence[i:i+3] for i in range(0, len(sequence) - 2, 3)]
    if not codons:
        return 0.0
    
    codon_w = {}
    for aa, codon_freqs in host_profile.codon_usage.items():
        max_freq = max(codon_freqs.values()) if codon_freqs else 1.0
        if max_freq <= 0.0:
            max_freq = 1.0
        for codon, freq in codon_freqs.items():
            codon_w[codon.upper()] = freq / max_freq
            
    start_index = 0
    end_index = len(codons)
    
    if codons[0] in ("ATG", "GTG", "TTG"):
        start_index = 1
        
    last_codon = codons[-1]
    is_stop = False
    for aa, codon_freqs in host_profile.codon_usage.items():
        if aa == "*" and last_codon in codon_freqs:
            is_stop = True
            break
    if is_stop:
        end_index = len(codons) - 1
        
    eval_codons = codons[start_index:end_index]
    if not eval_codons:
        eval_codons = codons
        
    w_values = []
    for codon in eval_codons:
        w = codon_w.get(codon, 0.01)
        w_values.append(w)
        
    log_sum = sum(math.log(max(w, 1e-5)) for w in w_values)
    cai = math.exp(log_sum / len(w_values))
    return cai


def calculate_rare_codon_fraction(sequence: str, host_profile: HostProfile) -> float:
    sequence = sequence.upper().strip()
    if len(sequence) < 3:
        return 0.0
    codons = [sequence[i:i+3] for i in range(0, len(sequence) - 2, 3)]
    if not codons:
        return 0.0
        
    codon_freqs = {}
    for aa, freqs in host_profile.codon_usage.items():
        for codon, freq in freqs.items():
            codon_freqs[codon.upper()] = freq
            
    rare_count = 0
    for codon in codons:
        freq = codon_freqs.get(codon, 0.0)
        if freq < host_profile.rare_codon_threshold:
            rare_count += 1
            
    return rare_count / len(codons)


def align_rbs_to_sd(rbs_sequence: str) -> float:
    rbs_sequence = rbs_sequence.upper().strip()
    if not rbs_sequence:
        return 0.0
    target = "TAAGGAGG"
    n_target = len(target)
    n_rbs = len(rbs_sequence)
    
    max_matches = 0
    for offset in range(-n_target + 1, n_rbs):
        matches = 0
        for j in range(n_target):
            rbs_idx = offset + j
            if 0 <= rbs_idx < n_rbs:
                if target[j] == rbs_sequence[rbs_idx]:
                    matches += 1
        if matches > max_matches:
            max_matches = matches
    return max_matches / n_target


def _candidate(
    design: DesignIRV2,
    host_profile: HostProfile,
    *,
    candidate_id: str,
    strategy: str,
    sequence_overrides: dict[str, str],
    settings: dict[str, Any],
    weights: dict[str, float],
) -> HostOptimizationCandidate:
    sequence_quality = _sequence_quality_score(design, host_profile, sequence_overrides)
    
    cai_scores = []
    rare_codon_fractions = []
    
    for part in design.parts:
        if part.part_type.lower() == "cds":
            seq = sequence_overrides.get(part.id, part.sequence)
            if seq:
                seq = normalize_dna(seq)
                cai_scores.append(calculate_cai(seq, host_profile))
                rare_codon_fractions.append(calculate_rare_codon_fraction(seq, host_profile))
                
    cai = mean(cai_scores) if cai_scores else 1.0
    rare_codon_fraction = mean(rare_codon_fractions) if rare_codon_fractions else 0.0
    
    rbs_strengths = []
    for part in design.parts:
        if part.part_type.upper() == "RBS" or part.role.lower() == "rbs" or "rbs" in part.id.lower():
            seq = sequence_overrides.get(part.id, part.sequence)
            if seq:
                seq = normalize_dna(seq)
                rbs_strengths.append(align_rbs_to_sd(seq))
                
    if rbs_strengths:
        rbs_strength = mean(rbs_strengths)
    else:
        rbs_strength_setting = settings.get("rbs_strength", "moderate")
        if rbs_strength_setting == "strong":
            rbs_strength = 0.95
        elif rbs_strength_setting == "moderate_strong":
            rbs_strength = 0.85
        elif rbs_strength_setting == "moderate":
            rbs_strength = 0.70
        else:
            rbs_strength = 0.80

    promoter_setting = settings.get("promoter_strength", "moderate")
    if promoter_setting == "strong":
        promoter_factor = 1.2
        promoter_penalty = 0.15
    elif promoter_setting == "moderate_strong":
        promoter_factor = 1.0
        promoter_penalty = 0.08
    elif promoter_setting == "moderate":
        promoter_factor = 0.8
        promoter_penalty = 0.02
    else:
        promoter_factor = 1.0
        promoter_penalty = 0.05
        
    copy_number_setting = settings.get("copy_number_class", "medium")
    if copy_number_setting == "medium_high":
        copy_number_factor = 1.2
        copy_number_penalty = 0.15
    elif copy_number_setting == "medium":
        copy_number_factor = 1.0
        copy_number_penalty = 0.08
    elif copy_number_setting == "low_medium":
        copy_number_factor = 0.8
        copy_number_penalty = 0.02
    else:
        copy_number_factor = 1.0
        copy_number_penalty = 0.05

    expression = max(0.0, min(1.0, cai * promoter_factor * copy_number_factor * rbs_strength))
    low_burden = max(0.0, min(1.0, (1.0 - rare_codon_fraction) - copy_number_penalty - promoter_penalty))
    stability = max(0.0, min(1.0, sequence_quality - copy_number_penalty))

    objective_scores = {
        "expression": round(expression, 4),
        "low_burden": round(low_burden, 4),
        "sequence_quality": round(sequence_quality, 4),
        "stability": round(stability, 4),
    }
    aggregate = round(
        sum(objective_scores[key] * weights.get(key, 0.0) for key in objective_scores),
        4,
    )
    return HostOptimizationCandidate(
        candidate_id=candidate_id,
        strategy=strategy,
        status="ready",
        objective_scores=objective_scores,
        aggregate_score=aggregate,
        sequence_overrides=sequence_overrides,
        recommended_settings=settings,
        tradeoffs=_tradeoffs(strategy),
        warnings=_candidate_warnings(sequence_quality),
        metadata={
            "host_profile_id": host_profile.profile_id,
            "sequence_override_count": len(sequence_overrides),
        },
    )



def _sequence_quality_score(
    design: DesignIRV2,
    host_profile: HostProfile,
    sequence_overrides: dict[str, str],
) -> float:
    values: list[float] = []
    for part in design.parts:
        sequence = sequence_overrides.get(part.id, part.sequence)
        if not sequence:
            continue
        replacement = type(part)(**part.__dict__)
        replacement.sequence = sequence
        analysis = analyze_part_sequence(
            replacement,
            host_organism=host_profile.host_organism,
        )
        penalty = 0.0
        for issue in analysis.issues:
            penalty += 0.35 if issue.severity == "error" else 0.12
        values.append(max(0.0, 1.0 - penalty))
    return mean(values) if values else 0.0


def _low_burden_sequences(
    design: DesignIRV2,
    optimized_sequences: dict[str, str],
) -> dict[str, str]:
    # Low-burden keeps already clean CDSs unchanged and only applies sequence
    # overrides where optimization removes an analyzer warning/error.
    selected: dict[str, str] = {}
    for part in design.parts:
        optimized = optimized_sequences.get(part.id)
        original = normalize_dna(part.sequence)
        if not optimized or not original:
            continue
        before = analyze_part_sequence(part)
        replacement = type(part)(**part.__dict__)
        replacement.sequence = optimized
        after = analyze_part_sequence(replacement)
        if after.status != before.status or len(after.issues) < len(before.issues):
            selected[part.id] = optimized
    return selected


def _normalized_weights(weights: dict[str, float]) -> dict[str, float]:
    selected = {
        key: max(0.0, float(weights.get(key, 0.0)))
        for key in DEFAULT_OBJECTIVE_WEIGHTS
    }
    total = sum(selected.values())
    if total <= 0:
        return dict(DEFAULT_OBJECTIVE_WEIGHTS)
    return {key: round(value / total, 6) for key, value in selected.items()}


def _tradeoffs(strategy: str) -> list[str]:
    if strategy == "high_expression":
        return ["Higher expression priority may increase burden and toxicity risk."]
    if strategy == "low_burden":
        return ["Lower burden settings may reduce absolute output signal."]
    return ["Balanced candidate trades peak expression for lower implementation risk."]


def _candidate_warnings(sequence_quality: float) -> list[str]:
    if sequence_quality < 0.75:
        return ["Sequence quality warnings remain; review before construction."]
    return []


def _mean_or_none(values: list[float]) -> float | None:
    return round(mean(values), 6) if values else None


def _calibration_recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations = []
    coverage = dict(summary.get("coverage") or {})
    if coverage.get("growth_rate", 0) == 0:
        recommendations.append("Add growth-rate measurements to calibrate burden tradeoffs.")
    if coverage.get("on_off_ratio", 0) == 0:
        recommendations.append("Add ON/OFF ratio measurements to calibrate functional separation.")
    mean_burden = summary.get("mean_burden")
    if mean_burden is not None and float(mean_burden) > 0.7:
        recommendations.append("Measured burden is high; prioritize low-burden candidates.")
    if not recommendations:
        recommendations.append("Calibration coverage is sufficient for a first ranking update.")
    return recommendations
