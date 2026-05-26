from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agents.consolidator_agent import ConsolidatorAgent
from agents.data_miner_agent import DataMinerAgent
from benchmark_suite.benchmark_controller import evaluate_candidate
from mcp_server.artifact_writer import create_run_dir, write_json, write_state_artifacts
from mcp_server.chart_renderer import render_charts
from mcp_server.run_store import RunStore
from mcp_server.serializers import summarize_state, summarize_topology
from schemas.state import DesignState, SearchNode
from tools.cello_wrapper import CelloWrapper
from tools.ode_simulator import BatchODESimulator
from vector_db import InMemoryVectorDB
from workflows.reflexion_controller import run_reflexion_workflow


DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_RUN_STORE = RunStore()
ERROR_VALIDATION = "validation_error"
ERROR_DEPENDENCY = "dependency_error"
ERROR_WORKFLOW = "workflow_error"
ERROR_EXTERNAL_TOOL = "external_tool_error"
ERROR_NOT_FOUND = "not_found"


@dataclass
class WorkflowOptions:
    enable_rag: bool = True
    enable_ode: bool = True
    enable_skill_extraction: bool = True
    compute_budget: int = 2
    monte_carlo_samples: int = 1
    output_dir: str | None = None
    cello_command: str | None = None
    ucf_path: str | None = None
    model_name: str | None = None
    api_base: str | None = None
    api_key: str | None = None


class TranslatorRunner:
    def __init__(self, api_key: str | None, model_name: str, api_base: str | None):
        self.api_key = api_key
        self.model_name = model_name
        self.api_base = api_base
        self.kwargs: dict[str, Any] = {}

    def run(self, state: DesignState) -> DesignState:
        from agents.translator_agent import call_translator

        return call_translator(
            state,
            api_key=self.api_key,
            model_name=self.model_name,
            api_base=self.api_base,
            **self.kwargs,
        )


class NoOpODESimulator:
    def run(self, state: DesignState) -> DesignState:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        topologies = node.candidate_topologies if node else state.candidate_topologies
        for topology in topologies:
            topology["ode_status"] = "disabled"
        state.candidate_topologies = topologies
        return state


def design_circuit_quick(
    user_intent: str,
    host_organism: str = "Escherichia coli",
    compute_budget: int = 2,
    enable_rag: bool = True,
    enable_ode: bool = True,
    enable_skill_extraction: bool = True,
    monte_carlo_samples: int = 1,
    model_name: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    output_dir: str | None = None,
    cello_command: str | None = None,
    ucf_path: str | None = None,
) -> dict[str, Any]:
    user_intent = str(user_intent or "").strip()
    if not user_intent:
        return _error_response("user_intent is required.", ERROR_VALIDATION)
    compute_budget_result = _coerce_min_int(compute_budget, "compute_budget")
    if compute_budget_result["status"] == "error":
        return compute_budget_result
    monte_carlo_result = _coerce_min_int(monte_carlo_samples, "monte_carlo_samples")
    if monte_carlo_result["status"] == "error":
        return monte_carlo_result

    options = WorkflowOptions(
        enable_rag=enable_rag,
        enable_ode=enable_ode,
        enable_skill_extraction=enable_skill_extraction,
        compute_budget=compute_budget_result["value"],
        monte_carlo_samples=monte_carlo_result["value"],
        output_dir=output_dir,
        cello_command=cello_command,
        ucf_path=ucf_path,
        model_name=model_name,
        api_base=api_base,
        api_key=api_key,
    )
    resolved_model = _resolve_model(options.model_name)
    resolved_api_key = _resolve_api_key(options.api_key)
    resolved_api_base = options.api_base or os.getenv("LITELLM_API_BASE") or None

    if not resolved_model:
        return _error_response("model_name is required via argument or LITELLM_MODEL.", ERROR_VALIDATION)

    try:
        from agents.builder_agent import BuilderAgent
        from agents.critic_agent import CriticAgent
        from agents.skill_extractor_agent import SkillExtractorAgent
        from tools.skill_retriever import SkillRetriever
    except ModuleNotFoundError as exc:
        return _error_response(
            (
                "design_circuit_quick requires the LLM workflow dependencies. "
                f"Missing module: {exc.name}"
            ),
            ERROR_DEPENDENCY,
        )

    state = DesignState(
        user_intent=user_intent,
        host_organism=host_organism.strip() or "Escherichia coli",
        compute_budget=options.compute_budget,
    )

    batch_ode_simulator = (
        BatchODESimulator(monte_carlo_samples=options.monte_carlo_samples)
        if options.enable_ode
        else NoOpODESimulator()
    )
    skill_retriever = SkillRetriever.from_json_file() if options.enable_rag else None
    skill_extractor = (
        SkillExtractorAgent(vault_dir="outputs/obsidian_skills", vector_db=InMemoryVectorDB())
        if options.enable_skill_extraction
        else None
    )

    try:
        result_state = run_reflexion_workflow(
            state=state,
            builder=BuilderAgent(api_key=resolved_api_key, model_name=resolved_model, api_base=resolved_api_base),
            translator=TranslatorRunner(api_key=resolved_api_key, model_name=resolved_model, api_base=resolved_api_base),
            cello_wrapper=CelloWrapper(cello_command=options.cello_command, ucf_path=options.ucf_path),
            batch_ode_simulator=batch_ode_simulator,
            critic=CriticAgent(api_key=resolved_api_key, model_name=resolved_model, api_base=resolved_api_base),
            consolidator=ConsolidatorAgent(),
            skill_retriever=skill_retriever,
            data_miner=DataMinerAgent() if options.enable_ode else None,
            skill_extractor=skill_extractor,
        )
    except Exception as exc:
        return _error_response(f"workflow failed: {exc}", ERROR_WORKFLOW)

    run_dir = create_run_dir(options.output_dir)
    charts = render_charts(result_state.best_topology, run_dir)
    artifacts = write_state_artifacts(result_state, run_dir, charts)
    summary = summarize_state(result_state)
    return _success_response({
        "status": _status_from_state(result_state),
        "run_dir": str(run_dir.resolve()),
        "summary": summary,
        "artifacts": artifacts,
    })


