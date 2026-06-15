from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PlanIssue:
    code: str
    message: str
    severity: str = "warning"
    subject_id: str | None = None


@dataclass
class AssemblyFragment:
    fragment_id: str
    name: str
    source_type: str
    sequence: str
    core_sequence: str
    left_adapter: str = ""
    right_adapter: str = ""
    circular: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssemblyJunction:
    junction_id: str
    left_fragment_id: str
    right_fragment_id: str
    junction_type: str
    sequence: str
    unique: bool
    direction_valid: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssemblyScar:
    scar_id: str
    junction_id: str
    sequence: str
    scar_type: str
    retained_in_product: bool
    note: str = ""


@dataclass
class RestrictionDigest:
    molecule_id: str
    enzyme: str
    recognition_site: str
    cut_positions: list[int]
    fragment_lengths: list[int]
    circular: bool


@dataclass
class AssemblyPlan:
    plan_id: str
    design_id: str
    plasmid_id: str
    method: str
    status: str
    backbone_id: str
    backbone_version: str
    insertion_region_id: str
    target_length: int
    target_checksum: str | None
    fragments: list[AssemblyFragment] = field(default_factory=list)
    junctions: list[AssemblyJunction] = field(default_factory=list)
    scars: list[AssemblyScar] = field(default_factory=list)
    digests: list[RestrictionDigest] = field(default_factory=list)
    issues: list[PlanIssue] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)
    method_details: dict[str, Any] = field(default_factory=dict)

    @property
    def blockers(self) -> list[PlanIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = [asdict(issue) for issue in self.blockers]
        return payload
