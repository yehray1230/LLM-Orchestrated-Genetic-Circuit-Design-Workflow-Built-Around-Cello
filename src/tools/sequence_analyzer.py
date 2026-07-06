from __future__ import annotations

from collections import Counter
import re
from typing import Any

from Bio.Seq import Seq

from exporters.sequence_utils import is_valid_iupac_dna, normalize_dna
from schemas.backbone_registry import sequence_checksum
from schemas.design_ir_v2 import BiologicalPartV2, DesignIRV2
from schemas.sequence_analysis import (
    DesignSequenceAnalysis,
    SequenceAnalysisResult,
    SequenceIssue,
)


STOP_CODONS = {"TAA", "TAG", "TGA"}
COMMON_RESTRICTION_SITES = {
    "EcoRI": ("GAATTC",),
    "BamHI": ("GGATCC",),
    "HindIII": ("AAGCTT",),
    "NotI": ("GCGGCCGC",),
    "PstI": ("CTGCAG",),
    "SpeI": ("ACTAGT",),
    "XbaI": ("TCTAGA",),
}
TYPE_IIS_SITES = {
    "BsaI": ("GGTCTC", "GAGACC"),
    "BsmBI": ("CGTCTC", "GAGACG"),
}


def analyze_design_sequences(
    design: DesignIRV2,
    *,
    part_ids: list[str] | None = None,
    window_size: int = 50,
    homopolymer_threshold: int = 6,
    repeat_length: int = 12,
) -> DesignSequenceAnalysis:
    selected = set(part_ids or [])
    results = [
        analyze_part_sequence(
            part,
            host_organism=_host(design),
            window_size=window_size,
            homopolymer_threshold=homopolymer_threshold,
            repeat_length=repeat_length,
        )
        for part in design.parts
        if not selected or part.id in selected
    ]
    issue_counts = Counter(
        issue.severity
        for result in results
        for issue in result.issues
    )
    status = _rollup_status(results)
    return DesignSequenceAnalysis(
        design_id=design.design_id,
        status=status,
        host_organism=_host(design),
        results=results,
        summary={
            "part_count": len(results),
            "blocked_count": sum(1 for item in results if item.status == "blocked"),
            "warning_count": issue_counts.get("warning", 0),
            "error_count": issue_counts.get("error", 0),
        },
    )


def analyze_part_sequence(
    part: BiologicalPartV2,
    *,
    host_organism: str | None = None,
    window_size: int = 50,
    homopolymer_threshold: int = 6,
    repeat_length: int = 12,
) -> SequenceAnalysisResult:
    sequence = normalize_dna(part.sequence)
    issues: list[SequenceIssue] = []
    if not sequence:
        issues.append(
            SequenceIssue(
                code="MISSING_SEQUENCE",
                severity="error",
                message=f"Part {part.id} has no sequence.",
                subject_id=part.id,
            )
        )
        return _result(part, "", None, {}, issues)
    if not is_valid_iupac_dna(sequence):
        issues.append(
            SequenceIssue(
                code="INVALID_IUPAC_DNA",
                severity="error",
                message=f"Part {part.id} contains non-IUPAC DNA symbols.",
                subject_id=part.id,
            )
        )

    metrics = _basic_metrics(sequence, window_size)
    issues.extend(
        _homopolymer_issues(
            sequence,
            part.id,
            threshold=homopolymer_threshold,
        )
    )
    issues.extend(_restriction_issues(sequence, part.id))
    issues.extend(
        _repeat_issues(
            sequence,
            part.id,
            repeat_length=repeat_length,
        )
    )
    if part.part_type.lower() == "cds":
        issues.extend(_cds_issues(sequence, part.id))
        issues.extend(internal_sd_issues(sequence, part.id))
        metrics["protein_length_aa"] = _protein_length(sequence)
        
        tag = detect_degradation_tags(sequence)
        metrics["degradation_tag"] = tag
        metrics["has_degradation_tag"] = tag is not None
        if tag is not None:
            issues.append(
                SequenceIssue(
                    code="DEGRADATION_TAG_DETECTED",
                    severity="info",
                    message=f"CDS {part.id} contains active degradation tag: {tag}.",
                    subject_id=part.id,
                    metadata={"tag": tag},
                )
            )

    compatible = {item.lower() for item in part.host_compatibility}
    if host_organism and compatible and host_organism.lower() not in compatible:
        issues.append(
            SequenceIssue(
                code="HOST_COMPATIBILITY",
                severity="warning",
                message=f"Part {part.id} is not annotated for host {host_organism}.",
                subject_id=part.id,
            )
        )
    elif host_organism and not compatible:
        issues.append(
            SequenceIssue(
                code="HOST_COMPATIBILITY_UNANNOTATED",
                severity="warning",
                message=f"Part {part.id} has no host compatibility annotation.",
                subject_id=part.id,
            )
        )
    return _result(part, sequence, _safe_checksum(sequence), metrics, issues)