def start_design_run(
    user_intent: str,
    host_organism: str = "Escherichia coli",
    compute_budget: int = 6,
    enable_rag: bool = True,
    enable_ode: bool = True,
    enable_skill_extraction: bool = True,
    monte_carlo_samples: int = 1,
    model_name: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    output_dir: str | None = None,
    cello_command: str | None = None,
    ucf_path: str | None = None,
    run_store: RunStore | None = None,
) -> dict[str, Any]:
    user_intent = str(user_intent or "").strip()
    if not user_intent:
        return _error_response("user_intent is required.", ERROR_VALIDATION)
    compute_budget_result = _coerce_min_int(compute_budget, "compute_budget")
    if compute_budget_result["status"] == "error":
        return compute_budget_result
    monte_carlo_result = _coerce_min_int(monte_carlo_samples, "monte_carlo_samples")
    if monte_carlo_result["status"] == "error":
        return monte_carlo_result

    request = {
        "user_intent": user_intent,
        "host_organism": host_organism,
        "compute_budget": compute_budget_result["value"],
        "enable_rag": enable_rag,
        "enable_ode": enable_ode,
        "enable_skill_extraction": enable_skill_extraction,
        "monte_carlo_samples": monte_carlo_result["value"],
        "model_name": model_name,
        "api_base": api_base,
        "api_key": api_key,
        "output_dir": output_dir,
        "cello_command": cello_command,
        "ucf_path": ucf_path,
    }
    selected_store = run_store or DEFAULT_RUN_STORE
    return selected_store.start(
        task=lambda: design_circuit_quick(
            user_intent=user_intent,
            host_organism=host_organism,
            compute_budget=compute_budget_result["value"],
            enable_rag=enable_rag,
            enable_ode=enable_ode,
            enable_skill_extraction=enable_skill_extraction,
            monte_carlo_samples=monte_carlo_result["value"],
            model_name=model_name,
            api_base=api_base,
            api_key=api_key,
            output_dir=output_dir,
            cello_command=cello_command,
            ucf_path=ucf_path,
        ),
        request=request,
    )


def get_design_run_status(run_id: str, run_store: RunStore | None = None) -> dict[str, Any]:
    selected_store = run_store or DEFAULT_RUN_STORE
    return selected_store.status(run_id)


