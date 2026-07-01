from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from benchmark_suite.benchmark_controller import evaluate_candidate
from benchmark_suite.dataset import (
    list_benchmark_datasets,
    load_benchmark_dataset,
)
from benchmark_suite.runner import (
    compare_benchmark_runs,
    run_benchmark_dataset,
)
from benchmark_suite.scoring_profiles import (
    get_scoring_profile,
    list_scoring_profiles,
)


def _candidate(*, evidence_quality: float = 0.9) -> dict:
    return {
        "functional_score": 0.9,
        "kinetic_score": 0.8,
        "robustness_score": 0.85,
        "plausibility_score": 0.9,
        "orthogonality_score": 0.85,
        "cello_assignment_score": 0.8,
        "cello_buildable": True,
        "rise_time": 120,
        "evidence_quality": evidence_quality,
        "data_completeness": 0.9,
        "semantic_faithfulness_score": 0.95,
    }


def test_scoring_profiles_are_versioned_and_hashed() -> None:
    profiles = list_scoring_profiles()
    research = get_scoring_profile("research-v1.8")

    assert {item["profile_id"] for item in profiles} == {
        "legacy-weighted",
        "research-v1.8",
        "research-v2-preview",
    }
    assert research.version == "1.8.0"
    assert len(research.configuration_hash) == 64
    assert sum(research.dimension_weights.values()) == pytest.approx(1.0)


def test_research_profile_returns_explainable_dimensions() -> None:
    result = evaluate_candidate(
        _candidate(),
        profile_id="research-v1.8",
    )

    assert result["scoring_model"] == "multidimensional_research_score"
    assert result["scoring_version"] == "1.8.0"
    assert result["scoring_configuration_hash"]
    assert set(result["dimension_scores"]) == {
        "logic_function",
        "dynamic_behavior",
        "robustness",
        "resource_burden",
        "buildability",
        "evidence_quality",
        "data_completeness",
        "semantic_faithfulness",
    }
    assert result["component_scores"]["cello_assignment"] == pytest.approx(0.8)


def test_research_profile_penalizes_missing_evidence() -> None:
    supported = evaluate_candidate(
        _candidate(evidence_quality=0.95),
        profile_id="research-v1.8",
    )
    unsupported = evaluate_candidate(
        _candidate(evidence_quality=0.05),
        profile_id="research-v1.8",
    )

    assert supported["weighted_total_score"] > unsupported["weighted_total_score"]
    assert supported["dimension_scores"]["evidence_quality"] == 0.95
    assert unsupported["dimension_scores"]["evidence_quality"] == 0.05


def test_research_v2_perfect_simulated_candidate_can_reach_full_score() -> None:
    candidate = {
        **_candidate(evidence_quality=1.0),
        "ode_status": "simulated",
        "semantic_faithfulness_score": 1.0,
        "monte_carlo_terminal_output_cv": 0.0,
        "retroactivity_max": 0.0,
        "rbs_blocking_detected": False,
        "gate_count": 1,
    }

    result = evaluate_candidate(candidate, profile_id="research-v2-preview")

    assert result["score"] == pytest.approx(1.0)
    assert result["grade"] == "Excellent"


@pytest.mark.parametrize(
    ("penalty", "expected_score"),
    [
        ({"monte_carlo_terminal_output_cv": 1.0}, 0.85),
        ({"retroactivity_max": 1.0}, 0.85),
        ({"rbs_blocking_detected": True}, 0.85),
    ],
)
def test_research_v2_biophysical_risks_reduce_score(
    penalty: dict,
    expected_score: float,
) -> None:
    candidate = {
        **_candidate(evidence_quality=1.0),
        "ode_status": "simulated",
        "semantic_faithfulness_score": 1.0,
        "monte_carlo_terminal_output_cv": 0.0,
        "retroactivity_max": 0.0,
        "rbs_blocking_detected": False,
        "gate_count": 1,
        **penalty,
    }

    result = evaluate_candidate(candidate, profile_id="research-v2-preview")

    assert result["score"] == pytest.approx(expected_score)


