from __future__ import annotations

from copy import deepcopy
from typing import Any


PARAMETER_ORIGINS = {"measured", "literature", "inferred", "default", "unknown"}
CONFIDENCE_CATEGORIES = {"measured", "literature", "inferred", "default", "unknown"}
DATA_BOUNDARIES = {"public", "local_private", "unknown"}


def normalize_parameter_metadata(
    parameter: dict[str, Any],
    *,
    default_origin: str = "unknown",
    default_context: dict[str, Any] | None = None,
    is_override: bool = False,
) -> dict[str, Any]:
    normalized = deepcopy(parameter)
    source = str(normalized.get("source") or "unknown").strip() or "unknown"
    origin = _origin(
        normalized.get("parameter_origin"),
        source=source,
        default_origin=default_origin,
    )
    confidence = _confidence(normalized.get("confidence"))
    confidence_category = _confidence_category(
        normalized.get("confidence_category"),
        source=source,
        origin=origin,
        confidence=confidence,
    )
    measurement_context = normalized.get("measurement_context")
    if not isinstance(measurement_context, dict):
        measurement_context = {}
    measurement_context = {
        **dict(default_context or {}),
        **measurement_context,
    }
    data_boundary = _data_boundary(normalized.get("data_boundary"), source=source)

    normalized.update(
        {
            "source": source,
            "confidence": confidence,
            "confidence_category": confidence_category,
            "parameter_origin": origin,
            "measurement_context": measurement_context,
            "data_boundary": data_boundary,
            "is_override": bool(normalized.get("is_override", is_override)),
        }
    )
    if normalized["is_override"]:
        normalized.setdefault("override_policy", "do_not_replace_defaults_silently")
    return normalized


def summarize_parameter_governance(
    parameters: dict[str, Any],
) -> dict[str, Any]:
    source_summary: dict[str, int] = {}
    origin_summary: dict[str, int] = {}
    confidence_summary: dict[str, int] = {}
    boundary_summary: dict[str, int] = {}
    override_count = 0
    missing_context = []
    for name, parameter in parameters.items():
        record = parameter if isinstance(parameter, dict) else {}
        source = str(record.get("source") or "unknown")
        origin = str(record.get("parameter_origin") or "unknown")
        confidence_category = str(record.get("confidence_category") or "unknown")
        data_boundary = str(record.get("data_boundary") or "unknown")
        source_summary[source] = source_summary.get(source, 0) + 1
        origin_summary[origin] = origin_summary.get(origin, 0) + 1
        confidence_summary[confidence_category] = (
            confidence_summary.get(confidence_category, 0) + 1
        )
        boundary_summary[data_boundary] = boundary_summary.get(data_boundary, 0) + 1
        if bool(record.get("is_override")):
            override_count += 1
        if not isinstance(record.get("measurement_context"), dict):
            missing_context.append(str(name))
    return {
        "source_summary": source_summary,
        "origin_summary": origin_summary,
        "confidence_summary": confidence_summary,
        "data_boundary_summary": boundary_summary,
        "override_count": override_count,
        "local_private_parameter_count": boundary_summary.get("local_private", 0),
        "parameters_missing_measurement_context": missing_context,
        "all_parameters_have_origin": origin_summary.get("unknown", 0) == 0,
    }


def _origin(value: Any, *, source: str, default_origin: str) -> str:
    selected = str(value or "").strip().lower()
    if selected in PARAMETER_ORIGINS:
        return selected
    source_lower = source.lower()
    if "default" in source_lower or "built_in" in source_lower:
        return "default"
    if "literature" in source_lower or "doi" in source_lower or "pubmed" in source_lower:
        return "literature"
    if "measured" in source_lower or "experiment" in source_lower:
        return "measured"
    if "local" in source_lower or "fitted" in source_lower or "inferred" in source_lower:
        return "inferred"
    fallback = str(default_origin or "unknown").strip().lower()
    return fallback if fallback in PARAMETER_ORIGINS else "unknown"


def _confidence(value: Any) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def _confidence_category(
    value: Any,
    *,
    source: str,
    origin: str,
    confidence: float | None,
) -> str:
    selected = str(value or "").strip().lower()
    if selected in CONFIDENCE_CATEGORIES:
        return selected
    if origin in CONFIDENCE_CATEGORIES:
        return origin
    if confidence is None:
        return "unknown"
    if confidence >= 0.85:
        return "measured"
    if confidence >= 0.65:
        return "literature" if "literature" in source.lower() else "inferred"
    if confidence >= 0.35:
        return "default"
    return "unknown"


def _data_boundary(value: Any, *, source: str) -> str:
    selected = str(value or "").strip().lower()
    if selected in DATA_BOUNDARIES:
        return selected
    if source.lower().startswith("local_") or "private" in source.lower():
        return "local_private"
    return "public" if source != "unknown" else "unknown"
