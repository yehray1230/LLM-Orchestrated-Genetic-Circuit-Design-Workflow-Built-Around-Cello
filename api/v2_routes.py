from __future__ import annotations

from typing import Any

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import get_services
from api.v2_schemas import ResearchComparisonRequest, ResearchSimulationRequest
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
