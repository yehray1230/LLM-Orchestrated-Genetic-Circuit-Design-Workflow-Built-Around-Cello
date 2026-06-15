from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

from application.research import ResearchService
from benchmark_suite.benchmark_controller import evaluate_candidate
from benchmark_suite.dataset import (
    list_benchmark_datasets,
    load_benchmark_dataset,
)
from benchmark_suite.runner import (
    compare_benchmark_runs,
    run_benchmark_dataset,
)
from benchmark_suite.scoring_profiles import list_scoring_profiles
from exporters.bom_exporter import export_bom_csv
from exporters.export_result import ExportResult
from exporters.genbank_exporter import export_genbank
from exporters.plasmid_tools import PlasmidAssemblyResult, assemble_plasmid_v2
from exporters.sbol3_exporter import export_sbol3_turtle
from importers.genbank_importer import genbank_to_import_draft
from mcp_server.run_store import RunStore
from mcp_server.service import (
    cancel_design_run,
    get_design_run_artifacts,
    get_design_run_events,
    get_design_run_result,
    get_design_run_status,
    list_design_runs,
    resume_design_run,
    start_design_run,
    submit_design_feedback,
)
from repositories.json_repository import JsonRepository
from repositories.factory import create_design_repository, repository_backend
from repositories.protocols import RecordRepository, RevisionRepository
from repositories.sqlite_repository import canonical_payload_hash
from schemas.backbone_registry import (
    BackboneRegistryEntry,
    backbone_entry_from_dict,
    create_backbone_entry,
    registry_key,
)
from benchmark_suite.readiness_evaluator import evaluate_readiness
from schemas.design_diff import compare_designs
from schemas.design_migrations import (
    design_ir_v2_to_v1_payload,
    migrate_design_payload_to_v2,
)
from schemas.design_ir import DesignIR, design_ir_from_dict
from schemas.design_ir_v2 import DesignIRV2, design_ir_v2_from_dict
from schemas.import_draft import (
    ImportDraft,
    import_draft_from_json,
    import_draft_to_design_ir,
    validate_import_draft,
)
from schemas.simulation import (
    SIMULATION_MODEL_ID,
    SIMULATION_MODEL_VERSION,
    simulation_spec_from_design_ir_v2,
)
from tools.assembly_planner import create_assembly_plan
from tools.ode_simulator import BatchODESimulator


DEFAULT_API_DATA_DIR = Path("outputs") / "api_data"
SAFE_RUN_ID = re.compile(r"^run_[A-Za-z0-9_-]{1,120}$")


class ImportService:
    def __init__(
        self,
        draft_repository: JsonRepository,
        design_service: DesignService,
    ):
        self.drafts = draft_repository
        self.designs = design_service

    def validate(self, draft: ImportDraft) -> dict[str, Any]:
        validation = validate_import_draft(draft)
        return {**asdict(validation), "can_import": validation.can_import}

    def save_draft(self, draft: ImportDraft) -> ImportDraft:
        self.drafts.save(draft.draft_id, draft.to_dict())
        return draft

    def get_draft(self, draft_id: str) -> ImportDraft | None:
        payload = self.drafts.get(draft_id)
        return import_draft_from_json(payload) if payload else None

    def import_json(self, value: str | bytes | dict[str, Any]) -> ImportDraft:
        return self.save_draft(import_draft_from_json(value))

    def import_genbank(
        self,
        value: str | bytes,
        *,
        filename: str,
    ) -> ImportDraft:
        return self.save_draft(
            genbank_to_import_draft(value, filename=filename)
        )

    def confirm(self, draft: ImportDraft) -> DesignIR:
        self.save_draft(draft)
        design = import_draft_to_design_ir(draft)
        return self.designs.save(design)

    def confirm_by_id(self, draft_id: str) -> DesignIR:
        draft = self.get_draft(draft_id)
        if draft is None:
            raise KeyError(draft_id)
        return self.confirm(draft)


