from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from schemas.design_ir import (
    DesignIR,
    DesignRevision,
    PartAssignment,
    ProvenanceRecord,
)
from tools.part_library import LibraryPart, PartLibrary


@dataclass
class ReplacementValidation:
    valid: bool
    target_part_id: str
    replacement_part_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)


@dataclass
class ReplacementResult:
    validation: ReplacementValidation
    design: DesignIR | None = None


def validate_replacement(
    design: DesignIR,
    *,
    target_part_id: str,
    replacement_part_id: str,
    library: PartLibrary,
) -> ReplacementValidation:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, str] = {}
    target = next((part for part in design.parts if part.id == target_part_id), None)
    replacement = library.get(replacement_part_id)

    if target is None:
        errors.append(f"Target part does not exist in design: {target_part_id}")
    if replacement is None:
        errors.append(f"Replacement part does not exist in library: {replacement_part_id}")
    if target is None or replacement is None:
        return ReplacementValidation(
            valid=False,
            target_part_id=target_part_id,
            replacement_part_id=replacement_part_id,
            errors=errors,
            warnings=warnings,
            checks=checks,
        )

    type_match = target.part_type.lower() == replacement.part_type.lower()
    checks["part_type"] = "pass" if type_match else "fail"
    if not type_match:
        errors.append(
            f"Part type mismatch: design requires {target.part_type}, "
            f"replacement is {replacement.part_type}."
        )

    design_hosts = {host.lower() for host in target.host_compatibility}
    replacement_hosts = {host.lower() for host in replacement.host_compatibility}
    host_match = not design_hosts or not replacement_hosts or bool(design_hosts & replacement_hosts)
    checks["host_compatibility"] = "pass" if host_match else "fail"
    if not host_match:
        errors.append("Replacement part is not compatible with the design host context.")

    gate_type = ""
    if target.assignment:
        gate_type = str(target.assignment.metadata.get("gate_type") or "").upper()
    gate_match = (
        not gate_type
        or not replacement.compatible_gate_types
        or gate_type in replacement.compatible_gate_types
    )
    checks["gate_compatibility"] = "pass" if gate_match else "fail"
    if not gate_match:
        errors.append(
            f"Replacement does not support the assigned {gate_type} gate role."
        )

    checks["sequence"] = "pass" if replacement.sequence else "warning"
    if not replacement.sequence:
        warnings.append("Replacement has no DNA sequence.")
    elif replacement.sequence_status != "validated":
        warnings.append(
            f"Replacement sequence status is {replacement.sequence_status}; "
            "it must not be treated as assembly-ready."
        )

    checks["evidence"] = (
        "warning" if library.evidence_level == "demo_only" else "pass"
    )
    if library.evidence_level == "demo_only":
        warnings.append("The selected part comes from a demonstration-only library.")

    if target.assignment and target.assignment.part_id == replacement.id:
        warnings.append("Replacement is identical to the currently assigned part.")

    return ReplacementValidation(
        valid=not errors,
        target_part_id=target_part_id,
        replacement_part_id=replacement_part_id,
        errors=errors,
        warnings=warnings,
        checks=checks,
    )


def replace_part_immutable(
    design: DesignIR,
    *,
    target_part_id: str,
    replacement_part_id: str,
    library: PartLibrary,
    created_by: str = "user",
) -> ReplacementResult:
    validation = validate_replacement(
        design,
        target_part_id=target_part_id,
        replacement_part_id=replacement_part_id,
        library=library,
    )
    if not validation.valid:
        return ReplacementResult(validation=validation)

    replacement = library.get(replacement_part_id)
    if replacement is None:
        return ReplacementResult(validation=validation)

    revised = deepcopy(design)
    target = next(part for part in revised.parts if part.id == target_part_id)
    old_snapshot = _part_snapshot(target)
    assignment = _assignment_for_replacement(target_part_id, replacement, library)
    target.name = replacement.name
    target.part_type = replacement.part_type
    target.sequence = replacement.sequence
    target.source = f"{library.library_id}@{library.version}"
    target.confidence = library.evidence_level
    target.host_compatibility = list(replacement.host_compatibility)
    target.assignment = assignment
    target.rationale = (
        f"Replaced through validated library operation with {replacement.id}."
    )

    revised.assignments = [
        item for item in revised.assignments if item.logic_node_id != target_part_id
    ] + [assignment]
    created_at = datetime.now(timezone.utc).isoformat()
    revised.provenance.append(
        ProvenanceRecord(
            id=f"provenance_{library.library_id}_{library.version}",
            source_type="part_library",
            source_uri=library.source_path,
            source_version=library.version,
            generated_by="replace_part_immutable",
            generated_at=created_at,
            metadata={
                "library_id": library.library_id,
                "evidence_level": library.evidence_level,
            },
        )
    )
    target.provenance_ids.append(revised.provenance[-1].id)
    parent_revision = revised.revision
    next_number = parent_revision.revision_number + 1
    revised.revision = DesignRevision(
        revision_id=f"revision_{next_number}",
        parent_revision_id=parent_revision.revision_id,
        revision_number=next_number,
        created_at=created_at,
        created_by=created_by,
        change_type="part_replacement",
        summary=f"Replaced {target_part_id} with {replacement.id}",
        changes=[
            {
                "operation": "replace_part",
                "target_part_id": target_part_id,
                "before": old_snapshot,
                "after": _part_snapshot(target),
            }
        ],
    )
    revised.validation_status["sequences"] = _sequence_coverage(revised)
    revised.validation_status["assembly_ready"] = "no"
    revised.warnings = list(dict.fromkeys(revised.warnings + validation.warnings))
    return ReplacementResult(validation=validation, design=revised)


def _assignment_for_replacement(
    target_part_id: str,
    part: LibraryPart,
    library: PartLibrary,
) -> PartAssignment:
    return PartAssignment(
        logic_node_id=target_part_id,
        part_id=part.id,
        part_name=part.name,
        part_type=part.part_type,
        library_id=library.library_id,
        sequence=part.sequence,
        evidence_source=library.source_path,
        confidence=None,
        metadata={
            "library_version": library.version,
            "sequence_status": part.sequence_status,
            "roles": list(part.roles),
            "compatible_gate_types": list(part.compatible_gate_types),
            "orthogonality_group": part.orthogonality_group,
            "burden_score": part.burden_score,
        },
    )


def _part_snapshot(part: Any) -> dict[str, Any]:
    return {
        "id": part.id,
        "name": part.name,
        "part_type": part.part_type,
        "sequence": part.sequence,
        "source": part.source,
        "assignment_part_id": part.assignment.part_id if part.assignment else None,
    }


def _sequence_coverage(design: DesignIR) -> str:
    count = sum(1 for part in design.parts if part.sequence)
    if not count:
        return "missing"
    if count == len(design.parts):
        return "complete"
    return "partial"
