from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class PhaseWindow:
    start: float
    end: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.start) or not math.isfinite(self.end):
            raise ValueError("Phase-window bounds must be finite.")
        if self.start < 0.0:
            raise ValueError("Phase-window start must be non-negative.")
        if self.end <= self.start:
            raise ValueError("Phase-window end must be greater than start.")

    def to_dict(self) -> dict[str, float]:
        return {"start": self.start, "end": self.end}


@dataclass(frozen=True)
class ToggleProfile:
    high_threshold: float
    low_threshold: float
    phase_windows: dict[str, PhaseWindow]
    minimum_hold_margin: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.high_threshold) or not math.isfinite(
            self.low_threshold
        ):
            raise ValueError("Toggle thresholds must be finite.")
        if self.low_threshold < 0.0:
            raise ValueError("Toggle low threshold must be non-negative.")
        if self.high_threshold <= self.low_threshold:
            raise ValueError("Toggle high threshold must exceed low threshold.")
        if not math.isfinite(self.minimum_hold_margin):
            raise ValueError("Toggle hold margin must be finite.")
        if self.minimum_hold_margin < 0.0:
            raise ValueError("Toggle hold margin must be non-negative.")
        required_windows = {
            "phase1_end",
            "phase2",
            "phase3_end",
            "phase4",
            "simultaneous",
        }
        missing = sorted(required_windows - set(self.phase_windows))
        if missing:
            raise ValueError(
                "Toggle profile is missing phase windows: " + ", ".join(missing)
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_threshold": self.high_threshold,
            "low_threshold": self.low_threshold,
            "phase_windows": {k: v.to_dict() for k, v in self.phase_windows.items()},
            "minimum_hold_margin": self.minimum_hold_margin,
        }


@dataclass(frozen=True)
class OscillatorProfile:
    transient_cutoff: float
    minimum_peak_count: int
    minimum_amplitude: float
    maximum_period_cv: float | None = None
    minimum_amplitude_retention: float | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.transient_cutoff) or self.transient_cutoff < 0.0:
            raise ValueError("Oscillator transient cutoff must be non-negative.")
        if self.minimum_peak_count < 2:
            raise ValueError("Oscillator minimum peak count must be at least two.")
        if not math.isfinite(self.minimum_amplitude) or self.minimum_amplitude <= 0.0:
            raise ValueError("Oscillator minimum amplitude must be positive.")
        if self.maximum_period_cv is not None:
            if (
                not math.isfinite(self.maximum_period_cv)
                or self.maximum_period_cv < 0.0
            ):
                raise ValueError("Oscillator maximum period CV must be non-negative.")
        if self.minimum_amplitude_retention is not None:
            if not 0.0 <= self.minimum_amplitude_retention <= 1.0:
                raise ValueError(
                    "Oscillator minimum amplitude retention must be between zero and one."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transient_cutoff": self.transient_cutoff,
            "minimum_peak_count": self.minimum_peak_count,
            "minimum_amplitude": self.minimum_amplitude,
            "maximum_period_cv": self.maximum_period_cv,
            "minimum_amplitude_retention": self.minimum_amplitude_retention,
        }


@dataclass(frozen=True)
class TemporalEvaluatorConfig:
    version: str
    toggle_profile: ToggleProfile
    oscillator_profile: OscillatorProfile

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("Temporal evaluator version is required.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "toggle_profile": self.toggle_profile.to_dict(),
            "oscillator_profile": self.oscillator_profile.to_dict(),
        }


# Configuration Version 1.0 (aligns exactly with existing hardcoded thresholds)
CONFIG_V1_0 = TemporalEvaluatorConfig(
    version="1.0",
    toggle_profile=ToggleProfile(
        high_threshold=100.0,
        low_threshold=40.0,
        phase_windows={
            "phase1_end": PhaseWindow(950.0, 1000.0),
            "phase2": PhaseWindow(1100.0, 2000.0),
            "phase3_end": PhaseWindow(2950.0, 3000.0),
            "phase4": PhaseWindow(3100.0, 4000.0),
            "simultaneous": PhaseWindow(4900.0, 5000.0),
        },
        minimum_hold_margin=20.0,
    ),
    oscillator_profile=OscillatorProfile(
        transient_cutoff=200.0,
        minimum_peak_count=2,
        minimum_amplitude=10.0,
        maximum_period_cv=None,
        minimum_amplitude_retention=None,
    ),
)

# Configuration Version 1.1 (the proposed stricter thresholds)
CONFIG_V1_1 = TemporalEvaluatorConfig(
    version="1.1",
    toggle_profile=ToggleProfile(
        high_threshold=100.0,
        low_threshold=40.0,
        phase_windows={
            "phase1_end": PhaseWindow(950.0, 1000.0),
            "phase2": PhaseWindow(1100.0, 2000.0),
            "phase3_end": PhaseWindow(2950.0, 3000.0),
            "phase4": PhaseWindow(3100.0, 4000.0),
            "simultaneous": PhaseWindow(4900.0, 5000.0),
        },
        minimum_hold_margin=20.0,
    ),
    oscillator_profile=OscillatorProfile(
        transient_cutoff=500.0,
        minimum_peak_count=3,
        minimum_amplitude=10.0,
        maximum_period_cv=0.25,
        minimum_amplitude_retention=0.7,
    ),
)


TEMPORAL_EVALUATOR_CONFIGS = {
    CONFIG_V1_0.version: CONFIG_V1_0,
    CONFIG_V1_1.version: CONFIG_V1_1,
}


def get_temporal_evaluator_config(version: str) -> TemporalEvaluatorConfig:
    try:
        return TEMPORAL_EVALUATOR_CONFIGS[version]
    except KeyError as exc:
        supported = ", ".join(sorted(TEMPORAL_EVALUATOR_CONFIGS))
        raise ValueError(
            f"Unknown temporal evaluator version: {version}. Supported: {supported}."
        ) from exc


DEFAULT_TEMPORAL_CONFIG = CONFIG_V1_1
