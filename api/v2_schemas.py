from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_id: str | None = Field(default=None, max_length=128)
    topology: dict[str, Any] | None = None
    simulation_time: float = Field(default=600.0, gt=0.0, le=604800.0)
    sample_count: int = Field(default=80, ge=2, le=10000)
    monte_carlo_samples: int = Field(default=1, ge=1, le=1000)
    noise_fraction: float = Field(default=0.15, ge=0.0, le=10.0)
    random_seed: int | None = Field(default=None, ge=0, le=2**32 - 1)
    profile_id: str = Field(default="research-v2-preview", max_length=128)

    @model_validator(mode="after")
    def validate_source(self) -> "ResearchSimulationRequest":
        if not self.design_id and not self.topology:
            raise ValueError("Either design_id or topology is required.")
        return self


class ResearchComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_run_ids: list[str] = Field(min_length=2, max_length=20)
