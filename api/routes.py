from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.dependencies import get_services
from api.schemas import (
    BenchmarkComparisonRequest,
    BenchmarkRunRequest,
    ComparisonRequest,
    EvaluationRequest,
    GenBankImportRequest,
    ImportDraftRequest,
    JsonImportRequest,
    ParameterFitRequest,
    ParameterFitSnapshotComparisonRequest,
    RunFeedbackRequest,
    RunResumeRequest,
    RunStartRequest,
    SimulationRequest,
    SimulationComparisonRequest,
    ParameterSweepRequest,
    BifurcationSweepRequest,
    temporal_inputs_to_dict,
)
from application.services import ApplicationServices
from mcp_server.service import list_tool_capabilities
from repositories.json_repository import RepositoryError
from schemas.import_draft import import_draft_from_json


router = APIRouter(prefix="/api/v1")


def envelope(data: Any, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {"api_version": "v1", "schema_version": "1.0"},
        "warnings": warnings or [],
    }


@router.get("/health")
def health() -> dict[str, Any]:
    return envelope({"status": "ok", "service": "genetic-circuit-api"})


@router.get("/tool-capabilities")
def get_tool_capabilities() -> dict[str, Any]:
    return envelope(list_tool_capabilities())


@router.post("/imports/drafts/validate")
def validate_draft(
    request: ImportDraftRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    draft = import_draft_from_json(request.model_dump())
    return envelope(services.imports.validate(draft))


@router.post("/imports/json", status_code=status.HTTP_201_CREATED)
def import_json(
    request: JsonImportRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        draft = services.imports.import_json(request.draft.model_dump())
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("IMPORT_INVALID", str(exc)) from exc
    validation = services.imports.validate(draft)
    return envelope(
        {"draft": draft.to_dict(), "validation": validation},
        validation["warnings"],
    )


@router.post("/imports/genbank", status_code=status.HTTP_201_CREATED)
def import_genbank(
    request: GenBankImportRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        draft = services.imports.import_genbank(
            request.content,
            filename=request.filename,
        )
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("GENBANK_IMPORT_INVALID", str(exc)) from exc
    validation = services.imports.validate(draft)
    return envelope(
        {"draft": draft.to_dict(), "validation": validation},
        validation["warnings"],
    )


@router.post("/imports/{draft_id}/confirm", status_code=status.HTTP_201_CREATED)
def confirm_import(
    draft_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        design = services.imports.confirm_by_id(draft_id)
    except KeyError as exc:
        raise _not_found("DRAFT_NOT_FOUND", draft_id) from exc
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("IMPORT_VALIDATION_FAILED", str(exc)) from exc
    return envelope(design.to_dict(), design.warnings)


@router.get("/designs")
def list_designs(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    designs = services.designs.list()
    return envelope(
        {
            "items": [design.to_dict() for design in designs],
            "count": len(designs),
        }
    )


@router.get("/designs/{design_id}")
def get_design(
    design_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        design = services.designs.get(design_id)
    except RepositoryError as exc:
        raise _bad_request("INVALID_DESIGN_ID", str(exc)) from exc
    if design is None:
        raise _not_found("DESIGN_NOT_FOUND", design_id)
    return envelope(design.to_dict(), design.warnings)


@router.get("/designs/{design_id}/ir-v2")
def get_design_ir_v2(
    design_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        design = services.designs.get_v2(design_id)
    except RepositoryError as exc:
        raise _bad_request("INVALID_DESIGN_ID", str(exc)) from exc
    if design is None:
        raise _not_found("DESIGN_NOT_FOUND", design_id)
    return envelope(
        design.to_dict(),
        ["This endpoint exposes the DesignIR v2 storage contract."],
    )


@router.get("/designs/{design_id}/simulation-spec")
def get_design_simulation_spec(
    design_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        spec = services.designs.simulation_spec(design_id)
    except RepositoryError as exc:
        raise _bad_request("INVALID_DESIGN_ID", str(exc)) from exc
    if spec is None:
        raise _not_found("DESIGN_NOT_FOUND", design_id)
    return envelope(
        spec,
        ["This is a computational simulation configuration, not an experimental protocol."],
    )


@router.get("/designs/{design_id}/revisions")
def list_design_revisions(
    design_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        if services.designs.get_v2(design_id) is None:
            raise _not_found("DESIGN_NOT_FOUND", design_id)
        revisions = services.designs.revisions(design_id)
    except RepositoryError as exc:
        raise _bad_request("INVALID_DESIGN_ID", str(exc)) from exc
    return envelope({"items": revisions, "count": len(revisions)})


@router.post("/comparisons")
def compare(
    request: ComparisonRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.comparisons.compare(
            request.left_design_id,
            request.right_design_id,
            left_metrics=request.left_metrics,
            right_metrics=request.right_metrics,
        )
    except KeyError as exc:
        raise _not_found("DESIGN_NOT_FOUND", str(exc.args[0])) from exc
    except RepositoryError as exc:
        raise _bad_request("INVALID_DESIGN_ID", str(exc)) from exc
    return envelope(result)


@router.post("/evaluations")
def evaluate(
    request: EvaluationRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.evaluations.evaluate(
            request.candidate,
            profile_id=request.profile_id,
        )
    except ValueError as exc:
        raise _bad_request("SCORING_PROFILE_INVALID", str(exc)) from exc
    return envelope(result)


@router.get("/evaluation/profiles")
def list_evaluation_profiles(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    profiles = services.evaluations.profiles()
    return envelope({"items": profiles, "count": len(profiles)})


@router.get("/simulation/models")
def list_simulation_models(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    models = services.simulations.models()
    return envelope({"items": models, "count": len(models)})


@router.post("/simulations")
def simulate_candidate(
    request: SimulationRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        topology = request.topology
        if request.parameter_fit_snapshot_id:
            snapshot = services.evaluations.parameter_fit_snapshot(
                request.parameter_fit_snapshot_id
            )
            if not snapshot:
                raise ValueError(
                    f"Parameter fit snapshot '{request.parameter_fit_snapshot_id}' not found."
                )
            topology = services.simulations.apply_parameter_fit_snapshot(
                topology, snapshot
            )
        result = services.simulations.simulate(
            topology,
            simulation_time=request.simulation_time,
            sample_count=request.sample_count,
            monte_carlo_samples=request.monte_carlo_samples,
            noise_fraction=request.noise_fraction,
            random_seed=request.random_seed,
            host_profile_id=request.host_profile_id,
            temporal_inputs=temporal_inputs_to_dict(request.temporal_inputs),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _bad_request("SIMULATION_INVALID", str(exc)) from exc
    return envelope(
        result,
        ["Simulation outputs are screening estimates and require experimental validation."],
    )


@router.post("/simulations/compare-snapshot")
def compare_simulation_snapshot(
    request: SimulationComparisonRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.simulations.compare_default_vs_fitted(
            request.topology,
            request.parameter_fit_snapshot_id,
            simulation_time=request.simulation_time,
            sample_count=request.sample_count,
            monte_carlo_samples=request.monte_carlo_samples,
            noise_fraction=request.noise_fraction,
            random_seed=request.random_seed,
            host_profile_id=request.host_profile_id,
            temporal_inputs=temporal_inputs_to_dict(request.temporal_inputs),
        )
    except KeyError as exc:
        raise _not_found("PARAMETER_FIT_NOT_FOUND", str(exc.args[0])) from exc
    except (TypeError, ValueError) as exc:
        raise _bad_request("SIMULATION_INVALID", str(exc)) from exc
    return envelope(
        result,
        ["Simulation comparisons are computational estimates and require experimental validation."],
    )


@router.post("/simulations/sweep")
def parameter_sweep(
    request: ParameterSweepRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    from tools.sensitivity_analysis import run_parameter_sweep
    try:
        result = run_parameter_sweep(
            request.topology,
            request.parameter_name,
            request.sweep_values,
            host_profile_id=request.host_profile_id,
            host_profiles=services.simulations.host_profiles,
        )
    except Exception as exc:
        raise _bad_request("SWEEP_INVALID", str(exc)) from exc
    return envelope(result)


@router.post("/simulations/bifurcation")
def bifurcation_sweep(
    request: BifurcationSweepRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    from tools.sensitivity_analysis import run_bifurcation_sweep
    try:
        result = run_bifurcation_sweep(
            request.topology,
            request.input_name,
            request.input_values,
            host_profile_id=request.host_profile_id,
            host_profiles=services.simulations.host_profiles,
        )
    except Exception as exc:
        raise _bad_request("SWEEP_INVALID", str(exc)) from exc
    return envelope(result)


@router.get("/benchmarks/datasets")
def list_benchmark_dataset_records(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    datasets = services.evaluations.datasets()
    return envelope({"items": datasets, "count": len(datasets)})


@router.get("/benchmarks/datasets/{dataset_id}")
def get_benchmark_dataset(
    dataset_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        dataset = services.evaluations.dataset(dataset_id)
    except KeyError as exc:
        raise _not_found("BENCHMARK_DATASET_NOT_FOUND", dataset_id) from exc
    except ValueError as exc:
        raise _bad_request("BENCHMARK_DATASET_INVALID", str(exc)) from exc
    return envelope(dataset)


@router.post("/benchmarks/runs", status_code=status.HTTP_201_CREATED)
def run_benchmark(
    request: BenchmarkRunRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.evaluations.run_benchmark(
            request.dataset_id,
            profile_id=request.profile_id,
        )
    except KeyError as exc:
        raise _not_found(
            "BENCHMARK_DATASET_NOT_FOUND",
            request.dataset_id,
        ) from exc
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("BENCHMARK_RUN_INVALID", str(exc)) from exc
    return envelope(result)


@router.get("/benchmarks/runs")
def list_benchmark_runs(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    runs = services.evaluations.benchmark_results()
    return envelope({"items": runs, "count": len(runs)})


@router.get("/benchmarks/runs/{benchmark_run_id}")
def get_benchmark_run(
    benchmark_run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.evaluations.benchmark_result(benchmark_run_id)
    except RepositoryError as exc:
        raise _bad_request("BENCHMARK_RUN_ID_INVALID", str(exc)) from exc
    if result is None:
        raise _not_found("BENCHMARK_RUN_NOT_FOUND", benchmark_run_id)
    return envelope(result)


@router.post("/benchmarks/comparisons")
def compare_benchmark_results(
    request: BenchmarkComparisonRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.evaluations.compare_benchmarks(
            request.benchmark_run_ids
        )
    except KeyError as exc:
        raise _not_found("BENCHMARK_RUN_NOT_FOUND", str(exc.args[0])) from exc
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("BENCHMARK_COMPARISON_INVALID", str(exc)) from exc
    return envelope(result)


@router.post("/benchmarks/parameter-fits", status_code=status.HTTP_201_CREATED)
def create_parameter_fit_snapshot(
    request: ParameterFitRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.evaluations.create_parameter_fit_snapshot(
            request.model_dump()
        )
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("PARAMETER_FIT_INVALID", str(exc)) from exc
    return envelope(result, [warning["message"] for warning in result.get("warnings", [])])


@router.get("/benchmarks/parameter-fits")
def list_parameter_fit_snapshots(
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    items = services.evaluations.parameter_fit_snapshots()
    return envelope({"items": items, "count": len(items)})


@router.get("/benchmarks/parameter-fits/{snapshot_id}")
def get_parameter_fit_snapshot(
    snapshot_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.evaluations.parameter_fit_snapshot(snapshot_id)
    except RepositoryError as exc:
        raise _bad_request("PARAMETER_FIT_ID_INVALID", str(exc)) from exc
    if result is None:
        raise _not_found("PARAMETER_FIT_NOT_FOUND", snapshot_id)
    warnings = [
        warning["message"]
        for warning in result.get("warnings", [])
        if isinstance(warning, dict) and warning.get("message")
    ]
    return envelope(result, warnings)


@router.post("/benchmarks/parameter-fits/{snapshot_id}/comparison")
def create_parameter_fit_snapshot_comparison(
    snapshot_id: str,
    request: ParameterFitSnapshotComparisonRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.simulations.compare_default_vs_fitted(
            request.topology,
            snapshot_id,
            simulation_time=request.simulation_time,
            sample_count=request.sample_count,
            monte_carlo_samples=request.monte_carlo_samples,
            noise_fraction=request.noise_fraction,
            random_seed=request.random_seed,
            host_profile_id=request.host_profile_id,
            temporal_inputs=temporal_inputs_to_dict(request.temporal_inputs),
        )
    except KeyError as exc:
        raise _not_found("PARAMETER_FIT_NOT_FOUND", str(exc.args[0])) from exc
    except (TypeError, ValueError) as exc:
        raise _bad_request("SIMULATION_INVALID", str(exc)) from exc
    return envelope(
        result,
        [
            "Snapshot comparison reports are computational estimates and require experimental validation."
        ],
    )


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(
    request: RunStartRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    result = services.runs.start(request.model_dump())
    _raise_run_error(result)
    return envelope(result)


@router.get("/runs")
def list_runs(
    limit: int = 20,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    result = services.runs.list(limit=limit)
    _raise_run_error(result)
    return envelope(result)


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.status(run_id)
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.get("/runs/{run_id}/events")
def get_run_events(
    run_id: str,
    after_event_id: int = 0,
    limit: int = 100,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.events(
            run_id,
            after_event_id=after_event_id,
            limit=limit,
        )
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.get("/runs/{run_id}/result")
def get_run_result(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.result(run_id)
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.get("/runs/{run_id}/artifacts")
def get_run_artifacts(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.artifacts(run_id)
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: str,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.cancel(run_id)
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.post("/runs/{run_id}/feedback")
def submit_run_feedback(
    run_id: str,
    request: RunFeedbackRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.submit_feedback(
            run_id,
            request.constraints,
            action=request.action,
            extra_budget=request.extra_budget,
        )
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.post("/runs/{run_id}/resume", status_code=status.HTTP_202_ACCEPTED)
def resume_run(
    run_id: str,
    request: RunResumeRequest,
    services: ApplicationServices = Depends(get_services),
) -> dict[str, Any]:
    try:
        result = services.runs.resume(
            run_id,
            model_name=request.model_name,
            api_base=request.api_base,
        )
    except ValueError as exc:
        raise _bad_request("INVALID_RUN_ID", str(exc)) from exc
    _raise_run_error(result)
    return envelope(result)


@router.get("/designs/{design_id}/exports/{export_format}")
def export_design(
    design_id: str,
    export_format: str,
    services: ApplicationServices = Depends(get_services),
) -> Response:
    try:
        result = services.exports.export(design_id, export_format)
    except KeyError as exc:
        raise _not_found("DESIGN_NOT_FOUND", design_id) from exc
    except (ValueError, RepositoryError) as exc:
        raise _bad_request("EXPORT_INVALID", str(exc)) from exc
    if not result.ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXPORT_BLOCKED",
                "message": result.status,
                "details": result.errors,
                "warnings": result.warnings,
            },
        )
    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Export-Status": result.status,
    }
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers=headers,
    )


def _bad_request(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": code, "message": message, "details": []},
    )


def _not_found(code: str, identifier: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": code,
            "message": f"Resource not found: {identifier}",
            "details": [],
        },
    )


def _raise_run_error(result: dict[str, Any]) -> None:
    result_status = str(result.get("status") or "")
    error_type = str(result.get("error_type") or "")
    if result_status == "not_found" or error_type == "not_found":
        raise _not_found(
            "RUN_NOT_FOUND",
            str(result.get("run_id") or "unknown"),
        )
    if result_status == "error":
        raise _bad_request(
            error_type.upper() or "RUN_ERROR",
            str(result.get("error") or "Run operation failed."),
        )
