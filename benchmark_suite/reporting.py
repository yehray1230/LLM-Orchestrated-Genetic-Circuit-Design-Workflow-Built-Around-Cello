from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any


def write_benchmark_report(
    result: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, str]:
    run_dir = Path(output_dir) / str(result["benchmark_run_id"])
    run_dir.mkdir(parents=True, exist_ok=False)
    json_path = run_dir / "benchmark_report.json"
    csv_path = run_dir / "benchmark_cases.csv"
    markdown_path = run_dir / "benchmark_summary.md"

    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    csv_path.write_text(_cases_csv(result), encoding="utf-8-sig")
    markdown_path.write_text(_summary_markdown(result), encoding="utf-8")
    return {
        "report_json": str(json_path.resolve()),
        "cases_csv": str(csv_path.resolve()),
        "summary_markdown": str(markdown_path.resolve()),
    }


def _cases_csv(result: dict[str, Any]) -> str:
    buffer = io.StringIO()
    dimensions = sorted(
        {
            key
            for case in result.get("cases", [])
            for key in case.get("evaluation", {}).get("dimension_scores", {})
        }
    )
    fieldnames = [
        "case_id",
        "name",
        "passed",
        "score",
        "grade",
        *dimensions,
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for case in result.get("cases", []):
        evaluation = case.get("evaluation", {})
        row = {
            "case_id": case.get("case_id"),
            "name": case.get("name"),
            "passed": case.get("passed"),
            "score": evaluation.get("weighted_total_score"),
            "grade": evaluation.get("grade"),
        }
        row.update(evaluation.get("dimension_scores", {}))
        writer.writerow(row)
    return buffer.getvalue()


def _summary_markdown(result: dict[str, Any]) -> str:
    dataset = result.get("dataset", {})
    summary = result.get("summary", {})
    lines = [
        "# Benchmark Report",
        "",
        f"- Run: `{result.get('benchmark_run_id')}`",
        f"- Dataset: `{dataset.get('dataset_id')}@{dataset.get('version')}`",
        f"- Dataset hash: `{dataset.get('content_hash')}`",
        f"- Scoring profile: `{result.get('profile_id')}@{result.get('scoring_version')}`",
        f"- Scoring configuration: `{result.get('scoring_configuration_hash')}`",
        f"- Cases: {summary.get('case_count', 0)}",
        f"- Pass rate: {float(summary.get('pass_rate') or 0.0):.1%}",
        f"- Mean score: {float(summary.get('mean') or 0.0):.3f}",
        "",
        "## Dimension Means",
        "",
    ]
    for key, value in summary.get("dimensions", {}).items():
        lines.append(f"- `{key}`: {float(value.get('mean') or 0.0):.3f}")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Score | Grade | Expected checks |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for case in result.get("cases", []):
        evaluation = case.get("evaluation", {})
        lines.append(
            f"| {case.get('case_id')} | "
            f"{float(evaluation.get('weighted_total_score') or 0.0):.3f} | "
            f"{evaluation.get('grade')} | "
            f"{'pass' if case.get('passed') else 'fail'} |"
        )
    lines.extend(
        [
            "",
            "> These scores are computational screening results and do not "
            "constitute wet-lab validation.",
            "",
        ]
    )
    return "\n".join(lines)
