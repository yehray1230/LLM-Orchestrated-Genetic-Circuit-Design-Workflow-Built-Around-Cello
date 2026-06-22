from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


READINESS_SCHEMA_VERSION = "1.0.0"
READINESS_STAGES = (
    "conceptual",
    "sequence_complete",
    "assembly_planned",
    "primer_ready",
    "sequence_optimized",
    "host_optimized",
    "expert_review_required",
)


@dataclass
class ReadinessFinding:
    code: str
    message: str
    source: str
    severity: str
    subject_id: str | None = None


@dataclass
class ReadinessResult:
    readiness_status: str
    computational_design_score: float | None
    domain_scores: dict[str, float | None]
    domain_applicability: dict[str, str]
    blockers: list[ReadinessFinding] = field(default_factory=list)
    warnings: list[ReadinessFinding] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)
    next_required_stage: str | None = None
    schema_version: str = READINESS_SCHEMA_VERSION
    evaluator: str = "readiness-evaluator"
    evaluator_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
