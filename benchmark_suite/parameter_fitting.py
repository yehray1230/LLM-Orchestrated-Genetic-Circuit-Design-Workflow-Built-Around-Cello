from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np

from schemas.parameter_governance import normalize_parameter_metadata
from tools.tool_adapters import detect_python_module, normalize_tool_warning

try:
    from scipy.optimize import curve_fit
except ModuleNotFoundError:  # pragma: no cover - depends on runtime extras
    curve_fit = None


@dataclass
class PlateReaderPoint:
    concentration: float
    response: float
    replicate: str = ""
    condition: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HillFitResult:
    status: str
    parameters: dict[str, dict[str, Any]]
    metrics: dict[str, Any]
    tool_record: dict[str, Any]
    warnings: list[dict[str, Any]] = field(default_factory=list)
    fitted_points: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_plate_reader_csv(
    source: str | Path,
    *,
    concentration_column: str = "concentration",
    response_column: str = "response",
) -> list[PlateReaderPoint]:
    text = (
        Path(source).read_text(encoding="utf-8")
        if isinstance(source, Path) or Path(str(source)).is_file()
        else str(source)
    )
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Plate-reader CSV requires a header row.")
    normalized_fields = {field.strip().lower(): field for field in reader.fieldnames}
    concentration_key = normalized_fields.get(concentration_column.lower())
    response_key = normalized_fields.get(response_column.lower())
    if concentration_key is None or response_key is None:
        raise ValueError(
            f"CSV requires '{concentration_column}' and '{response_column}' columns."
        )

    points = []
    for index, row in enumerate(reader, start=2):
        try:
            concentration = float(row.get(concentration_key, ""))
            response = float(row.get(response_key, ""))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric value on CSV row {index}.") from exc
        if concentration < 0.0:
            raise ValueError(f"Concentration must be non-negative on CSV row {index}.")
        metadata = {
            key: value
            for key, value in row.items()
            if key not in {concentration_key, response_key}
        }
        points.append(
            PlateReaderPoint(
                concentration=concentration,
                response=response,
                replicate=str(row.get("replicate") or ""),
                condition=str(row.get("condition") or ""),
                metadata=metadata,
            )
        )
    if len(points) < 4:
        raise ValueError("At least four plate-reader rows are required for fitting.")
    return points


