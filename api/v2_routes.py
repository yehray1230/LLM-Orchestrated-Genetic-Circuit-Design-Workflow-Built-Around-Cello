from __future__ import annotations

from typing import Any

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import get_services
from api.v2_schemas import (
    AssemblyPlanRequest,
    BackboneRegistrationRequest,
    PlasmidAssemblyRequest,
    ResearchComparisonRequest,
    ResearchSimulationRequest,
)
from application.services import ApplicationServices


router = APIRouter(prefix="/api/v2")


def envelope(data: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {"api_version": "v2", "schema_version": "2.0"},
        "warnings": warnings or [],
    }


@router.get("/health")
def health(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    return envelope(
        {
            "status": "ok",
            "service": "genetic-circuit-research-api",
            "storage_backend": services.storage_backend,
        }
    )


@router.post("/designs/{design_id}/plasmid-assemblies")
def assemble_plasmid(
    design_id: str,
    request: PlasmidAssemblyRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.plasmid_assemblies.assemble(
            design_id,
            plasmid_id=request.plasmid_id,
            backbone_id=request.backbone_id,
            backbone_version=request.backbone_version,
            insertion_region_id=request.insertion_region_id,
            insertion_start=request.insertion_start,
            insertion_end=request.insertion_end,
            assembly_method=request.assembly_method,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Design not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result.ok:
        raise HTTPException(
            status_code=409,
            detail={
                "message": result.report.status,
                "report": result.report.to_dict(),
            },
        )
    return envelope(result.to_dict())


@router.post("/backbones", status_code=status.HTTP_201_CREATED)
def register_backbone(
    request: BackboneRegistrationRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        entry = services.backbones.register(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(entry.to_dict())


@router.get("/backbones")
def list_backbones(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    entries = services.backbones.list()
    return envelope(
        {
            "items": [entry.to_dict() for entry in entries],
            "count": len(entries),
        }
    )


@router.get("/backbones/{backbone_id}/versions/{version}")
def get_backbone(
    backbone_id: str,
    version: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    entry = services.backbones.get(backbone_id, version)
    if entry is None:
        raise HTTPException(status_code=404, detail="Backbone not found.")
    return envelope(entry.to_dict())


@router.post("/designs/{design_id}/assembly-plans")
def create_plasmid_assembly_plan(
    design_id: str,
    request: AssemblyPlanRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.assembly_plans.plan(
            design_id,
            **request.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Design not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result)
    return envelope(result)


@router.post("/research/runs", status_code=status.HTTP_202_ACCEPTED)
def start_research_run(
    request: ResearchSimulationRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.research.start_simulation(request.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Design not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(result)


@router.get("/research/runs")
def list_research_runs(
    limit: int = 50,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    return envelope(services.research.list(limit=limit))


@router.get("/research/runs/{run_id}")
def get_research_run(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    result = services.research.status(run_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Research run not found.")
    return envelope(result)


@router.get("/research/runs/{run_id}/result")
def get_research_result(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    result = services.research.result(run_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Research run not found.")
    return envelope(result)


@router.get("/research/runs/{run_id}/artifacts/{artifact_key}")
def get_research_artifact(
    run_id: str,
    artifact_key: str,
    services: ApplicationServices = Depends(get_services),
) -> FileResponse:
    result = services.research.result(run_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Research run not found.")
    artifacts = result.get("artifacts")
    path_value = artifacts.get(artifact_key) if isinstance(artifacts, dict) else None
    if not path_value:
        raise HTTPException(status_code=404, detail="Research artifact not found.")
    path = Path(str(path_value)).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Research artifact not found.")
    return FileResponse(path, filename=path.name)


@router.post("/research/runs/{run_id}/cancel")
def cancel_research_run(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    result = services.research.cancel(run_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Research run not found.")
    return envelope(result)


@router.post("/research/comparisons")
def compare_research_runs(
    request: ResearchComparisonRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.research.compare(request.research_run_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return envelope(result)