def _basic_metrics(sequence: str, window_size: int) -> dict[str, Any]:
    gc_percent = _gc_percent(sequence)
    windows = _window_gc(sequence, window_size)
    restriction_count = sum(
        len(_motif_positions(sequence, motif))
        for motifs in COMMON_RESTRICTION_SITES.values()
        for motif in motifs
    )
    type_iis_count = sum(
        len(_motif_positions(sequence, motif))
        for motifs in TYPE_IIS_SITES.values()
        for motif in motifs
    )
    return {
        "gc_percent": gc_percent,
        "min_window_gc_percent": min(windows) if windows else gc_percent,
        "max_window_gc_percent": max(windows) if windows else gc_percent,
        "homopolymer_max_run": _max_homopolymer_run(sequence),
        "restriction_site_count": restriction_count,
        "type_iis_site_count": type_iis_count,
    }


def _cds_issues(sequence: str, part_id: str) -> list[SequenceIssue]:
    issues: list[SequenceIssue] = []
    if len(sequence) % 3:
        issues.append(
            SequenceIssue(
                code="CDS_FRAME_LENGTH",
                severity="error",
                message=f"CDS {part_id} length is not divisible by three.",
                subject_id=part_id,
            )
        )
    if not sequence.startswith("ATG"):
        issues.append(
            SequenceIssue(
                code="CDS_START_CODON",
                severity="warning",
                message=f"CDS {part_id} does not start with ATG.",
                position=1,
                subject_id=part_id,
            )
        )
    if sequence[-3:] not in STOP_CODONS:
        issues.append(
            SequenceIssue(
                code="CDS_STOP_CODON",
                severity="warning",
                message=f"CDS {part_id} has no terminal stop codon.",
                position=max(1, len(sequence) - 2),
                subject_id=part_id,
            )
        )
    for index in range(3, max(3, len(sequence) - 3), 3):
        codon = sequence[index : index + 3]
        if codon in STOP_CODONS:
            issues.append(
                SequenceIssue(
                    code="CDS_INTERNAL_STOP",
                    severity="error",
                    message=f"CDS {part_id} contains an internal stop codon.",
                    position=index + 1,
                    subject_id=part_id,
                    metadata={"codon": codon},
                )
            )
    return issues


def internal_sd_issues(sequence: str, part_id: str) -> list[SequenceIssue]:
    issues: list[SequenceIssue] = []
    sd_motifs = ["AGGAGG", "GAGGAG", "GGAGG", "AGGAG"]
    reported_positions = set()
    for motif in sd_motifs:
        for match in re.finditer(f"(?={motif})", sequence):
            pos = match.start() + 1
            if pos in reported_positions:
                continue
            reported_positions.add(pos)
            issues.append(
                SequenceIssue(
                    code="INTERNAL_SD_SITE",
                    severity="warning",
                    message=(
                        f"CDS contains internal Shine-Dalgarno-like sequence '{motif}' "
                        f"at position {pos} which could cause ribosome stalling."
                    ),
                    position=pos,
                    subject_id=part_id,
                    metadata={"motif": motif},
                )
            )
    return issues


def detect_degradation_tags(sequence: str) -> str | None:
    if not sequence or len(sequence) % 3 != 0:
        return None
    try:
        translated = str(Seq(sequence).translate(to_stop=False)).upper().rstrip("*")
    except Exception:
        return None
    degradation_tags = {
        "ssrA_LVA": "AANDENYALAA",
        "ssrA_LAV": "AANDENYALAV",
        "ssrA_ASV": "AANDENYAASV",
    }
    for tag_name, peptide in degradation_tags.items():
        if translated.endswith(peptide):
            return tag_name
    return None


def _restriction_issues(sequence: str, part_id: str) -> list[SequenceIssue]:
    issues: list[SequenceIssue] = []
    for enzyme, motifs in {**COMMON_RESTRICTION_SITES, **TYPE_IIS_SITES}.items():
        for motif in motifs:
            for position in _motif_positions(sequence, motif):
                code = (
                    f"INTERNAL_{enzyme.upper()}_SITE"
                    if enzyme in TYPE_IIS_SITES
                    else "RESTRICTION_SITE"
                )
                issues.append(
                    SequenceIssue(
                        code=code,
                        severity="warning",
                        message=(
                            f"Sequence contains {enzyme} site at position "
                            f"{position}."
                        ),
                        position=position,
                        subject_id=part_id,
                        metadata={"enzyme": enzyme, "motif": motif},
                    )
                )
    return issues


