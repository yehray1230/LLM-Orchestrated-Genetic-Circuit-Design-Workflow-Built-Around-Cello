from __future__ import annotations

from typing import Any

from Bio.Seq import Seq

from exporters.sequence_utils import normalize_dna
from schemas.backbone_registry import sequence_checksum
from schemas.design_ir_v2 import DesignIRV2
from schemas.host_profile import HostProfile
from schemas.sequence_optimization import (
    SequenceChange,
    SequenceOptimizationRequest,
    SequenceOptimizationResult,
)
from tools.sequence_analyzer import analyze_part_sequence


def evaluate_sequence_optimization(
    design: DesignIRV2,
    request: SequenceOptimizationRequest,
) -> list[SequenceOptimizationResult]:
    selected = set(request.part_ids or [])
    results: list[SequenceOptimizationResult] = []
    for part in design.parts:
        if selected and part.id not in selected:
            continue
        before = analyze_part_sequence(part, host_organism=_host(design))
        optimized_sequence = normalize_dna(
            request.optimized_sequences.get(part.id)
        )
        after = None
        protein_preserved = None
        changes: list[SequenceChange] = []
        issues: list[dict[str, Any]] = []
        if optimized_sequence is None:
            status = "needs_review"
            issues.append(
                {
                    "code": "NO_OPTIMIZED_SEQUENCE",
                    "severity": "info",
                    "message": (
                        "No optimized sequence was supplied; this result records "
                        "the analysis baseline only."
                    ),
                }
            )
        else:
            replacement = _part_with_sequence(part, optimized_sequence)
            after = analyze_part_sequence(replacement, host_organism=_host(design))
            protein_preserved = _protein_preserved(
                part.part_type,
                part.sequence,
                optimized_sequence,
            )
            if part.part_type.lower() == "cds" and protein_preserved is False:
                issues.append(
                    {
                        "code": "PROTEIN_SEQUENCE_CHANGED",
                        "severity": "error",
                        "message": (
                            "Optimized CDS changes the translated protein sequence."
                        ),
                    }
                )

            # Calculate CAI and rare codon usage if part is CDS
            if part.part_type.lower() == "cds" and optimized_sequence:
                import math
                from schemas.host_profile import default_ecoli_profile, default_yeast_profile, default_mammalian_profile

                profile_id = request.host_profile_id or ""
                if "yeast" in profile_id.lower():
                    host_profile = default_yeast_profile()
                elif any(x in profile_id.lower() for x in ("mammalian", "human", "cho")):
                    host_profile = default_mammalian_profile()
                else:
                    host_profile = default_ecoli_profile()

                codons = [optimized_sequence[idx:idx+3] for idx in range(0, len(optimized_sequence), 3)]
                w_vals = []
                rare_codons_found = []
                rare_threshold = host_profile.rare_codon_threshold

                for c_idx, codon in enumerate(codons):
                    codon = codon.upper()
                    if len(codon) != 3:
                        continue
                    try:
                        amino_acid = str(Seq(codon).translate(to_stop=False))
                    except Exception:
                        continue
                    if amino_acid == "*":
                        continue

                    usage_table = host_profile.codon_usage.get(amino_acid, {})
                    f_val = usage_table.get(codon, 1.0)
                    max_f = max(usage_table.values()) if usage_table else 1.0
                    w_val = f_val / max_f if max_f > 0 else 1.0
                    w_vals.append(w_val)

                    if f_val < rare_threshold:
                        rare_codons_found.append({
                            "codon": codon,
                            "position": c_idx,
                            "amino_acid": amino_acid,
                            "frequency": f_val
                        })

                if w_vals:
                    cai = math.exp(sum(math.log(w) for w in w_vals) / len(w_vals))
                    L = len(w_vals)
                    if rare_codons_found:
                        issues.append({
                            "code": "RARE_CODONS_DETECTED",
                            "severity": "info",
                            "message": f"Detected {len(rare_codons_found)} rare codons in optimized CDS (cai: {cai:.3f}). These may restrict tRNA availability and lower translation speed.",
                            "details": {
                                "cai": round(cai, 4),
                                "rare_codon_count": len(rare_codons_found),
                                "rare_codon_fraction": round(len(rare_codons_found) / L, 4),
                                "rare_codons": rare_codons_found[:10]
                            }
                        })
                    else:
                        issues.append({
                            "code": "CODON_ADAPTATION_INFO",
                            "severity": "info",
                            "message": f"Codon Adaptation Index (CAI) is {cai:.3f} with 0 rare codons.",
                            "details": {
                                "cai": round(cai, 4),
                                "rare_codon_count": 0,
                                "rare_codon_fraction": 0.0
                            }
                        })

            changes = _sequence_changes(part.sequence, optimized_sequence)
            status = _optimization_status(after, issues)
        results.append(
            SequenceOptimizationResult(
                status=status,
                design_id=design.design_id,
                part_id=part.id,
                host_profile_id=request.host_profile_id,
                objective=request.objective,
                original_sequence=normalize_dna(part.sequence),
                optimized_sequence=optimized_sequence,
                original_checksum=_checksum_or_none(part.sequence),
                optimized_checksum=_checksum_or_none(optimized_sequence),
                protein_preserved=protein_preserved,
                constraints=request.constraints,
                before_analysis=before,
                after_analysis=after,
                changes=changes,
                issues=issues,
                provenance={
                    "dry_run": request.dry_run,
                    "source": "sequence-optimization-evaluate",
                },
            )
        )
    return results


