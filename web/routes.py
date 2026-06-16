from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Annotated, Any
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from api.dependencies import get_services
from application.services import ApplicationServices
from schemas.import_draft import FieldEvidence, ImportDraft


router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)
TERMINAL_RUN_STATUSES = {
    "completed",
    "needs_human_input",
    "error",
    "failed",
    "cancelled",
}


@router.get("/", response_class=HTMLResponse)
@router.get("/web", response_class=HTMLResponse)
def dashboard(
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    designs = services.designs.list()
    run_data = services.runs.list(limit=5)
    runs = run_data.get("runs", []) if isinstance(run_data, dict) else []
    return _template(
        request,
        "dashboard.html",
        designs=designs,
        runs=runs,
        design_count=len(designs),
        active_run_count=sum(
            str(item.get("status")) not in TERMINAL_RUN_STATUSES
            for item in runs
        ),
    )


@router.get("/web/designs", response_class=HTMLResponse)
def designs_page(
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    return _template(
        request,
        "designs.html",
        designs=services.designs.list(),
    )


@router.get("/web/assembly", response_class=HTMLResponse)
def assembly_workspace(
    request: Request,
    deliverable_id: str = "",
    services: ApplicationServices = Depends(get_services),
) -> Response:
    if deliverable_id:
        return RedirectResponse(
            f"/web/assembly/deliverables/{deliverable_id}",
            status_code=303,
        )
    return _assembly_template(request, services, "assembly.html")


@router.get("/web/assembly/backbones", response_class=HTMLResponse)
def assembly_backbones_page(
    request: Request,
    backbone: str = "",
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    return _assembly_template(
        request,
        services,
        "assembly_backbones.html",
        selected_backbone=backbone,
    )


@router.get("/web/assembly/new", response_class=HTMLResponse)
def assembly_new_page(
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    return _assembly_template(request, services, "assembly_new.html")


@router.post("/web/assembly/backbones")
async def upload_assembly_backbone(
    file: Annotated[UploadFile, File()],
    backbone_id: Annotated[str, Form()],
    version: Annotated[str, Form()],
    name: Annotated[str, Form()],
    source_uri: Annotated[str, Form()] = "",
    host_organisms: Annotated[str, Form()] = "Escherichia coli",
    origin_of_replication: Annotated[str, Form()] = "unknown",
    selection_marker: Annotated[str, Form()] = "unknown",
    copy_number_class: Annotated[str, Form()] = "unknown",
    insertion_region_id: Annotated[str, Form()] = "mcs",
    insertion_region_name: Annotated[str, Form()] = "Insertion region",
    insertion_start: Annotated[int, Form()] = 0,
    insertion_end: Annotated[int, Form()] = 1,
    essential_regions_json: Annotated[str, Form()] = "[]",
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(status_code=413, detail="Upload exceeds 5 MB.")
    try:
        essential_regions = json.loads(essential_regions_json or "[]")
        if not isinstance(essential_regions, list):
            raise ValueError("Essential regions must be a JSON array.")
        entry = services.backbones.register(
            {
                "backbone_id": backbone_id,
                "version": version,
                "name": name,
                "source_type": "user_upload",
                "source_uri": source_uri.strip()
                or f"upload://{file.filename or 'backbone.gb'}",
                "genbank": content.decode("utf-8-sig"),
                "host_organisms": _comma_list(host_organisms),
                "origin_of_replication": origin_of_replication,
                "selection_marker": selection_marker,
                "copy_number_class": copy_number_class,
                "insertion_regions": [
                    {
                        "region_id": insertion_region_id,
                        "name": insertion_region_name,
                        "start": insertion_start,
                        "end": insertion_end,
                        "description": "Registered from the HTML assembly workspace.",
                    }
                ],
                "essential_regions": essential_regions,
            }
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(
        f"/web/assembly/backbones?backbone={entry.backbone_id}@{entry.version}",
        status_code=303,
    )


@router.post("/web/assembly/deliverables")
def create_assembly_delivery(
    design_id: Annotated[str, Form()],
    plasmid_id: Annotated[str, Form()],
    backbone_id: Annotated[str, Form()],
    backbone_version: Annotated[str, Form()],
    insertion_region_id: Annotated[str, Form()],
    insertion_start: Annotated[int, Form()],
    insertion_end: Annotated[int, Form()],
    method: Annotated[str, Form()] = "gibson",
    restriction_enzymes: Annotated[str, Form()] = "EcoRI,BsaI,BsmBI",
    gibson_overlap_length: Annotated[int, Form()] = 25,
    golden_gate_enzyme: Annotated[str, Form()] = "BsaI",
    golden_gate_overhangs: Annotated[str, Form()] = "",
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    overhangs = _comma_list(golden_gate_overhangs)
    try:
        result = services.assembly_deliverables.create(
            design_id,
            plasmid_id=plasmid_id,
            backbone_id=backbone_id,
            backbone_version=backbone_version,
            insertion_region_id=insertion_region_id,
            insertion_start=insertion_start,
            insertion_end=insertion_end,
            method=method,
            restriction_enzymes=_comma_list(restriction_enzymes),
            gibson_overlap_length=gibson_overlap_length,
            golden_gate_enzyme=golden_gate_enzyme,
            golden_gate_overhangs=overhangs or None,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result.get("deliverable_id"):
        raise HTTPException(status_code=409, detail=result)
    return RedirectResponse(
        f"/web/assembly/deliverables/{result['deliverable_id']}",
        status_code=303,
    )


@router.get(
    "/web/assembly/deliverables/{deliverable_id}",
    response_class=HTMLResponse,
)
def assembly_report_page(
    deliverable_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    deliverable = services.assembly_deliverables.get(deliverable_id)
    if deliverable is None:
        raise HTTPException(status_code=404, detail="Assembly deliverable not found.")
    return _assembly_template(
        request,
        services,
        "assembly_report.html",
        deliverable=deliverable,
    )


@router.get(
    "/web/assembly/deliverables/{deliverable_id}/downloads",
    response_class=HTMLResponse,
)
def assembly_downloads_page(
    deliverable_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    deliverable = services.assembly_deliverables.get(deliverable_id)
    if deliverable is None:
        raise HTTPException(status_code=404, detail="Assembly deliverable not found.")
    return _assembly_template(
        request,
        services,
        "assembly_downloads.html",
        deliverable=deliverable,
    )


@router.get(
    "/web/assembly/deliverables/{deliverable_id}/artifacts/{artifact_key}"
)
def download_assembly_delivery(
    deliverable_id: str,
    artifact_key: str,
    services: ApplicationServices = Depends(get_services),
) -> FileResponse:
    artifact = services.assembly_deliverables.artifact(
        deliverable_id,
        artifact_key,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Assembly artifact not found.")
    path, media_type = artifact
    return FileResponse(path, filename=path.name, media_type=media_type)


@router.get("/web/benchmarks", response_class=HTMLResponse)
def benchmarks_page(
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    return _template(
        request,
        "benchmarks.html",
        profiles=services.evaluations.profiles(),
        datasets=services.evaluations.datasets(),
        runs=services.evaluations.benchmark_results(),
    )


@router.post("/web/benchmarks")
def start_benchmark(
    dataset_id: Annotated[str, Form()],
    profile_id: Annotated[str, Form()] = "research-v1.8",
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    try:
        result = services.evaluations.run_benchmark(
            dataset_id,
            profile_id=profile_id,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(
        f"/web/benchmarks/{result['benchmark_run_id']}",
        status_code=303,
    )


@router.get(
    "/web/benchmarks/{benchmark_run_id}",
    response_class=HTMLResponse,
)
def benchmark_detail(
    benchmark_run_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    result = services.evaluations.benchmark_result(benchmark_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")
    return _template(request, "benchmark_detail.html", benchmark=result)


@router.get("/web/designs/{design_id}", response_class=HTMLResponse)
def design_detail(
    design_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    design = services.designs.get(design_id)
    if design is None:
        raise HTTPException(status_code=404, detail="Design not found.")
    return _template(
        request,
        "design_detail.html",
        design=design,
        design_v2=services.designs.get_v2(design_id),
        simulation_spec=services.designs.simulation_spec(design_id),
        revisions=services.designs.revisions(design_id),
    )


@router.get("/web/research", response_class=HTMLResponse)
def research_workspace(
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    run_data = services.research.list(limit=50)
    return _template(
        request,
        "research.html",
        designs=services.designs.list_v2(),
        runs=run_data.get("runs", []),
        models=services.simulations.models(),
        profiles=services.evaluations.profiles(),
    )


@router.post("/web/research/runs")
def start_research_run(
    design_id: Annotated[str, Form()] = "",
    verilog: Annotated[str, Form()] = "",
    truth_table_json: Annotated[str, Form()] = "",
    copy_number: Annotated[float, Form()] = 1.0,
    simulation_time: Annotated[float, Form()] = 600.0,
    sample_count: Annotated[int, Form()] = 80,
    monte_carlo_samples: Annotated[int, Form()] = 1,
    noise_fraction: Annotated[float, Form()] = 0.15,
    random_seed: Annotated[str, Form()] = "",
    profile_id: Annotated[str, Form()] = "research-v2-preview",
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    topology = None
    if verilog.strip():
        try:
            truth_table = (
                json.loads(truth_table_json)
                if truth_table_json.strip()
                else []
            )
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Truth table must be valid JSON.",
            ) from exc
        topology = {
            "verilog": verilog.strip(),
            "truth_table": truth_table,
            "copy_number": copy_number,
        }
    payload = {
        "design_id": design_id.strip() or None,
        "topology": topology,
        "simulation_time": simulation_time,
        "sample_count": sample_count,
        "monte_carlo_samples": monte_carlo_samples,
        "noise_fraction": noise_fraction,
        "random_seed": int(random_seed) if random_seed.strip() else None,
        "profile_id": profile_id,
    }
    try:
        result = services.research.start_simulation(payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(
        f"/web/research/runs/{result['run_id']}",
        status_code=303,
    )


@router.get("/web/research/runs/{run_id}", response_class=HTMLResponse)
def research_run_detail(
    run_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    run = services.research.status(run_id)
    if run.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Research run not found.")
    terminal = run.get("status") in TERMINAL_RUN_STATUSES
    result = services.research.result(run_id) if terminal else None
    return _template(
        request,
        "research_run.html",
        run=run,
        result=result,
        terminal=terminal,
    )


@router.get("/web/research/compare", response_class=HTMLResponse)
def research_compare(
    request: Request,
    runs: str = "",
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    run_ids = [item.strip() for item in runs.split(",") if item.strip()]
    comparison = None
    error = None
    if len(run_ids) >= 2:
        try:
            comparison = services.research.compare(run_ids)
        except ValueError as exc:
            error = str(exc)
    return _template(
        request,
        "research_compare.html",
        runs=services.research.list(limit=50).get("runs", []),
        selected=run_ids,
        comparison=comparison,
        error=error,
    )


@router.get("/web/imports", response_class=HTMLResponse)
def imports_page(request: Request) -> HTMLResponse:
    return _template(request, "imports.html")


@router.post("/web/imports/guided")
def create_guided_import(
    name: Annotated[str, Form()],
    source_type: Annotated[str, Form()] = "literature",
    source_uri: Annotated[str, Form()] = "",
    citation: Annotated[str, Form()] = "",
    host_organism: Annotated[str, Form()] = "unknown",
    inputs: Annotated[str, Form()] = "",
    outputs: Annotated[str, Form()] = "",
    logic_expression: Annotated[str, Form()] = "",
    validation_status: Annotated[str, Form()] = "unknown",
    validation_notes: Annotated[str, Form()] = "",
    evidence_status: Annotated[str, Form()] = "unknown",
    locator: Annotated[str, Form()] = "",
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    draft = ImportDraft(
        draft_id=f"external_{uuid4().hex[:12]}",
        name=name.strip(),
        source_type=source_type.strip() or "literature",
        source_uri=source_uri.strip() or None,
        citation=citation.strip(),
        host_organism=host_organism.strip() or "unknown",
        inputs=_comma_list(inputs),
        outputs=_comma_list(outputs),
        logic_expression=logic_expression.strip(),
        validation_status=validation_status.strip() or "unknown",
        validation_notes=validation_notes.strip(),
        evidence=[
            FieldEvidence(
                field_path="design_summary",
                status=evidence_status,
                source_uri=source_uri.strip() or None,
                locator=locator.strip() or None,
            )
        ],
    )
    services.imports.save_draft(draft)
    return RedirectResponse(
        f"/web/imports/{draft.draft_id}",
        status_code=303,
    )


@router.post("/web/imports/upload")
async def upload_import(
    file: Annotated[UploadFile, File()],
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(status_code=413, detail="Upload exceeds 5 MB.")
    filename = file.filename or "external_design.json"
    try:
        if filename.lower().endswith(".json"):
            draft = services.imports.import_json(content)
        else:
            draft = services.imports.import_genbank(
                content,
                filename=filename,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(
        f"/web/imports/{draft.draft_id}",
        status_code=303,
    )


@router.get("/web/imports/{draft_id}", response_class=HTMLResponse)
def review_import(
    draft_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    draft = services.imports.get_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return _template(
        request,
        "import_review.html",
        draft=draft,
        validation=services.imports.validate(draft),
    )


@router.post("/web/imports/{draft_id}/confirm")
def confirm_import(
    draft_id: str,
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    try:
        design = services.imports.confirm_by_id(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Draft not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(
        f"/web/designs/{design.design_id}",
        status_code=303,
    )


@router.get("/web/runs", response_class=HTMLResponse)
def runs_page(
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    result = services.runs.list(limit=50)
    return _template(
        request,
        "runs.html",
        runs=result.get("runs", []),
    )


@router.get("/web/new-design", response_class=HTMLResponse)
def new_design_page(request: Request) -> HTMLResponse:
    return _template(request, "new_design.html")


@router.post("/web/runs")
def start_run(
    user_intent: Annotated[str, Form()],
    host_organism: Annotated[str, Form()] = "Escherichia coli",
    compute_budget: Annotated[int, Form()] = 6,
    model_name: Annotated[str, Form()] = "",
    enable_rag: Annotated[str | None, Form()] = None,
    enable_ode: Annotated[str | None, Form()] = None,
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    result = services.runs.start(
        {
            "user_intent": user_intent,
            "host_organism": host_organism,
            "compute_budget": compute_budget,
            "model_name": model_name or None,
            "enable_rag": enable_rag == "on",
            "enable_ode": enable_ode == "on",
        }
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return RedirectResponse(
        f"/web/runs/{result['run_id']}",
        status_code=303,
    )


@router.get("/web/runs/{run_id}", response_class=HTMLResponse)
def run_detail(
    run_id: str,
    request: Request,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    status = services.runs.status(run_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Run not found.")
    events = services.runs.events(run_id, limit=100).get("events", [])
    result = (
        services.runs.result(run_id)
        if status.get("status") in TERMINAL_RUN_STATUSES
        else None
    )
    return _template(
        request,
        "run_detail.html",
        run=status,
        events=events,
        result=result,
        monitor=_run_monitor_view(status, events, result),
        terminal=status.get("status") in TERMINAL_RUN_STATUSES,
    )


@router.get("/web/runs/{run_id}/status")
def run_monitor_status(
    run_id: str,
    after_event_id: int = 0,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, object]:
    payload = _run_monitor_payload(
        run_id,
        services,
        after_event_id=after_event_id,
    )
    if payload["run"].get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Run not found.")
    return payload


@router.post("/web/runs/{run_id}/feedback")
def run_feedback(
    run_id: str,
    constraints: Annotated[str, Form()],
    action: Annotated[str, Form()] = "repair",
    extra_budget: Annotated[int, Form()] = 2,
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    result = services.runs.submit_feedback(
        run_id,
        constraints,
        action=action,
        extra_budget=extra_budget,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return RedirectResponse(f"/web/runs/{run_id}", status_code=303)


@router.post("/web/runs/{run_id}/resume")
def run_resume(
    run_id: str,
    model_name: Annotated[str, Form()] = "",
    services: ApplicationServices = Depends(get_services),
) -> RedirectResponse:
    result = services.runs.resume(
        run_id,
        model_name=model_name or None,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    return RedirectResponse(
        f"/web/runs/{result['run_id']}",
        status_code=303,
    )


@router.get("/web/compare", response_class=HTMLResponse)
def compare_page(
    request: Request,
    left: str | None = None,
    right: str | None = None,
    services: ApplicationServices = Depends(get_services),
) -> HTMLResponse:
    designs = services.designs.list()
    comparison = None
    error = None
    if left and right and left != right:
        try:
            comparison = services.comparisons.compare(left, right)
        except KeyError:
            error = "One of the selected designs no longer exists."
    return _template(
        request,
        "compare.html",
        designs=designs,
        left=left,
        right=right,
        comparison=comparison,
        error=error,
    )


def _template(
    request: Request,
    name: str,
    **context: object,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"active_path": request.url.path, **context},
    )


def _run_monitor_payload(
    run_id: str,
    services: ApplicationServices,
    *,
    after_event_id: int = 0,
) -> dict[str, object]:
    status = services.runs.status(run_id)
    events = services.runs.events(
        run_id,
        after_event_id=after_event_id,
        limit=100,
    ).get("events", [])
    terminal = status.get("status") in TERMINAL_RUN_STATUSES
    result = services.runs.result(run_id) if terminal else None
    return {
        "run": status,
        "events": events,
        "result": result,
        "monitor": _run_monitor_view(status, events, result),
        "terminal": terminal,
        "next_poll_ms": None if terminal else 3000,
    }


def _run_monitor_view(
    status: dict[str, Any],
    events: list[dict[str, Any]],
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    latest_event = events[-1] if events else None
    return {
        "status_class": _status_class(str(status.get("status") or "")),
        "stage_class": _stage_class(str(status.get("stage") or "")),
        "latest_message": (
            latest_event.get("message")
            if isinstance(latest_event, dict)
            else status.get("error")
            or "No events have been recorded yet."
        ),
        "event_count": len(events),
        "events": [
            {
                **event,
                "stage_class": _stage_class(str(event.get("stage") or "")),
                "status_class": _status_class(str(event.get("status") or "")),
            }
            for event in events
        ],
        "score_summary": _score_summary(result),
        "score_breakdown": _score_breakdown(result),
        "topology_graph": _topology_graph(result),
        "ode_trace": _ode_trace_view(result),
        "search_tree": _search_tree_view(result),
    }


def _status_class(value: str) -> str:
    normalized = value.lower().replace(" ", "_")
    if normalized in {"completed", "pass", "ready"}:
        return "status-ready"
    if normalized in {"error", "failed", "cancelled", "dead_end"}:
        return "status-error"
    if normalized in {"needs_human_input", "warning", "review_required"}:
        return "status-warning"
    if normalized in {"running", "queued", "pending", "evaluated"}:
        return "status-active"
    return "status-neutral"


def _stage_class(value: str) -> str:
    normalized = value.lower()
    if "builder" in normalized or "translator" in normalized:
        return "stage-build"
    if "critic" in normalized or "evaluation" in normalized:
        return "stage-evaluate"
    if "consolidator" in normalized or "complete" in normalized:
        return "stage-complete"
    if "human" in normalized or "pause" in normalized:
        return "stage-human"
    return "stage-neutral"


def _score_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    source = _best_score_source(result)
    score = _score_like(
        result.get("score")
        or result.get("weighted_total_score")
        or source.get("score")
        or source.get("weighted_total_score")
    )
    return {
        "score": score,
        "grade": result.get("grade") or source.get("grade"),
        "mapping_status": source.get("mapping_status") or result.get("mapping_status"),
        "ode_status": source.get("ode_status") or result.get("ode_status"),
    }


def _score_breakdown(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    evaluation = result.get("evaluation")
    if isinstance(evaluation, dict) and isinstance(evaluation.get("dimension_scores"), dict):
        return [
            _score_item(key, value)
            for key, value in evaluation["dimension_scores"].items()
            if _score_like(value) is not None
        ]
    if isinstance(result.get("dimension_scores"), dict):
        return [
            _score_item(key, value)
            for key, value in result["dimension_scores"].items()
            if _score_like(value) is not None
        ]
    source = _best_score_source(result)
    items = []
    score_fields = [
        ("semantic_faithfulness_score", "Semantic faithfulness"),
        ("metabolic_burden_score", "Metabolic burden"),
        ("kinetic_score", "Kinetic"),
        ("robustness_score", "Robustness"),
        ("orthogonality_score", "Orthogonality"),
        ("cello_assignment_score", "Cello assignment"),
        ("toxicity_score", "Toxicity"),
    ]
    benchmark = source.get("benchmark_report")
    if not isinstance(benchmark, dict):
        benchmark = {}
    for key, label in score_fields:
        value = source.get(key, benchmark.get(key, result.get(key)))
        score = _score_like(value)
        if score is not None:
            items.append({"key": key, "label": label, "score": score, "percent": round(score * 100)})
    return items


def _best_score_source(result: dict[str, Any]) -> dict[str, Any]:
    direct = result.get("best_topology")
    if isinstance(direct, dict):
        return direct
    summary = result.get("summary")
    if isinstance(summary, dict) and isinstance(summary.get("best_topology"), dict):
        return summary["best_topology"]
    return result


def _topology_graph(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"nodes": [], "edges": [], "message": "Topology data is not available yet."}
    source = _best_score_source(result)
    graph = source.get("topology_graph") or source.get("graph")
    if isinstance(graph, dict):
        nodes = _normalize_graph_nodes(graph.get("nodes"))
        edges = _normalize_graph_edges(graph.get("edges"))
        if nodes:
            return {"nodes": nodes, "edges": edges, "message": ""}

    nodes = _normalize_graph_nodes(source.get("nodes"))
    edges = _normalize_graph_edges(source.get("edges"))
    if nodes:
        return {"nodes": nodes, "edges": edges, "message": ""}

    interactions = source.get("interactions")
    if isinstance(interactions, list):
        nodes, edges = _graph_from_interactions(interactions)
        if nodes:
            return {"nodes": nodes, "edges": edges, "message": ""}

    verilog = str(source.get("verilog") or result.get("verilog") or "")
    if verilog.strip():
        nodes, edges = _graph_from_verilog(verilog)
        if nodes:
            return {"nodes": nodes, "edges": edges, "message": ""}
    return {"nodes": [], "edges": [], "message": "No topology graph could be inferred."}


def _normalize_graph_nodes(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    nodes = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            node_id = str(item.get("id") or item.get("node_id") or item.get("name") or f"node_{index}")
            label = str(item.get("label") or item.get("name") or node_id)
            node_type = str(item.get("type") or item.get("part_type") or "signal")
        else:
            node_id = str(item)
            label = node_id
            node_type = "signal"
        if node_id.strip():
            nodes.append({"id": node_id, "label": label, "type": node_type})
    return nodes


def _normalize_graph_edges(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    edges = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or item.get("from") or "").strip()
        target = str(item.get("target") or item.get("to") or "").strip()
        if source and target:
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "label": str(item.get("label") or item.get("type") or ""),
                }
            )
    return edges


def _graph_from_interactions(
    interactions: list[Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    node_ids: set[str] = set()
    edges = []
    for item in interactions:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").strip()
        target = str(item.get("target") or "").strip()
        if not source or not target:
            continue
        node_ids.update({source, target})
        edges.append(
            {
                "source": source,
                "target": target,
                "label": str(item.get("interaction_type") or item.get("label") or ""),
            }
        )
    nodes = [{"id": node_id, "label": node_id, "type": "part"} for node_id in sorted(node_ids)]
    return nodes, edges


def _graph_from_verilog(verilog: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    code = _strip_verilog_comments(verilog)
    assignments = re.findall(
        r"\bassign\s+([A-Za-z_]\w*)\s*=\s*([^;]+);",
        code,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not assignments:
        return [], []
    nodes_by_id: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []
    for index, (target, expression) in enumerate(assignments, start=1):
        logic_id = f"logic_{index}"
        nodes_by_id[logic_id] = {
            "id": logic_id,
            "label": _logic_label(expression),
            "type": "logic",
        }
        nodes_by_id[target] = {"id": target, "label": target, "type": "output"}
        edges.append({"source": logic_id, "target": target, "label": "drives"})
        for token in _expression_tokens(expression):
            nodes_by_id.setdefault(token, {"id": token, "label": token, "type": "input"})
            edges.append({"source": token, "target": logic_id, "label": ""})
    return list(nodes_by_id.values()), edges


def _strip_verilog_comments(value: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
    return re.sub(r"//.*", "", without_block)


def _expression_tokens(expression: str) -> list[str]:
    reserved = {"assign", "and", "or", "not", "module", "endmodule", "input", "output", "wire"}
    tokens = re.findall(r"\b[A-Za-z_]\w*\b", expression)
    return list(dict.fromkeys(token for token in tokens if token.lower() not in reserved))


def _logic_label(expression: str) -> str:
    compact = " ".join(expression.strip().split())
    if not compact:
        return "logic"
    if len(compact) > 34:
        return f"{compact[:31]}..."
    return compact


def _ode_trace_view(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"status": "unavailable", "series": [], "metrics": [], "message": "ODE trace is not available yet."}
    source = _best_score_source(result)
    trace = source.get("ode_trace")
    if not isinstance(trace, dict):
        trace = result.get("ode_trace")
    if not _valid_ode_trace(trace):
        return {
            "status": str(source.get("ode_status") or result.get("ode_status") or "unavailable"),
            "series": [],
            "metrics": _ode_metrics(source),
            "message": "No saved ODE time series was found for this run.",
        }
    return {
        "status": str(source.get("ode_status") or "simulated"),
        "series": _ode_series(trace),
        "metrics": _ode_metrics(source),
        "message": "",
    }


def _valid_ode_trace(trace: Any) -> bool:
    if not isinstance(trace, dict):
        return False
    time_values = trace.get("time")
    output_values = trace.get("output_protein")
    return (
        isinstance(time_values, list)
        and isinstance(output_values, list)
        and len(time_values) == len(output_values)
        and len(time_values) > 0
    )


def _ode_series(trace: dict[str, Any]) -> list[dict[str, Any]]:
    series = []
    for key, label in [
        ("output_protein", "Output protein"),
        ("total_mrna", "Total mRNA"),
        ("total_protein", "Total protein"),
        ("rnap_occupancy", "RNAP occupancy"),
        ("ribosome_occupancy", "Ribosome occupancy"),
    ]:
        values = trace.get(key)
        if isinstance(values, list) and values:
            points = _sparkline_points(trace.get("time", []), values)
            if points:
                series.append({"key": key, "label": label, "points": points})
    return series


def _sparkline_points(time_values: Any, values: list[Any]) -> str:
    pairs = []
    for index, raw_value in enumerate(values):
        try:
            y_value = float(raw_value)
            x_value = float(time_values[index]) if isinstance(time_values, list) and index < len(time_values) else float(index)
        except (TypeError, ValueError):
            continue
        pairs.append((x_value, y_value))
    if not pairs:
        return ""
    min_x = min(x for x, _ in pairs)
    max_x = max(x for x, _ in pairs)
    min_y = min(y for _, y in pairs)
    max_y = max(y for _, y in pairs)
    x_span = max(max_x - min_x, 1e-9)
    y_span = max(max_y - min_y, 1e-9)
    points = []
    for x_value, y_value in pairs:
        x_pos = ((x_value - min_x) / x_span) * 100
        y_pos = 36 - ((y_value - min_y) / y_span) * 30 - 3
        points.append(f"{x_pos:.2f},{y_pos:.2f}")
    return " ".join(points)


def _ode_metrics(source: dict[str, Any]) -> list[dict[str, str]]:
    items = []
    for key, label in [
        ("dynamic_margin", "Dynamic margin"),
        ("signal_to_noise_ratio", "SNR"),
        ("metrics_cv", "Output CV"),
        ("monte_carlo_runs", "MC runs"),
    ]:
        value = source.get(key)
        if value is not None:
            items.append({"label": label, "value": _format_monitor_value(value)})
    return items


def _search_tree_view(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"nodes": [], "branches": [], "path": [], "message": "Search history is not available yet."}
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    nodes = _normalize_search_nodes(summary.get("tree_summary") or result.get("tree_summary"))
    if not nodes:
        nodes = _normalize_search_nodes(result.get("search_tree"))
    if not nodes:
        return {"nodes": [], "branches": [], "path": [], "message": "No search tree was recorded for this run."}
    node_by_id = {node["node_id"]: node for node in nodes}
    branches = [
        {
            "source": node["parent_id"],
            "target": node["node_id"],
            "label": node["search_mode"],
        }
        for node in nodes
        if node.get("parent_id") in node_by_id
    ]
    current_id = str(summary.get("current_node_id") or result.get("current_node_id") or nodes[-1]["node_id"])
    path = _search_path(nodes, current_id)
    return {"nodes": nodes, "branches": branches, "path": path, "message": ""}


def _normalize_search_nodes(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    nodes = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id") or item.get("id") or f"node_{index}").strip()
        if not node_id:
            continue
        score = _score_like(item.get("score"))
        nodes.append(
            {
                "node_id": node_id,
                "parent_id": str(item.get("parent_id") or "").strip(),
                "search_mode": str(item.get("search_mode") or item.get("mode") or "Exploration"),
                "status": str(item.get("status") or "unknown"),
                "score": score,
                "score_label": "-" if score is None else f"{score:.3f}",
                "error_type": str(item.get("error_type") or "NONE"),
                "critic_feedback": str(item.get("critic_feedback") or item.get("feedback") or ""),
            }
        )
    return nodes


def _search_path(nodes: list[dict[str, Any]], current_id: str) -> list[dict[str, Any]]:
    node_by_id = {node["node_id"]: node for node in nodes}
    path = []
    seen: set[str] = set()
    selected = current_id if current_id in node_by_id else nodes[-1]["node_id"]
    while selected and selected in node_by_id and selected not in seen:
        seen.add(selected)
        node = node_by_id[selected]
        path.append(node)
        selected = str(node.get("parent_id") or "")
    return list(reversed(path))


def _format_monitor_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _score_item(key: str, value: Any) -> dict[str, Any]:
    score = _score_like(value)
    assert score is not None
    return {
        "key": key,
        "label": str(key).replace("_", " ").title(),
        "score": score,
        "percent": round(score * 100),
    }


def _score_like(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0:
        return None
    if score > 1 and score <= 100:
        score = score / 100
    return max(0.0, min(1.0, score))


def _assembly_template(
    request: Request,
    services: ApplicationServices,
    name: str,
    *,
    deliverable: dict[str, object] | None = None,
    selected_backbone: str = "",
) -> HTMLResponse:
    return _template(
        request,
        name,
        designs=services.designs.list_v2(),
        backbones=[item.to_dict() for item in services.backbones.list()],
        deliverable=deliverable,
        selected_backbone=selected_backbone,
    )


def _comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
