from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from schemas.readiness import ReadinessResult
from benchmark_suite.readiness_evaluator import evaluate_readiness
from application.services import ApplicationServices

@dataclass
class DesignContextView:
    design_id: str
    name: str
    is_historical: bool
    viewed_rev: int
    latest_rev: int
    
    # Biological info
    host_organism: str
    chassis: str
    parts_count: int
    inputs_count: int
    outputs_count: int
    
    # Provenance
    source_run_id: str | None
    source_candidate_index: int | None
    topology_hash: str | None
    is_legacy: bool
    
    # Validation / Warning / Readiness
    readiness: ReadinessResult
    warnings: list[str]
    blockers: list[dict[str, Any]]
    
    # Revisions history list
    revisions: list[dict[str, Any]]
    
    # Sub-navigation capabilities / locks
    can_simulate: bool
    can_optimize: bool
    can_assemble: bool
    can_export: bool
    
    # Locks reason / unlock descriptions
    simulate_lock_reason: str | None = None
    optimize_lock_reason: str | None = None
    assemble_lock_reason: str | None = None
    export_lock_reason: str | None = None
    
    # Recent artifacts
    recent_deliverable_id: str | None = None
    recent_simulation_run_id: str | None = None
    
    # Stage G fields
    is_archived: bool = False
    is_deleted: bool = False
    is_pinned: bool = False


def build_design_context_view(
    design_id: str,
    viewed_rev_num: int | None,
    services: ApplicationServices,
) -> DesignContextView:
    # 1. Fetch revisions list
    revisions = services.designs.revisions(design_id) or []
    latest_rev = 1
    if revisions:
        latest_rev = max(r.get("revision_number", 1) for r in revisions)
        
    # 2. Determine viewed revision number and load DesignIRV2
    if viewed_rev_num is None:
        viewed_rev = latest_rev
        design_v2 = services.designs.get_v2(design_id)
    else:
        viewed_rev = viewed_rev_num
        design_v2 = services.designs.get_revision(design_id, viewed_rev)
        
    if design_v2 is None:
        raise ValueError(f"Design {design_id} (Revision {viewed_rev}) not found.")
        
    is_historical = (viewed_rev_num is not None)
    
    # 3. Evaluate readiness
    readiness = evaluate_readiness(design_v2)
    
    # 4. Extract provenance details
    source_run_id = None
    source_candidate_index = None
    topology_hash = None
    is_legacy = True
    
    if design_v2.provenance:
        for prov in design_v2.provenance:
            meta = prov.metadata or {}
            if meta.get("source_run_id"):
                source_run_id = meta.get("source_run_id")
                source_candidate_index = meta.get("source_candidate_index")
                topology_hash = meta.get("topology_hash")
                is_legacy = False
                break
                
    # 5. Biological parameters
    host_organism = design_v2.biological_context.host_organism.value or "Unknown"
    chassis = design_v2.biological_context.chassis.value or "Inherited from host"
    parts_count = len(design_v2.parts)
    inputs_count = len(design_v2.specification.inputs)
    outputs_count = len(design_v2.specification.outputs)
    
    # 6. Navigation locks
    # Simulation is unlocked if we have valid inputs/outputs and logic specification
    can_simulate = bool(design_v2.specification.inputs and design_v2.specification.outputs)
    simulate_lock_reason = None if can_simulate else "設計規範缺少輸入或輸出訊號，請先編輯輸入/輸出規格。"
    
    # Optimization is unlocked if chassis/host organism is defined and not a legacy/empty design
    can_optimize = bool(design_v2.parts)
    optimize_lock_reason = None if can_optimize else "設計中無零件，請先建立或推廣拓樸零件以解鎖最佳化。"
    
    # Assembly is unlocked if we have constructs/plasmids defined and primer/sequence quality checks pass
    # Let's check readiness status: assembly requires no blockers
    can_assemble = (readiness.readiness_status != "blocked" and bool(design_v2.constructs))
    if not design_v2.constructs:
        assemble_lock_reason = "設計尚未定義構造片段 (Genetic Constructs)，請先定義構造再裝配。"
    elif readiness.readiness_status == "blocked":
        assemble_lock_reason = "當前設計存在裝配阻擋因素 (Blockers)，請修復阻擋因素以解鎖裝配。"
    else:
        assemble_lock_reason = None
        
    # Export is unlocked if we have at least one part and it builds
    can_export = bool(design_v2.parts)
    export_lock_reason = None if can_export else "無零件資料，無法進行匯出。"
    
    # 7. Rollup blockers & warnings
    warnings_list = [w.message for w in readiness.warnings]
    blockers_list = [{"code": b.code, "message": b.message, "source": b.source} for b in readiness.blockers]
    
    # 8. Recent artifacts & simulation runs
    recent_deliverable_id = None
    try:
        all_deliverables = services.assembly_deliverables.repository.list()
        matching = [
            d for d in all_deliverables
            if d.get("assembly", {}).get("design_id") == design_id
        ]
        if matching:
            recent_deliverable_id = matching[-1].get("deliverable_id")
    except Exception:
        pass

    recent_simulation_run_id = None
    try:
        research_runs = services.research.list(limit=100).get("runs", [])
        matching_runs = [
            r for r in research_runs
            if r.get("summary", {}).get("design_id") == design_id or r.get("run_id", "").startswith("research_")
        ]
        if matching_runs:
            recent_simulation_run_id = matching_runs[0].get("run_id")
    except Exception:
        pass
    
    return DesignContextView(
        design_id=design_id,
        name=design_v2.name,
        is_historical=is_historical,
        viewed_rev=viewed_rev,
        latest_rev=latest_rev,
        host_organism=host_organism,
        chassis=chassis,
        parts_count=parts_count,
        inputs_count=inputs_count,
        outputs_count=outputs_count,
        source_run_id=source_run_id,
        source_candidate_index=source_candidate_index,
        topology_hash=topology_hash,
        is_legacy=is_legacy,
        readiness=readiness,
        warnings=warnings_list,
        blockers=blockers_list,
        revisions=revisions,
        can_simulate=can_simulate,
        can_optimize=can_optimize,
        can_assemble=can_assemble,
        can_export=can_export,
        simulate_lock_reason=simulate_lock_reason,
        optimize_lock_reason=optimize_lock_reason,
        assemble_lock_reason=assemble_lock_reason,
        export_lock_reason=export_lock_reason,
        recent_deliverable_id=recent_deliverable_id,
        recent_simulation_run_id=recent_simulation_run_id,
        is_archived=getattr(design_v2, "is_archived", False),
        is_deleted=getattr(design_v2, "is_deleted", False),
        is_pinned=getattr(design_v2, "is_pinned", False),
    )