def get_design_run_result(run_id: str, run_store: RunStore | None = None) -> dict[str, Any]:
    selected_store = run_store or DEFAULT_RUN_STORE
    return _ensure_standard_response(selected_store.result(run_id))


def list_design_runs(limit: int = 20, run_store: RunStore | None = None) -> dict[str, Any]:
    selected_store = run_store or DEFAULT_RUN_STORE
    try:
        selected_limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        return _error_response("limit must be an integer.", ERROR_VALIDATION)
    return selected_store.list_runs(selected_limit)


def cancel_design_run(run_id: str, run_store: RunStore | None = None) -> dict[str, Any]:
    if not str(run_id or "").strip():
        return _error_response("run_id is required.", ERROR_VALIDATION)
    selected_store = run_store or DEFAULT_RUN_STORE
    return _ensure_standard_response(selected_store.cancel(str(run_id).strip()))


def get_design_run_artifacts(run_id: str, run_store: RunStore | None = None) -> dict[str, Any]:
    if not str(run_id or "").strip():
        return _error_response("run_id is required.", ERROR_VALIDATION)
    selected_store = run_store or DEFAULT_RUN_STORE
    return _ensure_standard_response(selected_store.artifacts(str(run_id).strip()))


def compare_design_runs(run_ids: list[str], run_store: RunStore | None = None) -> dict[str, Any]:
    normalized_run_ids = _normalize_run_ids(run_ids)
    if normalized_run_ids["status"] == "error":
        return normalized_run_ids

    selected_store = run_store or DEFAULT_RUN_STORE
    comparisons = []
    unavailable_runs = []
    for run_id in normalized_run_ids["run_ids"]:
        result = _ensure_standard_response(selected_store.result(run_id))
        if result.get("status") != "completed":
            unavailable_runs.append(
                {
                    "run_id": run_id,
                    "status": result.get("status"),
                    "error": result.get("error"),
                    "error_type": result.get("error_type"),
                }
            )
            continue
        comparisons.append(_comparison_entry(run_id, result))

    comparisons.sort(key=lambda item: (item["score"] is not None, item["score"] or -float("inf")), reverse=True)
    for index, item in enumerate(comparisons, start=1):
        item["rank"] = index

    return _success_response(
        {
            "status": "completed" if comparisons else "error",
            "summary": {
                "requested_run_count": len(normalized_run_ids["run_ids"]),
                "available_run_count": len(comparisons),
                "unavailable_run_count": len(unavailable_runs),
                "best_run_id": comparisons[0]["run_id"] if comparisons else None,
            },
            "artifacts": {},
            "best_run": comparisons[0] if comparisons else None,
            "ranked_runs": comparisons,
            "unavailable_runs": unavailable_runs,
            "metrics": [
                "score",
                "mapping_status",
                "ode_status",
                "cello_buildable",
                "robustness_score",
                "toxicity_score",
                "semantic_faithfulness_score",
                "artifact_count",
            ],
            "error": None if comparisons else "No completed runs were available for comparison.",
            "error_type": None if comparisons else ERROR_NOT_FOUND,
        }
    )


def diagnose_design_run(run_id: str, run_store: RunStore | None = None) -> dict[str, Any]:
    if not str(run_id or "").strip():
        return _error_response("run_id is required.", ERROR_VALIDATION)
    selected_store = run_store or DEFAULT_RUN_STORE
    result = _ensure_standard_response(selected_store.result(str(run_id).strip()))
    if result.get("status") == "not_found":
        return result

    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    artifacts = result.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    best_topology = _best_topology_from_result(result)
    failed_attempts = summary.get("failed_attempts") if isinstance(summary.get("failed_attempts"), list) else []

    findings = _diagnose_findings(result, summary, best_topology, failed_attempts)
    actions = _recommended_actions(findings)
    diagnosis_status = _diagnosis_status(findings)
    return _success_response(
        {
            "status": "completed",
            "summary": {
                "run_id": run_id,
                "run_status": result.get("status"),
                "diagnosis_status": diagnosis_status,
                "finding_count": len(findings),
                "high_severity_count": sum(1 for finding in findings if finding["severity"] == "high"),
            },
            "artifacts": artifacts,
            "diagnosis_status": diagnosis_status,
            "findings": findings,
            "likely_causes": _likely_causes(findings),
            "recommended_next_actions": actions,
        }
    )