class DesignService:
    def __init__(self, repository: RecordRepository):
        self.repository = repository

    def save(self, design: DesignIR) -> DesignIR:
        source_payload = design.to_dict()
        migration = migrate_design_payload_to_v2(source_payload)
        stored = self.repository.save(design.design_id, migration.design.to_dict())
        self._record_migration(
            design.design_id,
            source_payload=source_payload,
            result_payload=stored,
            migration=migration.to_dict(),
        )
        return design_ir_from_dict(design_ir_v2_to_v1_payload(stored))

    def get(self, design_id: str) -> DesignIR | None:
        payload = self.repository.get(design_id)
        return (
            design_ir_from_dict(design_ir_v2_to_v1_payload(payload))
            if payload
            else None
        )

    def list(self) -> list[DesignIR]:
        return [
            design_ir_from_dict(design_ir_v2_to_v1_payload(payload))
            for payload in self.repository.list()
        ]

    def get_v2(self, design_id: str) -> DesignIRV2 | None:
        payload = self.repository.get(design_id)
        return design_ir_v2_from_dict(payload) if payload else None

    def list_v2(self) -> list[DesignIRV2]:
        return [
            design_ir_v2_from_dict(payload)
            for payload in self.repository.list()
        ]

    def revisions(self, design_id: str) -> list[dict[str, Any]]:
        if not isinstance(self.repository, RevisionRepository):
            return []
        return self.repository.list_revisions(design_id)

    def get_revision(
        self,
        design_id: str,
        revision_number: int,
    ) -> DesignIRV2 | None:
        if not isinstance(self.repository, RevisionRepository):
            return None
        payload = self.repository.get_revision(design_id, revision_number)
        return design_ir_v2_from_dict(payload) if payload else None

    def simulation_spec(self, design_id: str) -> dict[str, Any] | None:
        design = self.get_v2(design_id)
        if design is None:
            return None
        return simulation_spec_from_design_ir_v2(design).to_dict()

    def _record_migration(
        self,
        design_id: str,
        *,
        source_payload: dict[str, Any],
        result_payload: dict[str, Any],
        migration: dict[str, Any],
    ) -> None:
        recorder = getattr(self.repository, "record_payload_migration", None)
        if not callable(recorder):
            return
        recorder(
            source_id=design_id,
            source_version=str(source_payload.get("schema_version") or "1.0"),
            target_version=str(result_payload.get("schema_version") or "2.0"),
            source_hash=canonical_payload_hash(source_payload),
            result_hash=canonical_payload_hash(result_payload),
            status="completed",
            report=migration,
        )