def fit_hill_response(
    points: list[PlateReaderPoint] | list[dict[str, Any]],
    *,
    source: str = "local_plate_reader_fit",
    measurement_context: dict[str, Any] | None = None,
) -> HillFitResult:
    parsed = [_coerce_point(point) for point in points]
    concentrations = np.asarray([point.concentration for point in parsed], dtype=float)
    responses = np.asarray([point.response for point in parsed], dtype=float)
    if len(parsed) < 4:
        raise ValueError("At least four points are required for Hill fitting.")
    if np.any(concentrations < 0.0):
        raise ValueError("Concentrations must be non-negative.")
    if float(np.max(concentrations)) <= 0.0:
        raise ValueError("At least one concentration must be greater than zero.")

    tool_record = _fit_tool_record()
    warnings = []
    try:
        values, covariance, method = _fit_with_scipy(concentrations, responses)
    except Exception as exc:
        values, covariance, method = _fit_with_deterministic_fallback(
            concentrations,
            responses,
        )
        tool_record["fallback_used"] = True
        tool_record["status"] = "fallback"
        warnings.append(
            normalize_tool_warning(
                "FITTING_FALLBACK_USED",
                f"SciPy curve_fit was unavailable or failed; used deterministic fallback ({exc}).",
            ).to_dict()
        )

    y_min, y_max, kd, hill = values
    predicted = _hill(concentrations, y_min, y_max, kd, hill)
    residuals = responses - predicted
    ss_res = float(np.sum(residuals * residuals))
    ss_tot = float(np.sum((responses - np.mean(responses)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 1.0
    context = {
        "fit_model": "hill_activation",
        "point_count": len(parsed),
        **dict(measurement_context or {}),
    }
    parameters = {
        "y_min": _parameter_record(y_min, "a.u.", source, context),
        "y_max": _parameter_record(y_max, "a.u.", source, context),
        "kd": _parameter_record(kd, "input concentration", source, context),
        "hill_coefficient": _parameter_record(hill, "dimensionless", source, context),
    }
    return HillFitResult(
        status="completed",
        parameters=parameters,
        metrics={
            "method": method,
            "r_squared": round(float(r_squared), 10),
            "residual_sum_squares": round(ss_res, 10),
            "point_count": len(parsed),
            "covariance_available": covariance is not None,
        },
        tool_record=tool_record,
        warnings=warnings,
        fitted_points=[
            {
                "concentration": float(concentration),
                "observed": float(observed),
                "predicted": float(estimate),
                "residual": float(observed - estimate),
            }
            for concentration, observed, estimate in zip(
                concentrations,
                responses,
                predicted,
            )
        ],
    )


def fitted_parameters_to_part_override(
    *,
    part_id: str,
    fit: HillFitResult | dict[str, Any],
    snapshot_id: str,
) -> dict[str, Any]:
    payload = fit.to_dict() if isinstance(fit, HillFitResult) else dict(fit)
    parameters = dict(payload.get("parameters") or {})
    if not part_id.strip():
        raise ValueError("part_id is required.")
    if not snapshot_id.strip():
        raise ValueError("snapshot_id is required.")
    return {
        "part_id": part_id,
        "snapshot_id": snapshot_id,
        "parameter_origin": "inferred",
        "data_boundary": "local_private",
        "parameters": parameters,
        "fit_metrics": dict(payload.get("metrics") or {}),
        "tool_record": dict(payload.get("tool_record") or {}),
        "warnings": list(payload.get("warnings") or []),
        "update_policy": "override_only_do_not_replace_source_defaults",
    }


def apply_parameter_fit_snapshot(
    topology: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    selected = dict(topology)
    override = dict(snapshot.get("override") or {})
    parameters = dict(override.get("parameters") or {})
    if not parameters:
        raise ValueError("Parameter fit snapshot does not contain override parameters.")
    biokinetic = dict(selected.get("biokinetic_parameters") or {})
    existing_parameters = dict(biokinetic.get("parameters") or {})
    merged_parameters = {
        **existing_parameters,
        **parameters,
    }
    applied = {
        "snapshot_id": snapshot.get("snapshot_id") or override.get("snapshot_id"),
        "part_id": snapshot.get("part_id") or override.get("part_id"),
        "source": snapshot.get("source"),
        "data_boundary": snapshot.get("data_boundary", "local_private"),
        "update_policy": snapshot.get(
            "update_policy",
            override.get("update_policy"),
        ),
        "fit_metrics": dict(override.get("fit_metrics") or {}),
    }
    biokinetic.update(
        {
            "parameters": merged_parameters,
            "parameter_fit_snapshot": applied,
        }
    )
    mining_summary = dict(biokinetic.get("mining_summary") or {})
    applied_snapshots = list(mining_summary.get("applied_parameter_fit_snapshots") or [])
    if applied["snapshot_id"] not in applied_snapshots:
        applied_snapshots.append(applied["snapshot_id"])
    mining_summary["applied_parameter_fit_snapshots"] = applied_snapshots
    mining_summary["local_private_parameter_count"] = max(
        int(mining_summary.get("local_private_parameter_count") or 0),
        len(parameters),
    )
    biokinetic["mining_summary"] = mining_summary
    selected["biokinetic_parameters"] = biokinetic
    selected["applied_parameter_fit_snapshot"] = applied
    return selected


def _fit_with_scipy(
    concentrations: np.ndarray,
    responses: np.ndarray,
) -> tuple[tuple[float, float, float, float], Any, str]:
    if curve_fit is None:
        raise RuntimeError("scipy.optimize.curve_fit is unavailable")
    initial = _initial_guess(concentrations, responses)
    lower = [0.0, 0.0, max(float(np.min(concentrations[concentrations > 0])), 1e-9), 0.2]
    upper = [
        max(float(np.max(responses)) * 2.0, 1.0),
        max(float(np.max(responses)) * 3.0, 1.0),
        max(float(np.max(concentrations)) * 10.0, 1e-6),
        6.0,
    ]
    values, covariance = curve_fit(
        _hill,
        concentrations,
        responses,
        p0=initial,
        bounds=(lower, upper),
        maxfev=10000,
    )
    y_min, y_max, kd, hill = [float(value) for value in values]
    if y_max < y_min:
        y_min, y_max = y_max, y_min
    return (y_min, y_max, max(kd, 1e-9), max(hill, 0.2)), covariance, "scipy_curve_fit"


def _fit_with_deterministic_fallback(
    concentrations: np.ndarray,
    responses: np.ndarray,
) -> tuple[tuple[float, float, float, float], None, str]:
    y_min = float(np.min(responses))
    y_max = float(np.max(responses))
    midpoint = y_min + 0.5 * (y_max - y_min)
    kd = float(concentrations[np.argmin(np.abs(responses - midpoint))])
    kd = max(kd, 1e-9)
    best = (y_min, y_max, kd, 1.0)
    best_error = float("inf")
    for hill in np.linspace(0.5, 4.0, 36):
        predicted = _hill(concentrations, y_min, y_max, kd, float(hill))
        error = float(np.sum((responses - predicted) ** 2))
        if error < best_error:
            best_error = error
            best = (y_min, y_max, kd, float(hill))
    return best, None, "deterministic_midpoint_fallback"


def _hill(
    concentration: np.ndarray,
    y_min: float,
    y_max: float,
    kd: float,
    hill_coefficient: float,
) -> np.ndarray:
    concentration = np.maximum(np.asarray(concentration, dtype=float), 0.0)
    kd = max(float(kd), 1e-12)
    hill_coefficient = max(float(hill_coefficient), 1e-9)
    numerator = np.power(concentration, hill_coefficient)
    denominator = np.power(kd, hill_coefficient) + numerator
    return float(y_min) + (float(y_max) - float(y_min)) * numerator / denominator


def _initial_guess(
    concentrations: np.ndarray,
    responses: np.ndarray,
) -> tuple[float, float, float, float]:
    y_min = float(np.min(responses))
    y_max = float(np.max(responses))
    midpoint = y_min + 0.5 * (y_max - y_min)
    kd = float(concentrations[np.argmin(np.abs(responses - midpoint))])
    if kd <= 0.0:
        kd = max(float(np.median(concentrations[concentrations > 0])), 1e-9)
    return y_min, y_max, kd, 1.5


def _parameter_record(
    value: float,
    unit: str,
    source: str,
    measurement_context: dict[str, Any],
) -> dict[str, Any]:
    return normalize_parameter_metadata(
        {
            "value": round(float(value), 10),
            "unit": unit,
            "source": source,
            "confidence": 0.7,
            "measurement_context": measurement_context,
            "data_boundary": "local_private",
        },
        default_origin="inferred",
        is_override=True,
    )


def _fit_tool_record() -> dict[str, Any]:
    availability = detect_python_module(
        "scipy",
        tool_name="scipy",
        adapter_name="hill_parameter_fitter",
        capability="benchmark_parameter_fitting",
        fallback_available=True,
    )
    return availability.to_dict()


def _coerce_point(point: PlateReaderPoint | dict[str, Any]) -> PlateReaderPoint:
    if isinstance(point, PlateReaderPoint):
        return point
    return PlateReaderPoint(
        concentration=float(point.get("concentration")),
        response=float(point.get("response")),
        replicate=str(point.get("replicate") or ""),
        condition=str(point.get("condition") or ""),
        metadata=dict(point.get("metadata") or {}),
    )