def generate_host_optimized_sequences(
    design: DesignIRV2,
    host_profile: HostProfile,
    *,
    part_ids: list[str] | None = None,
    preserve_start_codon: bool = True,
    preserve_stop_codon: bool = True,
) -> dict[str, str]:
    selected = set(part_ids or [])
    generated: dict[str, str] = {}
    for part in design.parts:
        if selected and part.id not in selected:
            continue
        if part.part_type.lower() != "cds":
            continue
        sequence = normalize_dna(part.sequence)
        if not sequence:
            continue
        generated[part.id] = optimize_cds_for_host(
            sequence,
            host_profile,
            preserve_start_codon=preserve_start_codon,
            preserve_stop_codon=preserve_stop_codon,
        )
    return generated


def optimize_cds_for_host(
    sequence: str,
    host_profile: HostProfile,
    *,
    preserve_start_codon: bool = True,
    preserve_stop_codon: bool = True,
) -> str:
    normalized = normalize_dna(sequence)
    if not normalized or len(normalized) % 3:
        return normalized or ""
    codons = [
        normalized[index : index + 3]
        for index in range(0, len(normalized), 3)
    ]
    optimized = list(codons)
    forbidden = [motif.upper() for motif in host_profile.forbidden_motifs]
    for index, codon in enumerate(codons):
        if preserve_start_codon and index == 0:
            continue
        if preserve_stop_codon and index == len(codons) - 1:
            continue
        amino_acid = str(Seq(codon).translate(to_stop=False))
        if amino_acid == "*":
            continue
        candidates = _ranked_codons(host_profile, amino_acid, fallback=codon)
        optimized[index] = _select_codon(
            optimized,
            index,
            candidates,
            forbidden,
        )
    return "".join(optimized)


def _part_with_sequence(part: Any, sequence: str) -> Any:
    replacement = type(part)(**part.__dict__)
    replacement.sequence = sequence
    return replacement


def _protein_preserved(
    part_type: str,
    original: str | None,
    optimized: str | None,
) -> bool | None:
    if part_type.lower() != "cds" or not original or not optimized:
        return None
    original_sequence = normalize_dna(original)
    optimized_sequence = normalize_dna(optimized)
    if (
        not original_sequence
        or not optimized_sequence
        or len(original_sequence) % 3
        or len(optimized_sequence) % 3
    ):
        return False
    return str(Seq(original_sequence).translate(to_stop=False)) == str(
        Seq(optimized_sequence).translate(to_stop=False)
    )


def _sequence_changes(
    original: str | None,
    optimized: str,
) -> list[SequenceChange]:
    original_sequence = normalize_dna(original) or ""
    changes: list[SequenceChange] = []
    shared = min(len(original_sequence), len(optimized))
    for index in range(shared):
        if original_sequence[index] != optimized[index]:
            changes.append(
                SequenceChange(
                    position=index + 1,
                    original=original_sequence[index],
                    optimized=optimized[index],
                )
            )
    if len(original_sequence) != len(optimized):
        changes.append(
            SequenceChange(
                position=shared + 1,
                original=original_sequence[shared:],
                optimized=optimized[shared:],
                change_type="length_change",
            )
        )
    return changes


def _optimization_status(
    after: Any,
    issues: list[dict[str, Any]],
) -> str:
    if after.status == "blocked" or any(
        issue.get("severity") == "error" for issue in issues
    ):
        return "blocked"
    if after.status == "warning" or any(
        issue.get("severity") in ("warning", "error") for issue in issues
    ):
        return "needs_review"
    return "passed"


def _checksum_or_none(sequence: str | None) -> str | None:
    normalized = normalize_dna(sequence)
    if not normalized:
        return None
    try:
        return sequence_checksum(normalized)
    except ValueError:
        return None


def _host(design: DesignIRV2) -> str | None:
    value = design.biological_context.host_organism.value
    text = "" if value is None else str(value).strip()
    return text or None


def _ranked_codons(
    host_profile: HostProfile,
    amino_acid: str,
    *,
    fallback: str,
) -> list[str]:
    usage = host_profile.codon_usage.get(amino_acid)
    if not usage:
        return [fallback]
    ranked = sorted(
        usage.items(),
        key=lambda item: (-float(item[1]), item[0]),
    )
    codons = [codon for codon, _ in ranked]
    return codons or [fallback]


def _select_codon(
    codons: list[str],
    index: int,
    candidates: list[str],
    forbidden: list[str],
) -> str:
    original = codons[index]
    for candidate in candidates:
        tentative = list(codons)
        tentative[index] = candidate
        sequence = "".join(tentative)
        if not any(motif in sequence for motif in forbidden):
            return candidate
    return original