def evaluate_verilog(
    verilog: str,
    user_intent: str = "Evaluate a Cello-compatible genetic circuit.",
    host_organism: str = "Escherichia coli",
    enable_ode: bool = True,
    monte_carlo_samples: int = 1,
    output_dir: str | None = None,
    cello_command: str | None = None,
    ucf_path: str | None = None,
) -> dict[str, Any]:
    verilog = str(verilog or "").strip()
    if not verilog:
        return _error_response("verilog is required.", ERROR_VALIDATION)
    monte_carlo_result = _coerce_min_int(monte_carlo_samples, "monte_carlo_samples")
    if monte_carlo_result["status"] == "error":
        return monte_carlo_result

    state = DesignState(user_intent=user_intent, host_organism=host_organism, compute_budget=1)
    node = SearchNode(node_id="root", search_mode="Exploration")
    node.verilog_codes = [verilog]
    state.tree_nodes["root"] = node
    state.current_node_id = "root"
    state.verilog_codes = [verilog]

    try:
        state = CelloWrapper(cello_command=cello_command, ucf_path=ucf_path).run(state)
        if state.last_error:
            return _error_response(state.last_error, ERROR_EXTERNAL_TOOL)
        state = DataMinerAgent().run(state) if enable_ode else state
        state = (
            BatchODESimulator(monte_carlo_samples=monte_carlo_result["value"]).run(state)
            if enable_ode
            else NoOpODESimulator().run(state)
        )
        for topology in node.candidate_topologies:
            topology.update(evaluate_candidate(topology))
        best_topology = max(node.candidate_topologies, key=lambda item: float(item.get("score", -9999)), default=None)
        node.best_topology = best_topology
        node.sync_evaluation_metrics(best_topology)
        state.best_topology = best_topology
    except Exception as exc:
        return _error_response(f"evaluation failed: {exc}", ERROR_WORKFLOW)

    run_dir = create_run_dir(output_dir)
    charts = render_charts(state.best_topology, run_dir)
    artifacts = write_state_artifacts(state, run_dir, charts)
    write_json(run_dir / "input_verilog.json", {"verilog": verilog})
    return _success_response({
        "status": "completed",
        "run_dir": str(run_dir.resolve()),
        "summary": summarize_state(state),
        "best_topology": summarize_topology(state.best_topology),
        "artifacts": artifacts,
    })


def summarize_design_state(state_json: dict[str, Any]) -> dict[str, Any]:
    """Summarize a saved state JSON produced by this adapter."""
    return _success_response({
        "status": "completed",
        "summary": {
            "user_intent": state_json.get("user_intent"),
            "host_organism": state_json.get("host_organism"),
            "is_completed": state_json.get("is_completed"),
            "is_approved": state_json.get("is_approved"),
            "requires_human_input": state_json.get("requires_human_input"),
            "pause_reason": state_json.get("pause_reason"),
            "current_node_id": state_json.get("current_node_id"),
            "best_topology": summarize_topology(state_json.get("best_topology")),
        },
        "artifacts": {},
    })


