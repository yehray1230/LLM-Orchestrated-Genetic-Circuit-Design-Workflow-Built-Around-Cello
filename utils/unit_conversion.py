from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedValue:
    value: float
    unit: str


CONCENTRATION_TO_NM = {
    "m": 1_000_000_000.0,
    "molar": 1_000_000_000.0,
    "mm": 1_000_000.0,
    "millimolar": 1_000_000.0,
    "um": 1000.0,
    "µm": 1000.0,
    "μm": 1000.0,
    "micromolar": 1000.0,
    "nm": 1.0,
    "nanomolar": 1.0,
    "pm": 0.001,
    "picomolar": 0.001,
}


RATE_TO_PER_SECOND = {
    "s^-1": 1.0,
    "1/s": 1.0,
    "1/sec": 1.0,
    "1/second": 1.0,
    "per_second": 1.0,
    "min^-1": 1.0 / 60.0,
    "1/min": 1.0 / 60.0,
    "1/minute": 1.0 / 60.0,
    "per_minute": 1.0 / 60.0,
    "h^-1": 1.0 / 3600.0,
    "1/h": 1.0 / 3600.0,
    "1/hour": 1.0 / 3600.0,
    "per_hour": 1.0 / 3600.0,
}


def normalize_biokinetic_value(value: float, unit: str) -> NormalizedValue:
    normalized_unit = _canonical_unit(unit)
    if normalized_unit in CONCENTRATION_TO_NM:
        return NormalizedValue(value=float(value) * CONCENTRATION_TO_NM[normalized_unit], unit="nM")
    if normalized_unit in RATE_TO_PER_SECOND:
        return NormalizedValue(value=float(value) * RATE_TO_PER_SECOND[normalized_unit], unit="1/s")
    if normalized_unit in {"nm/s", "nanomolar/second"}:
        return NormalizedValue(value=float(value), unit="nM/s")
    if normalized_unit in {"um/s", "µm/s", "μm/s", "micromolar/second"}:
        return NormalizedValue(value=float(value) * 1000.0, unit="nM/s")
    if normalized_unit in {"nm/min", "nanomolar/minute"}:
        return NormalizedValue(value=float(value) / 60.0, unit="nM/s")
    if normalized_unit in {"um/min", "µm/min", "μm/min", "micromolar/minute"}:
        return NormalizedValue(value=float(value) * 1000.0 / 60.0, unit="nM/s")
    if normalized_unit in {"", "dimensionless", "unitless"}:
        return NormalizedValue(value=float(value), unit="dimensionless")
    return NormalizedValue(value=float(value), unit=unit or "dimensionless")


def _canonical_unit(unit: str) -> str:
    return (
        str(unit or "")
        .strip()
        .replace(" ", "")
        .replace("−", "-")
        .replace("^-1", "^-1")
        .lower()
    )
