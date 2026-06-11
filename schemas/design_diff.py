from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from schemas.design_ir import BiologicalPart, DesignIR


@dataclass
class PartChange:
    part_id: str
    change_type: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None


@dataclass
class MetricChange:
    metric: str
    left: Any
    right: Any
    delta: float | None = None


@dataclass
class DesignDiff:
    left_design_id: str
    right_design_id: str
    part_changes: list[PartChange] = field(default_factory=list)
    construct_changes: list[dict[str, Any]] = field(default_factory=list)
    validation_changes: list[MetricChange] = field(default_factory=list)
    metric_changes: list[MetricChange] = field(default_factory=list)
    summary: str = ""
    recommendation: str = ""


def compare_designs(
    left: DesignIR,
    right: DesignIR,
    *,
    left_metrics: dict[str, Any] | None = None,
    right_metrics: dict[str, Any] | None = None,
) -> DesignDiff:
    left_parts = {part.id: part for part in left.parts}
    right_parts = {part.id: part for part in right.parts}
    part_changes: list[PartChange] = []
    for part_id in sorted(set(left_parts) | set(right_parts)):
        before = left_parts.get(part_id)
        after = right_parts.get(part_id)
        if before is None:
            part_changes.append(
                PartChange(part_id, "added", None, _part_comparison(after))
            )
        elif after is None:
            part_changes.append(
                PartChange(part_id, "removed", _part_comparison(before), None)
            )
        elif _part_comparison(before) != _part_comparison(after):
            part_changes.append(
                PartChange(
                    part_id,
                    "changed",
                    _part_comparison(before),
                    _part_comparison(after),
                )
            )

    left_constructs = {item.id: item.parts for item in left.constructs}
    right_constructs = {item.id: item.parts for item in right.constructs}
    construct_changes = [
        {
            "construct_id": construct_id,
            "left_parts": left_constructs.get(construct_id),
            "right_parts": right_constructs.get(construct_id),
        }
        for construct_id in sorted(set(left_constructs) | set(right_constructs))
        if left_constructs.get(construct_id) != right_constructs.get(construct_id)
    ]
    validation_changes = _mapping_changes(
        left.validation_status,
        right.validation_status,
    )
    metric_changes = _mapping_changes(
        left_metrics or {},
        right_metrics or {},
        numeric_delta=True,
    )
    summary = (
        f"{len(part_changes)} part changes, "
        f"{len(construct_changes)} construct changes, "
        f"{len(metric_changes)} metric changes."
    )
    return DesignDiff(
        left_design_id=left.design_id,
        right_design_id=right.design_id,
        part_changes=part_changes,
        construct_changes=construct_changes,
        validation_changes=validation_changes,
        metric_changes=metric_changes,
        summary=summary,
        recommendation=_recommend(metric_changes, part_changes),
    )


def _part_comparison(part: BiologicalPart | None) -> dict[str, Any] | None:
    if part is None:
        return None
    return {
        "name": part.name,
        "part_type": part.part_type,
        "source": part.source,
        "sequence_status": "available" if part.sequence else "missing",
        "assignment_part_id": part.assignment.part_id if part.assignment else None,
    }


def _mapping_changes(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    numeric_delta: bool = False,
) -> list[MetricChange]:
    changes = []
    for key in sorted(set(left) | set(right)):
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value == right_value:
            continue
        delta = None
        if numeric_delta:
            try:
                delta = round(float(right_value) - float(left_value), 10)
            except (TypeError, ValueError):
                delta = None
        changes.append(MetricChange(key, left_value, right_value, delta))
    return changes


def _recommend(
    metric_changes: list[MetricChange],
    part_changes: list[PartChange],
) -> str:
    score_change = next(
        (change for change in metric_changes if change.metric in {"score", "weighted_total_score"}),
        None,
    )
    if score_change and score_change.delta is not None:
        if score_change.delta > 0:
            return "Right candidate has the higher computational score; review its added part and assembly risks."
        if score_change.delta < 0:
            return "Left candidate has the higher computational score; keep the right candidate only if its part changes solve a specific constraint."
    if part_changes:
        return "Scores do not establish a winner; review the listed part substitutions and evidence levels."
    return "The compared designs are materially similar under the available fields."