def _homopolymer_issues(
    sequence: str,
    part_id: str,
    *,
    threshold: int,
) -> list[SequenceIssue]:
    issues: list[SequenceIssue] = []
    for match in re.finditer(r"(A+|C+|G+|T+)", sequence):
        if len(match.group(0)) >= threshold:
            issues.append(
                SequenceIssue(
                    code="HOMOPOLYMER_RUN",
                    severity="warning",
                    message=(
                        f"Sequence contains a homopolymer run of "
                        f"{len(match.group(0))} bases."
                    ),
                    position=match.start() + 1,
                    subject_id=part_id,
                    metadata={"base": match.group(0)[0], "length": len(match.group(0))},
                )
            )
    return issues


def _repeat_issues(
    sequence: str,
    part_id: str,
    *,
    repeat_length: int,
) -> list[SequenceIssue]:
    if len(sequence) < repeat_length * 2:
        return []
    issues: list[SequenceIssue] = []
    seen: dict[str, int] = {}
    for index in range(0, len(sequence) - repeat_length + 1):
        window = sequence[index : index + repeat_length]
        if window in seen and index - seen[window] >= repeat_length:
            issues.append(
                SequenceIssue(
                    code="DIRECT_REPEAT",
                    severity="warning",
                    message=f"Sequence contains repeated {repeat_length} bp motif.",
                    position=seen[window] + 1,
                    subject_id=part_id,
                    metadata={"repeat_position": index + 1, "motif": window},
                )
            )
            break
        seen.setdefault(window, index)
    for index in range(0, len(sequence) - repeat_length + 1):
        window = sequence[index : index + repeat_length]
        reverse = str(Seq(window).reverse_complement())
        other = sequence.find(reverse, index + repeat_length)
        if other >= 0:
            issues.append(
                SequenceIssue(
                    code="INVERTED_REPEAT",
                    severity="warning",
                    message=(
                        f"Sequence contains inverted {repeat_length} bp repeat."
                    ),
                    position=index + 1,
                    subject_id=part_id,
                    metadata={"repeat_position": other + 1, "motif": window},
                )
            )
            break
    return issues


def _result(
    part: BiologicalPartV2,
    sequence: str,
    checksum: str | None,
    metrics: dict[str, Any],
    issues: list[SequenceIssue],
) -> SequenceAnalysisResult:
    gc_percent = _gc_percent(sequence) if sequence else None
    return SequenceAnalysisResult(
        status=_status(issues),
        sequence_id=part.id,
        part_type=part.part_type,
        length_bp=len(sequence),
        gc_percent=gc_percent,
        checksum=checksum,
        metrics=metrics,
        issues=issues,
    )


def _motif_positions(sequence: str, motif: str) -> list[int]:
    return [
        match.start() + 1
        for match in re.finditer(f"(?={re.escape(motif)})", sequence)
    ]


def _gc_percent(sequence: str) -> float:
    if not sequence:
        return 0.0
    return round(100.0 * (sequence.count("G") + sequence.count("C")) / len(sequence), 4)


def _window_gc(sequence: str, window_size: int) -> list[float]:
    size = min(max(1, window_size), len(sequence))
    if not sequence:
        return []
    return [
        _gc_percent(sequence[index : index + size])
        for index in range(0, len(sequence) - size + 1)
    ]


def _max_homopolymer_run(sequence: str) -> int:
    return max((len(match.group(0)) for match in re.finditer(r"(A+|C+|G+|T+)", sequence)), default=0)


def _protein_length(sequence: str) -> int | None:
    if len(sequence) % 3:
        return None
    translated = str(Seq(sequence).translate(to_stop=False))
    return len(translated.rstrip("*"))


def _safe_checksum(sequence: str) -> str | None:
    try:
        return sequence_checksum(sequence)
    except ValueError:
        return None


def _status(issues: list[SequenceIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "blocked"
    if issues:
        return "warning"
    return "passed"


def _rollup_status(results: list[SequenceAnalysisResult]) -> str:
    if any(result.status == "blocked" for result in results):
        return "blocked"
    if any(result.status == "warning" for result in results):
        return "warning"
    return "passed"


def _host(design: DesignIRV2) -> str | None:
    value = design.biological_context.host_organism.value
    text = "" if value is None else str(value).strip()
    return text or None
