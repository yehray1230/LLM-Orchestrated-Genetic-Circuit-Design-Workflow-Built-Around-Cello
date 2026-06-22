from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FieldEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_path: str = Field(min_length=1, max_length=256)
    status: str = Field(default="unknown", max_length=64)
    source_uri: str | None = Field(default=None, max_length=2048)
    locator: str | None = Field(default=None, max_length=512)
    note: str = Field(default="", max_length=4000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class DraftPartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    part_type: str = Field(min_length=1, max_length=64)
    role: str = Field(default="", max_length=2000)
    sequence: str | None = Field(default=None, max_length=2_000_000)
    host_compatibility: list[str] = Field(default_factory=list, max_length=50)
    evidence: FieldEvidenceRequest | None = None


class DraftInteractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    interaction_type: str = Field(min_length=1, max_length=64)
    label: str = Field(default="", max_length=512)


class ImportDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str = Field(min_length=1, max_length=128)
    name: str = Field(default="", max_length=512)
    source_type: str = Field(default="literature", max_length=64)
    source_uri: str | None = Field(default=None, max_length=2048)
    citation: str = Field(default="", max_length=8000)
    host_organism: str = Field(default="unknown", max_length=512)
    inputs: list[str] = Field(default_factory=list, max_length=100)
    outputs: list[str] = Field(default_factory=list, max_length=100)
    logic_expression: str = Field(default="", max_length=20_000)
    validation_status: str = Field(default="unknown", max_length=64)
    validation_notes: str = Field(default="", max_length=20_000)
    parts: list[DraftPartRequest] = Field(default_factory=list, max_length=2000)
    interactions: list[DraftInteractionRequest] = Field(
        default_factory=list,
        max_length=5000,
    )
    evidence: list[FieldEvidenceRequest] = Field(default_factory=list, max_length=5000)
    notes: str = Field(default="", max_length=20_000)
    created_at: str = Field(default="", max_length=128)
    schema_version: str = Field(default="1.0", max_length=32)


class JsonImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: ImportDraftRequest


class GenBankImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(default="external_design.gb", max_length=255)
    content: str = Field(min_length=1, max_length=5_000_000)


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_design_id: str = Field(min_length=1, max_length=128)
    right_design_id: str = Field(min_length=1, max_length=128)
    left_metrics: dict[str, Any] = Field(default_factory=dict)
    right_metrics: dict[str, Any] = Field(default_factory=dict)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: dict[str, Any]
    profile_id: str = Field(default="research-v1.8", max_length=128)


class BenchmarkRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1, max_length=128)
    profile_id: str = Field(default="research-v1.8", max_length=128)


class BenchmarkComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_run_ids: list[str] = Field(min_length=2, max_length=20)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topology: dict[str, Any]
    simulation_time: float = Field(default=600.0, gt=0.0, le=604800.0)
    sample_count: int = Field(default=80, ge=2, le=10000)
    monte_carlo_samples: int = Field(default=1, ge=1, le=1000)
    noise_fraction: float = Field(default=0.15, ge=0.0, le=10.0)
    random_seed: int | None = Field(default=None, ge=0, le=2**32 - 1)


class RunStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_intent: str = Field(min_length=1, max_length=20_000)
    host_organism: str = Field(
        default="Escherichia coli",
        min_length=1,
        max_length=512,
    )
    compute_budget: int = Field(default=6, ge=1, le=100)
    enable_rag: bool = True
    enable_ode: bool = True
    enable_skill_extraction: bool = True
    monte_carlo_samples: int = Field(default=1, ge=1, le=1000)
    model_name: str | None = Field(default=None, max_length=256)
    api_base: str | None = Field(default=None, max_length=2048)
    cello_command: str | None = Field(default=None, max_length=4000)
    ucf_path: str | None = Field(default=None, max_length=2048)


class RunFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraints: list[str] = Field(min_length=1, max_length=100)
    action: str = Field(default="repair", pattern="^(repair|exploitation|fallback)$")
    extra_budget: int = Field(default=2, ge=1, le=100)


class RunResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str | None = Field(default=None, max_length=256)
    api_base: str | None = Field(default=None, max_length=2048)
