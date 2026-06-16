from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from schemas.sequence_analysis import SequenceAnalysisResult


SEQUENCE_OPTIMIZATION_SCHEMA_VERSION = "1.0.0"


@dataclass
class SequenceChange:
    position: int
    original: str
    optimized: str
    change_type: str = "substitution"


@dataclass
class SequenceOptimizationRequest:
    design_id: str
    objective: str = "sequence_quality_baseline"
    host_profile_id: str | None = None
    part_ids: list[str] = field(default_factory=list)
    optimized_sequences: dict[str, str] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SequenceOptimizationResult:
    status: str
    design_id: str
    part_id: str
    host_profile_id: str | None
    objective: str
    original_sequence: str | None
    optimized_sequence: str | None
    original_checksum: str | None
    optimized_checksum: str | None
    protein_preserved: bool | None
    constraints: dict[str, Any]
    before_analysis: SequenceAnalysisResult
    after_analysis: SequenceAnalysisResult | None = None
    changes: list[SequenceChange] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    tool_name: str = "sequence-optimization-evaluator"
    tool_version: str = "1.0.0"
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SEQUENCE_OPTIMIZATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