def test_dataset_is_versioned_validated_and_content_addressed() -> None:
    dataset = load_benchmark_dataset("research_smoke_v1")
    listed = list_benchmark_datasets()

    assert dataset.version == "1.0.0"
    assert len(dataset.cases) == 4
    assert len(dataset.content_hash) == 64
    assert listed[0]["case_count"] == 4
    assert dataset.provenance["wet_lab_validated"] is False


def test_benchmark_runner_checks_expectations_and_writes_reports(
    tmp_path: Path,
) -> None:
    dataset = load_benchmark_dataset("research_smoke_v1")
    result = run_benchmark_dataset(
        dataset,
        profile_id="research-v1.8",
        output_dir=tmp_path,
    )

    assert result["summary"]["case_count"] == 4
    assert result["summary"]["pass_rate"] == 1.0
    assert result["result_hash"]
    assert any(tool["capability"] == "ode_simulation" for tool in result["tools"])
    assert all(case["passed"] for case in result["cases"])
    assert Path(result["artifacts"]["report_json"]).exists()
    assert Path(result["artifacts"]["cases_csv"]).exists()
    markdown = Path(result["artifacts"]["summary_markdown"]).read_text(
        encoding="utf-8"
    )
    assert "computational screening" in markdown


def test_benchmark_comparison_ranks_runs_and_warns_across_versions() -> None:
    dataset = load_benchmark_dataset("research_smoke_v1")
    research = run_benchmark_dataset(dataset, profile_id="research-v1.8")
    legacy = run_benchmark_dataset(dataset, profile_id="legacy-weighted")

    comparison = compare_benchmark_runs([legacy, research])

    assert len(comparison["ranked_runs"]) == 2
    assert comparison["ranked_runs"][0]["rank"] == 1
    assert comparison["warning"] is not None


def test_evaluation_and_benchmark_api_contract(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            profiles = client.get("/api/v1/evaluation/profiles")
            datasets = client.get("/api/v1/benchmarks/datasets")
            evaluation = client.post(
                "/api/v1/evaluations",
                json={
                    "candidate": _candidate(),
                    "profile_id": "research-v1.8",
                },
            )
            created = client.post(
                "/api/v1/benchmarks/runs",
                json={
                    "dataset_id": "research_smoke_v1",
                    "profile_id": "research-v1.8",
                },
            )
            run_id = created.json()["data"]["benchmark_run_id"]
            second = client.post(
                "/api/v1/benchmarks/runs",
                json={
                    "dataset_id": "research_smoke_v1",
                    "profile_id": "legacy-weighted",
                },
            )
            second_run_id = second.json()["data"]["benchmark_run_id"]
            fetched = client.get(f"/api/v1/benchmarks/runs/{run_id}")
            compared = client.post(
                "/api/v1/benchmarks/comparisons",
                json={"benchmark_run_ids": [run_id, second_run_id]},
            )
            page = client.get("/web/benchmarks")
            detail = client.get(f"/web/benchmarks/{run_id}")
    finally:
        app.dependency_overrides.clear()

    assert profiles.status_code == 200
    assert datasets.json()["data"]["count"] >= 1
    assert evaluation.json()["data"]["scoring_version"] == "1.8.0"
    assert created.status_code == 201
    assert fetched.json()["data"]["result_hash"]
    assert compared.json()["data"]["warning"] is not None
    assert page.status_code == 200
    assert "Research evaluation smoke benchmark" in page.text
    assert detail.status_code == 200
    assert "Benchmark" in detail.text


def test_benchmark_service_persists_and_compares_runs(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    research = services.evaluations.run_benchmark(
        "research_smoke_v1",
        profile_id="research-v1.8",
    )
    legacy = services.evaluations.run_benchmark(
        "research_smoke_v1",
        profile_id="legacy-weighted",
    )

    persisted = services.evaluations.benchmark_result(
        research["benchmark_run_id"]
    )
    comparison = services.evaluations.compare_benchmarks(
        [research["benchmark_run_id"], legacy["benchmark_run_id"]]
    )

    assert persisted is not None
    assert json.loads(
        Path(persisted["artifacts"]["report_json"]).read_text(
            encoding="utf-8"
        )
    )["benchmark_run_id"] == research["benchmark_run_id"]
    assert len(comparison["ranked_runs"]) == 2