def _resolve_model(model_name: str | None) -> str:
    return model_name or os.getenv("LITELLM_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def _resolve_api_key(api_key: str | None) -> str | None:
    return api_key or os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY") or None


def _status_from_state(state: DesignState) -> str:
    if state.last_error:
        return "error"
    if state.requires_human_input:
        return "needs_human_input"
    if state.is_completed or state.best_topology:
        return "completed"
    return "stopped"


def _success_response(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("error", None)
    payload.setdefault("error_type", None)
    payload.setdefault("summary", {})
    payload.setdefault("artifacts", {})
    return payload


def _error_response(message: str, error_type: str) -> dict[str, Any]:
    return {
        "status": "error" if error_type != ERROR_NOT_FOUND else "not_found",
        "error": message,
        "error_type": error_type,
        "summary": {},
        "artifacts": {},
    }


def _ensure_standard_response(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") == "not_found":
        payload.setdefault("error_type", ERROR_NOT_FOUND)
    else:
        payload.setdefault("error_type", None)
    payload.setdefault("error", None)
    payload.setdefault("summary", {})
    payload.setdefault("artifacts", {})
    return payload


def _coerce_min_int(value: Any, field_name: str) -> dict[str, Any]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return _error_response(f"{field_name} must be an integer.", ERROR_VALIDATION)
    if parsed < 1:
        return _error_response(f"{field_name} must be at least 1.", ERROR_VALIDATION)
    return {"status": "ok", "value": parsed}


def _normalize_run_ids(run_ids: Any) -> dict[str, Any]:
    if not isinstance(run_ids, list):
        return _error_response("run_ids must be a list of run IDs.", ERROR_VALIDATION)
    normalized = [str(run_id).strip() for run_id in run_ids if str(run_id or "").strip()]
    if len(normalized) < 2:
        return _error_response("compare_design_runs requires between 2 and 10 run IDs.", ERROR_VALIDATION)
    if len(normalized) > 10:
        return _error_response("compare_design_runs accepts at most 10 run IDs.", ERROR_VALIDATION)
    return {"status": "ok", "run_ids": normalized}


def _comparison_entry(run_id: str, result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    best_topology = _best_topology_from_result(result)
    artifacts = result.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
    return {
        "run_id": run_id,
        "status": result.get("status"),
        "score": _metric(best_topology, summary, "score"),
        "mapping_status": _metric(best_topology, summary, "mapping_status"),
        "ode_status": _metric(best_topology, summary, "ode_status"),
        "cello_buildable": _metric(best_topology, summary, "cello_buildable"),
        "robustness_score": _metric(best_topology, summary, "robustness_score"),
        "toxicity_score": _metric(best_topology, summary, "toxicity_score"),
        "semantic_faithfulness_score": _metric(best_topology, summary, "semantic_faithfulness_score"),
        "artifact_count": len(artifacts),
        "artifact_keys": sorted(artifacts.keys()),
        "run_dir": result.get("run_dir") or result.get("workflow_run_dir"),
        "best_topology": best_topology,
    }


def _best_topology_from_result(result: dict[str, Any]) -> dict[str, Any]:
    direct = result.get("best_topology")
    if isinstance(direct, dict) and direct:
        return direct
    summary = result.get("summary", {})
    if isinstance(summary, dict):
        best_topology = summary.get("best_topology")
        if isinstance(best_topology, dict):
            return best_topology
    return {}


def _metric(best_topology: dict[str, Any], summary: dict[str, Any], key: str) -> Any:
    if key in best_topology:
        return best_topology[key]
    return summary.get(key)


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _diagnose_findings(
    result: dict[str, Any],
    summary: dict[str, Any],
    best_topology: dict[str, Any],
    failed_attempts: list[Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    run_status = result.get("status")
    if run_status != "completed":
        findings.append(
            _finding(
                "high",
                "run_status",
                f"Run status is {run_status}, so the design may not be ready for evaluation.",
                {"status": run_status, "error": result.get("error"), "error_type": result.get("error_type")},
            )
        )
    if summary.get("requires_human_input"):
        findings.append(
            _finding(
                "high",
                "human_input",
                "Workflow paused and requires human guidance before it can be considered complete.",
                {"pause_reason": summary.get("pause_reason"), "prompt": summary.get("human_feedback_prompt")},
            )
        )
    if not best_topology:
        findings.append(
            _finding(
                "high",
                "topology",
                "No best topology is available in the run result.",
                {"current_node_id": summary.get("current_node_id")},
            )
        )

    mapping_status = str(_metric(best_topology, summary, "mapping_status") or "").lower()
    if mapping_status in {"failed", "unmapped", "error"}:
        findings.append(
            _finding(
                "high" if mapping_status == "failed" else "warning",
                "mapping",
                "Cello mapping did not produce a clearly mapped design.",
                {"mapping_status": mapping_status or None},
            )
        )

    ode_status = str(_metric(best_topology, summary, "ode_status") or "").lower()
    if ode_status in {"failed", "error", "disabled"}:
        findings.append(
            _finding(
                "warning",
                "ode",
                "ODE validation is unavailable or did not complete successfully.",
                {"ode_status": ode_status or None},
            )
        )

    for metric_name, category in (
        ("score", "score"),
        ("robustness_score", "robustness"),
        ("semantic_faithfulness_score", "semantics"),
    ):
        metric_value = _float_or_none(_metric(best_topology, summary, metric_name))
        if metric_value is None:
            continue
        if metric_value < 0.25:
            severity = "high"
        elif metric_value < 0.5:
            severity = "warning"
        else:
            continue
        findings.append(
            _finding(
                severity,
                category,
                f"{metric_name} is below the recommended threshold.",
                {metric_name: metric_value},
            )
        )

    toxicity_score = _float_or_none(_metric(best_topology, summary, "toxicity_score"))
    toxicity = _float_or_none(_metric(best_topology, summary, "toxicity"))
    if toxicity_score is not None and toxicity_score < 0.5:
        findings.append(
            _finding(
                "warning" if toxicity_score >= 0.25 else "high",
                "toxicity",
                "Toxicity score suggests possible part burden or toxicity risk.",
                {"toxicity_score": toxicity_score, "toxicity": toxicity},
            )
        )

    feedback = str(summary.get("latest_critic_feedback") or "").strip()
    if feedback:
        findings.append(
            _finding(
                "info",
                "critic",
                "Critic feedback is available for this run.",
                {"latest_critic_feedback": feedback},
            )
        )

    if failed_attempts:
        findings.append(
            _finding(
                "warning",
                "search",
                "The workflow recorded failed attempts before reaching this result.",
                {"failed_attempt_count": len(failed_attempts), "recent_failed_attempt": failed_attempts[-1]},
            )
        )
    return findings


def _finding(severity: str, category: str, message: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "evidence": evidence,
    }


def _diagnosis_status(findings: list[dict[str, Any]]) -> str:
    severities = {finding.get("severity") for finding in findings}
    if "high" in severities:
        return "needs_attention"
    if "warning" in severities:
        return "watch"
    return "healthy"


def _likely_causes(findings: list[dict[str, Any]]) -> list[str]:
    causes_by_category = {
        "run_status": "The run did not complete successfully or is not ready for final evaluation.",
        "human_input": "The workflow needs additional constraints, trade-offs, or fallback guidance.",
        "topology": "The workflow did not produce a usable best topology.",
        "mapping": "Cello constraints, UCF configuration, or Verilog structure may prevent mapping.",
        "ode": "ODE simulation was disabled, unavailable, or failed during validation.",
        "score": "The candidate design underperformed across weighted benchmark criteria.",
        "robustness": "The design may be sensitive to parameter variation or biological noise.",
        "semantics": "The generated circuit may not faithfully match the original intent.",
        "toxicity": "Selected parts may introduce burden or toxicity concerns.",
        "critic": "The critic identified concerns that should be reviewed.",
        "search": "Earlier search branches failed before the current candidate was selected.",
    }
    causes = []
    for finding in findings:
        cause = causes_by_category.get(str(finding.get("category")))
        if cause and cause not in causes:
            causes.append(cause)
    return causes


def _recommended_actions(findings: list[dict[str, Any]]) -> list[str]:
    actions_by_category = {
        "run_status": "Check the run result error fields and rerun after resolving the reported issue.",
        "human_input": "Provide additional design constraints, acceptable trade-offs, or a preferred fallback topology.",
        "topology": "Rerun with a larger compute budget or inspect failed attempts for the blocking stage.",
        "mapping": "Inspect the Verilog, Cello command, and UCF path; consider simplifying gates or changing allowed parts.",
        "ode": "Enable ODE validation or inspect the ODE simulator inputs before trusting dynamic behavior.",
        "score": "Compare against higher-scoring runs and use the best topology as the next design seed.",
        "robustness": "Increase Monte Carlo samples and tune parts for stronger dynamic margins.",
        "semantics": "Clarify the natural-language intent and add edge cases for the translator/critic loop.",
        "toxicity": "Review part burden and toxicity metrics; prefer lower-burden gates or alternative host constraints.",
        "critic": "Review latest critic feedback before launching a repair or exploitation branch.",
        "search": "Use failed attempt records to choose between logic repair and part-level exploitation.",
    }
    actions = []
    for finding in findings:
        action = actions_by_category.get(str(finding.get("category")))
        if action and action not in actions:
            actions.append(action)
    if not actions:
        actions.append("No immediate action is required; keep the run as a viable candidate.")
    return actions
