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


class SequenceAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_ids: list[str] | None = Field(default=None, max_length=200)
    window_size: int = Field(default=50, ge=1, le=1000)
    homopolymer_threshold: int = Field(default=6, ge=3, le=50)
    repeat_length: int = Field(default=12, ge=4, le=100)


class SequenceOptimizationEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(default="sequence_quality_baseline", max_length=128)
    host_profile_id: str | None = Field(default=None, max_length=128)
    part_ids: list[str] | None = Field(default=None, max_length=200)
    optimized_sequences: dict[str, str] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class SequenceOptimizationRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(default="codon_optimization", max_length=128)
    host_profile_id: str = Field(default="ecoli_k12_default", max_length=128)
    part_ids: list[str] | None = Field(default=None, max_length=200)
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_by: str = Field(default="sequence_optimizer", max_length=128)


class HostProfileRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    host_organism: str = Field(min_length=1, max_length=256)
    strain: str = Field(default="", max_length=256)
    codon_usage: dict[str, dict[str, float]] = Field(default_factory=dict)
    forbidden_motifs: list[str] = Field(default_factory=list, max_length=200)
    rare_codon_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    evidence_level: str = Field(default="defaulted", max_length=64)
    source: str = Field(default="user_supplied", max_length=2000)
    version: str = Field(default="1.0.0", max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)
    rnap_total: float | None = Field(default=None, gt=0.0)
    ribosome_total: float | None = Field(default=None, gt=0.0)
    transcription_rate: float | None = Field(default=None, ge=0.0)
    translation_rate: float | None = Field(default=None, ge=0.0)
    mrna_degradation_rate: float | None = Field(default=None, ge=0.0)
    protein_degradation_rate: float | None = Field(default=None, ge=0.0)
    growth_rate_dilution: float | None = Field(default=None, ge=0.0)
    km_rnap: float | None = Field(default=None, gt=0.0)
    km_ribosome: float | None = Field(default=None, gt=0.0)
    burden_soft_limit: float | None = Field(default=None, gt=0.0)
    toxicity_threshold: float | None = Field(default=None, gt=0.0)


class HostOptimizationCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host_profile_id: str = Field(default="ecoli_k12_default", max_length=128)
    part_ids: list[str] | None = Field(default=None, max_length=200)
    objective_weights: dict[str, float] = Field(default_factory=dict)


class ExperimentalMeasurementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measurement_id: str = Field(min_length=1, max_length=128)
    design_id: str = Field(min_length=1, max_length=128)
    candidate_id: str | None = Field(default=None, max_length=128)
    host_profile_id: str | None = Field(default=None, max_length=128)
    expression_value: float | None = None
    growth_rate: float | None = None
    burden_value: float | None = None
    on_off_ratio: float | None = None
    units: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HostCalibrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calibration_id: str | None = Field(default=None, max_length=128)
    design_id: str = Field(min_length=1, max_length=128)
    host_profile_id: str | None = Field(default=None, max_length=128)
    measurements: list[ExperimentalMeasurementRequest] = Field(min_length=1)


class OptimizationWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host_profile_id: str = Field(default="ecoli_k12_default", max_length=128)
    part_ids: list[str] | None = Field(default=None, max_length=200)
    sequence_objective: str = Field(default="codon_optimization", max_length=128)
    objective_weights: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_by: str = Field(default="optimization_workflow", max_length=128)


class PlasmidAssemblyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plasmid_id: str = Field(min_length=1, max_length=128)
    backbone_id: str = Field(min_length=1, max_length=128)
    backbone_version: str = Field(min_length=1, max_length=64)
    insertion_region_id: str = Field(min_length=1, max_length=128)
    insertion_start: int = Field(ge=0)
    insertion_end: int = Field(ge=0)
    assembly_method: str = Field(
        default="direct_insertion",
        pattern=r"^(direct_insertion|gibson|restriction_cloning)$",
    )

    @model_validator(mode="after")
    def validate_window(self) -> "PlasmidAssemblyRequest":
        if self.insertion_start > self.insertion_end:
            raise ValueError(
                "insertion_start must be less than or equal to insertion_end."
            )
        return self


class BackboneRegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    description: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_window(self) -> "BackboneRegionRequest":
        if self.start >= self.end:
            raise ValueError("Region start must be less than region end.")
        return self


class BackboneRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backbone_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=256)
    source_type: str = Field(min_length=1, max_length=64)
    source_uri: str = Field(min_length=1, max_length=2000)
    genbank: str = Field(min_length=1, max_length=5_000_000)
    sequence_checksum: str | None = Field(default=None, max_length=128)
    host_organisms: list[str] = Field(min_length=1, max_length=50)
    origin_of_replication: str = Field(min_length=1, max_length=256)
    selection_marker: str = Field(min_length=1, max_length=256)
    copy_number_class: str = Field(min_length=1, max_length=32)
    insertion_regions: list[BackboneRegionRequest] = Field(min_length=1)
    essential_regions: list[BackboneRegionRequest] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssemblyPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plasmid_id: str = Field(min_length=1, max_length=128)
    backbone_id: str = Field(min_length=1, max_length=128)
    backbone_version: str = Field(min_length=1, max_length=64)
    insertion_region_id: str = Field(min_length=1, max_length=128)
    insertion_start: int = Field(ge=0)
    revision_number: int | None = Field(default=None)
    insertion_end: int = Field(ge=0)
    method: str = Field(
        pattern=r"^(restriction_cloning|gibson|golden_gate)$"
    )
    restriction_enzymes: list[str] = Field(
        default_factory=lambda: ["EcoRI", "BsaI", "BsmBI"],
        min_length=1,
        max_length=20,
    )
    gibson_overlap_length: int = Field(default=25, ge=15, le=80)
    golden_gate_enzyme: str = Field(
        default="BsaI",
        pattern=r"^(BsaI|BsmBI)$",
    )
    golden_gate_overhangs: list[str] | None = Field(
        default=None,
        min_length=2,
        max_length=2,
    )

    @model_validator(mode="after")
    def validate_plan(self) -> "AssemblyPlanRequest":
        if self.insertion_start > self.insertion_end:
            raise ValueError(
                "insertion_start must be less than or equal to insertion_end."
            )
        return self


class AssemblyDeliverableRequest(AssemblyPlanRequest):
    primer_min_size: int = Field(default=18, ge=15, le=35)
    primer_opt_size: int = Field(default=20, ge=15, le=35)
    primer_max_size: int = Field(default=28, ge=15, le=40)
    primer_min_tm: float = Field(default=57.0, ge=40.0, le=80.0)
    primer_opt_tm: float = Field(default=60.0, ge=40.0, le=80.0)
    primer_max_tm: float = Field(default=63.0, ge=40.0, le=80.0)
    primer_min_gc: float = Field(default=35.0, ge=0.0, le=100.0)
    primer_max_gc: float = Field(default=65.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_primer_ranges(self) -> "AssemblyDeliverableRequest":
        if not self.primer_min_size <= self.primer_opt_size <= self.primer_max_size:
            raise ValueError("Primer sizes must satisfy min <= opt <= max.")
        if not self.primer_min_tm <= self.primer_opt_tm <= self.primer_max_tm:
            raise ValueError("Primer Tm values must satisfy min <= opt <= max.")
        if self.primer_min_gc > self.primer_max_gc:
            raise ValueError("Primer GC values must satisfy min <= max.")
        return self