class ComparisonService:
    def __init__(self, designs: DesignService):
        self.designs = designs

    def compare(
        self,
        left_design_id: str,
        right_design_id: str,
        *,
        left_metrics: dict[str, Any] | None = None,
        right_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        left = self.designs.get(left_design_id)
        right = self.designs.get(right_design_id)
        if left is None:
            raise KeyError(left_design_id)
        if right is None:
            raise KeyError(right_design_id)
        return asdict(
            compare_designs(
                left,
                right,
                left_metrics=left_metrics,
                right_metrics=right_metrics,
            )
        )


class EvaluationService:
    def __init__(
        self,
        benchmark_repository: JsonRepository,
        report_dir: Path,
    ):
        self.benchmark_repository = benchmark_repository
        self.report_dir = report_dir

    def evaluate(
        self,
        candidate: dict[str, Any],
        *,
        profile_id: str = "research-v1.8",
    ) -> dict[str, Any]:
        return evaluate_candidate(candidate, profile_id=profile_id)

    def profiles(self) -> list[dict[str, Any]]:
        return list_scoring_profiles()

    def datasets(self) -> list[dict[str, Any]]:
        return list_benchmark_datasets()

    def dataset(self, dataset_id: str) -> dict[str, Any]:
        return load_benchmark_dataset(dataset_id).to_dict()

    def run_benchmark(
        self,
        dataset_id: str,
        *,
        profile_id: str = "research-v1.8",
    ) -> dict[str, Any]:
        dataset = load_benchmark_dataset(dataset_id)
        result = run_benchmark_dataset(
            dataset,
            profile_id=profile_id,
            output_dir=self.report_dir,
        )
        self.benchmark_repository.save(result["benchmark_run_id"], result)
        return result

    def benchmark_result(self, benchmark_run_id: str) -> dict[str, Any] | None:
        return self.benchmark_repository.get(benchmark_run_id)

    def benchmark_results(self) -> list[dict[str, Any]]:
        return self.benchmark_repository.list()

    def compare_benchmarks(
        self,
        benchmark_run_ids: list[str],
    ) -> dict[str, Any]:
        runs = []
        for run_id in benchmark_run_ids:
            result = self.benchmark_result(run_id)
            if result is None:
                raise KeyError(run_id)
            runs.append(result)
        return compare_benchmark_runs(runs)


class SimulationService:
    def models(self) -> list[dict[str, Any]]:
        return [
            {
                "model_id": SIMULATION_MODEL_ID,
                "version": SIMULATION_MODEL_VERSION,
                "status": "computational_screening",
                "state_model": "mRNA, immature protein, mature protein",
                "mechanisms": [
                    "regulatory topology",
                    "RNAP and ribosome competition",
                    "growth dilution",
                    "protein maturation",
                    "plasmid copy-number scaling",
                ],
            }
        ]

    def simulate(
        self,
        topology: dict[str, Any],
        *,
        simulation_time: float = 600.0,
        sample_count: int = 80,
        monte_carlo_samples: int = 1,
        noise_fraction: float = 0.15,
        random_seed: int | None = None,
    ) -> dict[str, Any]:
        simulator = BatchODESimulator(
            simulation_time=simulation_time,
            sample_count=sample_count,
            monte_carlo_samples=monte_carlo_samples,
            noise_fraction=noise_fraction,
            random_seed=random_seed,
        )
        result = simulator.simulate_topology(topology)
        return {
            "simulation_spec": result["simulation_spec"],
            "simulation_result": result["simulation_result"],
            "candidate": result,
        }


class ExportService:
    EXPORTERS = {
        "bom": export_bom_csv,
        "genbank": export_genbank,
        "sbol3": export_sbol3_turtle,
    }

    def __init__(self, designs: DesignService):
        self.designs = designs

    def export(self, design_id: str, export_format: str) -> ExportResult:
        design = self.designs.get(design_id)
        if design is None:
            raise KeyError(design_id)
        exporter = self.EXPORTERS.get(export_format.lower())
        if exporter is None:
            raise ValueError(f"Unsupported export format: {export_format}")
        return exporter(design)


class BackboneRegistryService:
    def __init__(self, repository: JsonRepository):
        self.repository = repository

    def register(self, payload: dict[str, Any]) -> BackboneRegistryEntry:
        entry = create_backbone_entry(payload)
        existing = self.get(entry.backbone_id, entry.version)
        if existing:
            if existing.sequence_checksum != entry.sequence_checksum:
                raise ValueError(
                    "Backbone version already exists with a different checksum."
                )
            return existing
        self.repository.save(entry.registry_key, entry.to_dict())
        return entry

    def get(
        self,
        backbone_id: str,
        version: str,
    ) -> BackboneRegistryEntry | None:
        payload = self.repository.get(registry_key(backbone_id, version))
        return backbone_entry_from_dict(payload) if payload else None

    def list(self) -> list[BackboneRegistryEntry]:
        return [
            backbone_entry_from_dict(payload)
            for payload in self.repository.list()
        ]


class PlasmidAssemblyService:
    def __init__(
        self,
        designs: DesignService,
        backbones: BackboneRegistryService,
    ):
        self.designs = designs
        self.backbones = backbones

    def assemble(
        self,
        design_id: str,
        *,
        plasmid_id: str,
        backbone_id: str,
        backbone_version: str,
        insertion_region_id: str,
        insertion_start: int,
        insertion_end: int,
        assembly_method: str = "direct_insertion",
    ) -> PlasmidAssemblyResult:
        design = self.designs.get_v2(design_id)
        if design is None:
            raise KeyError(design_id)
        backbone = self.backbones.get(backbone_id, backbone_version)
        if backbone is None:
            raise ValueError(
                f"Unknown registered backbone: {backbone_id}@{backbone_version}"
            )
        return assemble_plasmid_v2(
            design,
            plasmid_id=plasmid_id,
            backbone_genbank=backbone.genbank,
            insertion_start=insertion_start,
            insertion_end=insertion_end,
            assembly_method=assembly_method,
            backbone_entry=backbone,
            insertion_region_id=insertion_region_id,
        )


class AssemblyPlanningService:
    def __init__(
        self,
        assemblies: PlasmidAssemblyService,
        backbones: BackboneRegistryService,
    ):
        self.assemblies = assemblies
        self.backbones = backbones

    def plan(
        self,
        design_id: str,
        *,
        plasmid_id: str,
        backbone_id: str,
        backbone_version: str,
        insertion_region_id: str,
        insertion_start: int,
        insertion_end: int,
        method: str,
        restriction_enzymes: list[str] | None = None,
        gibson_overlap_length: int = 25,
        golden_gate_enzyme: str = "BsaI",
        golden_gate_overhangs: list[str] | None = None,
    ) -> dict[str, Any]:
        backbone = self.backbones.get(backbone_id, backbone_version)
        if backbone is None:
            raise ValueError(
                f"Unknown registered backbone: {backbone_id}@{backbone_version}"
            )
        design = self.assemblies.designs.get_v2(design_id)
        if design is None:
            raise KeyError(design_id)
        assembly = self.assemblies.assemble(
            design_id,
            plasmid_id=plasmid_id,
            backbone_id=backbone_id,
            backbone_version=backbone_version,
            insertion_region_id=insertion_region_id,
            insertion_start=insertion_start,
            insertion_end=insertion_end,
            assembly_method="direct_insertion",
        )
        if not assembly.ok:
            readiness = evaluate_readiness(
                design,
                assembly_report=assembly.report,
            )
            return {
                "ok": False,
                "assembly": assembly.to_dict(),
                "plan": None,
                "readiness": readiness.to_dict(),
            }
        plan = create_assembly_plan(
            assembly,
            backbone,
            method=method,
            insertion_start=insertion_start,
            insertion_end=insertion_end,
            restriction_enzymes=restriction_enzymes,
            gibson_overlap_length=gibson_overlap_length,
            golden_gate_enzyme=golden_gate_enzyme,
            golden_gate_overhangs=golden_gate_overhangs,
        )
        readiness = evaluate_readiness(
            design,
            assembly_report=assembly.report,
            assembly_plan=plan,
        )
        return {
            "ok": not plan.blockers,
            "assembly": assembly.to_dict(),
            "plan": plan.to_dict(),
            "readiness": readiness.to_dict(),
        }


class RunService:
    def __init__(self, run_store: RunStore):
        self.run_store = run_store

    def start(self, request: dict[str, Any]) -> dict[str, Any]:
        return start_design_run(
            user_intent=str(request.get("user_intent") or ""),
            host_organism=str(
                request.get("host_organism") or "Escherichia coli"
            ),
            compute_budget=int(request.get("compute_budget") or 6),
            enable_rag=bool(request.get("enable_rag", True)),
            enable_ode=bool(request.get("enable_ode", True)),
            enable_skill_extraction=bool(
                request.get("enable_skill_extraction", True)
            ),
            monte_carlo_samples=int(request.get("monte_carlo_samples") or 1),
            model_name=_optional_string(request.get("model_name")),
            api_base=_optional_string(request.get("api_base")),
            cello_command=_optional_string(request.get("cello_command")),
            ucf_path=_optional_string(request.get("ucf_path")),
            run_store=self.run_store,
        )

    def status(self, run_id: str) -> dict[str, Any]:
        return get_design_run_status(_validated_run_id(run_id), run_store=self.run_store)

    def events(
        self,
        run_id: str,
        *,
        after_event_id: int = 0,
        limit: int = 100,
    ) -> dict[str, Any]:
        return get_design_run_events(
            _validated_run_id(run_id),
            after_event_id=after_event_id,
            limit=limit,
            run_store=self.run_store,
        )

    def result(self, run_id: str) -> dict[str, Any]:
        return get_design_run_result(_validated_run_id(run_id), run_store=self.run_store)

    def list(self, limit: int = 20) -> dict[str, Any]:
        return list_design_runs(limit=limit, run_store=self.run_store)

    def cancel(self, run_id: str) -> dict[str, Any]:
        return cancel_design_run(_validated_run_id(run_id), run_store=self.run_store)

    def artifacts(self, run_id: str) -> dict[str, Any]:
        return get_design_run_artifacts(_validated_run_id(run_id), run_store=self.run_store)

    def submit_feedback(
        self,
        run_id: str,
        constraints: list[str] | str,
        *,
        action: str = "repair",
        extra_budget: int = 2,
    ) -> dict[str, Any]:
        return submit_design_feedback(
            _validated_run_id(run_id),
            constraints,
            action=action,
            extra_budget=extra_budget,
            run_store=self.run_store,
        )

    def resume(
        self,
        run_id: str,
        *,
        model_name: str | None = None,
        api_base: str | None = None,
    ) -> dict[str, Any]:
        return resume_design_run(
            _validated_run_id(run_id),
            model_name=model_name,
            api_base=api_base,
            run_store=self.run_store,
        )


@dataclass
class ApplicationServices:
    imports: ImportService
    designs: DesignService
    comparisons: ComparisonService
    evaluations: EvaluationService
    simulations: SimulationService
    research: ResearchService
    exports: ExportService
    backbones: BackboneRegistryService
    plasmid_assemblies: PlasmidAssemblyService
    assembly_plans: AssemblyPlanningService
    runs: RunService

    @property
    def storage_backend(self) -> str:
        return repository_backend(self.designs.repository)


def create_application_services(
    base_dir: str | Path | None = None,
) -> ApplicationServices:
    selected = Path(base_dir) if base_dir else DEFAULT_API_DATA_DIR
    draft_repository = JsonRepository(selected / "drafts")
    benchmark_repository = JsonRepository(selected / "benchmark_runs")
    backbone_repository = JsonRepository(selected / "backbones")
    design_repository = create_design_repository(selected / "research.db")
    designs = DesignService(design_repository)
    _migrate_legacy_design_repository(selected / "designs", designs)
    run_store = RunStore(base_dir=selected / "runs")
    simulation_service = SimulationService()
    backbones = BackboneRegistryService(backbone_repository)
    plasmid_assemblies = PlasmidAssemblyService(designs, backbones)
    research_run_store = RunStore(
        base_dir=selected / "research_runs",
        max_workers=2,
    )
    return ApplicationServices(
        imports=ImportService(draft_repository, designs),
        designs=designs,
        comparisons=ComparisonService(designs),
        evaluations=EvaluationService(
            benchmark_repository,
            selected / "benchmark_reports",
        ),
        simulations=simulation_service,
        research=ResearchService(
            designs=designs,
            simulations=simulation_service,
            run_store=research_run_store,
            report_dir=selected / "research_reports",
        ),
        exports=ExportService(designs),
        backbones=backbones,
        plasmid_assemblies=plasmid_assemblies,
        assembly_plans=AssemblyPlanningService(
            plasmid_assemblies,
            backbones,
        ),
        runs=RunService(run_store),
    )


@lru_cache(maxsize=1)
def get_default_services() -> ApplicationServices:
    return create_application_services()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _validated_run_id(run_id: str) -> str:
    selected = str(run_id or "").strip()
    if not SAFE_RUN_ID.fullmatch(selected):
        raise ValueError("Invalid run ID.")
    return selected


def _migrate_legacy_design_repository(
    legacy_dir: Path,
    designs: DesignService,
) -> None:
    if not legacy_dir.exists():
        return
    legacy = JsonRepository(legacy_dir)
    for payload in legacy.list():
        design_id = str(payload.get("design_id") or "").strip()
        if not design_id or designs.repository.exists(design_id):
            continue
        designs.save(design_ir_from_dict(payload))
