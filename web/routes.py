from __future__ import annotations

from pathlib import Path
import json
from typing import Annotated
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
from fastapi.responses import HTMLResponse, RedirectResponse
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
        terminal=status.get("status") in TERMINAL_RUN_STATUSES,
    )


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


def _comma_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
