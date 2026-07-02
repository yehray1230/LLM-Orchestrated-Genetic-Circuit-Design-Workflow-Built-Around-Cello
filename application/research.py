from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from benchmark_suite.benchmark_controller import evaluate_candidate
from mcp_server.run_store import RunStore
from schemas.simulation import canonical_payload_hash


class ResearchService:
    def __init__(
        self,
        *,
        designs: Any,
        simulations: Any,
        run_store: RunStore,
        report_dir: Path,
    ):
        self.designs = designs
        self.simulations = simulations
        self.run_store = run_store
        self.report_dir = report_dir

    def start_simulation(self, request: dict[str, Any]) -> dict[str, Any]:
        selected = dict(request)
        topology = self._topology(selected)
        run_id = f"research_{uuid4().hex[:12]}"

        def task() -> dict[str, Any]:
            simulation = self.simulations.simulate(
                topology,
                simulation_time=float(selected.get("simulation_time", 600.0)),
                sample_count=int(selected.get("sample_count", 80)),
                monte_carlo_samples=int(selected.get("monte_carlo_samples", 1)),
                noise_fraction=float(selected.get("noise_fraction", 0.15)),
                random_seed=selected.get("random_seed"),
                temporal_inputs=selected.get("temporal_inputs"),
            )
            candidate = simulation["candidate"]
            profile_id = str(
                selected.get("profile_id") or "research-v2-preview"
            )
            evaluation = evaluate_candidate(candidate, profile_id=profile_id)
            result = {
                "status": "completed",
                "research_run_id": run_id,
                "design_id": selected.get("design_id"),
                "simulation_spec": simulation["simulation_spec"],
                "simulation_result": simulation["simulation_result"],
                "evaluation": evaluation,
                "candidate": candidate,
                "summary": {
                    "score": evaluation["weighted_total_score"],
                    "grade": evaluation["grade"],
                    "simulation_status": simulation["simulation_result"]["status"],
                    "model_version": simulation["simulation_result"]["model_version"],
                    "scoring_version": evaluation["scoring_version"],
                },
            }
            result["research_result_hash"] = canonical_payload_hash(result)
            result["artifacts"] = write_research_report(result, self.report_dir)
            return result

        return self.run_store.start(task, selected, run_id=run_id)

    def status(self, run_id: str) -> dict[str, Any]:
        return self.run_store.status(run_id)

    def result(self, run_id: str) -> dict[str, Any]:
        return self.run_store.result(run_id)

    def list(self, limit: int = 50) -> dict[str, Any]:
        return self.run_store.list_runs(limit=limit)

    def cancel(self, run_id: str) -> dict[str, Any]:
        return self.run_store.cancel(run_id)

    def compare(self, run_ids: list[str]) -> dict[str, Any]:
        if len(run_ids) < 2:
            raise ValueError("At least two research runs are required.")
        rows = []
        for run_id in run_ids:
            result = self.result(run_id)
            if result.get("status") != "completed":
                raise ValueError(f"Research run is not completed: {run_id}.")
            simulation = result.get("simulation_result", {})
            evaluation = result.get("evaluation", {})
            rows.append(
                {
                    "research_run_id": run_id,
                    "design_id": result.get("design_id"),
                    "score": evaluation.get("weighted_total_score"),
                    "grade": evaluation.get("grade"),
                    "dimension_scores": evaluation.get("dimension_scores", {}),
                    "model_version": simulation.get("model_version"),
                    "configuration_hash": simulation.get("configuration_hash"),
                    "parameter_set_hash": simulation.get("parameter_set_hash"),
                    "scenario_set_hash": simulation.get("scenario_set_hash"),
                    "scoring_profile": evaluation.get("scoring_profile"),
                    "scoring_version": evaluation.get("scoring_version"),
                }
            )
        comparable = (
            len({row["model_version"] for row in rows}) == 1
            and len({row["scoring_version"] for row in rows}) == 1
        )
        ranked = sorted(
            rows,
            key=lambda row: float(row.get("score") or 0.0),
            reverse=True,
        )
        for rank, row in enumerate(ranked, start=1):
            row["rank"] = rank
        return {
            "comparable": comparable,
            "warning": (
                None
                if comparable
                else "Model or scoring versions differ; rankings are descriptive only."
            ),
            "ranked_runs": ranked,
            "comparison_hash": canonical_payload_hash(ranked),
        }

    def _topology(self, request: dict[str, Any]) -> dict[str, Any]:
        topology = request.get("topology")
        if isinstance(topology, dict) and topology:
            return dict(topology)
        design_id = str(request.get("design_id") or "").strip()
        if not design_id:
            raise ValueError("Either design_id or topology is required.")
        design = self.designs.get_v2(design_id)
        if design is None:
            raise KeyError(design_id)
        spec = self.designs.simulation_spec(design_id)
        if spec is None:
            raise KeyError(design_id)
        verilog = str(spec.get("verilog") or "")
        if not verilog:
            raise ValueError(
                "The selected design has no Verilog topology. "
                "Provide topology.verilog before simulation."
            )
        return {
            "verilog": verilog,
            "truth_table": design.specification.truth_table,
            "chassis": spec.get("chassis"),
            "copy_number": spec.get("copy_number"),
            "biokinetic_parameters": spec.get("parameters", {}),
        }


def write_research_report(
    result: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    run_dir = output_dir / str(result["research_run_id"])
    run_dir.mkdir(parents=True, exist_ok=False)
    json_path = run_dir / "research_report.json"
    csv_path = run_dir / "research_dimensions.csv"
    markdown_path = run_dir / "research_summary.md"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    csv_path.write_text(_dimension_csv(result), encoding="utf-8-sig")
    markdown_path.write_text(_research_markdown(result), encoding="utf-8")
    return {
        "report_json": str(json_path.resolve()),
        "dimensions_csv": str(csv_path.resolve()),
        "summary_markdown": str(markdown_path.resolve()),
    }


def _dimension_csv(result: dict[str, Any]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["dimension", "score", "applicability"])
    writer.writeheader()
    evaluation = result.get("evaluation", {})
    applicability = evaluation.get("dimension_applicability", {})
    for key, score in evaluation.get("dimension_scores", {}).items():
        writer.writerow(
            {
                "dimension": key,
                "score": score,
                "applicability": applicability.get(key),
            }
        )
    return buffer.getvalue()


def _research_markdown(result: dict[str, Any]) -> str:
    evaluation = result.get("evaluation", {})
    simulation = result.get("simulation_result", {})
    lines = [
        "# Research Simulation Report",
        "",
        f"- Run: `{result.get('research_run_id')}`",
        f"- Design: `{result.get('design_id') or 'direct topology'}`",
        f"- Model: `{simulation.get('model_id')}@{simulation.get('model_version')}`",
        f"- Configuration: `{simulation.get('configuration_hash')}`",
        f"- Scoring: `{evaluation.get('scoring_profile')}@{evaluation.get('scoring_version')}`",
        f"- Score: {float(evaluation.get('weighted_total_score') or 0.0):.3f}",
        f"- Grade: {evaluation.get('grade')}",
        "",
        "## Dimensions",
        "",
    ]
    for key, score in evaluation.get("dimension_scores", {}).items():
        lines.append(f"- `{key}`: {float(score):.3f}")
    lines.extend(
        [
            "",
            "> Computational screening only. This report does not establish "
            "wet-lab viability or provide an experimental protocol.",
            "",
        ]
    )
    return "\n".join(lines)
