from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SEQUENCE_ANALYSIS_SCHEMA_VERSION = "1.0.0"


@dataclass
class SequenceIssue:
    code: str
    severity: str
    message: str
    position: int | None = None
    subject_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SequenceAnalysisResult:
    status: str
    sequence_id: str
    part_type: str
    length_bp: int
    gc_percent: float | None
    checksum: str | None
    metrics: dict[str, Any] = field(default_factory=dict)
    issues: list[SequenceIssue] = field(default_factory=list)
    schema_version: str = SEQUENCE_ANALYSIS_SCHEMA_VERSION
    analyzer: str = "sequence-analyzer"
    analyzer_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DesignSequenceAnalysis:
    design_id: str
    status: str
    host_organism: str | None
    results: list[SequenceAnalysisResult]
    summary: dict[str, Any]
    schema_version: str = SEQUENCE_ANALYSIS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
