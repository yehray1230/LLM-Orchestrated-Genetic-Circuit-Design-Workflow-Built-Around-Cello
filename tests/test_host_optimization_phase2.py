from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from schemas.design_ir_v2 import (
    AttributedValue,
    BiologicalContext,
    BiologicalPartV2,
    DesignIRV2,
    DesignSpecification,
)
from schemas.host_optimization import ExperimentalMeasurement
from schemas.host_profile import default_ecoli_profile
from tools.host_optimization import (
    rank_host_optimization_candidates,
    summarize_host_calibration,
    calculate_cai,
    calculate_rare_codon_fraction,
    align_rbs_to_sd,
)


def _design() -> DesignIRV2:
    return DesignIRV2(
        design_id="phase2_design",
        name="Phase 2 design",
        specification=DesignSpecification(outputs=["Y"]),
        biological_context=BiologicalContext(
            host_organism=AttributedValue(
                value="Escherichia coli",
                status="explicit",
            )
        ),
        parts=[
            BiologicalPartV2(
                id="reporter_cds",
                name="Reporter CDS",
                part_type="CDS",
                role="reporter",
                sequence="ATGGGTCTCTAA",
                evidence_level="user_verified",
                host_compatibility=["Escherichia coli"],
            )
        ],
        interactions=[],
        constructs=[],
    )


def test_host_optimization_ranks_pareto_style_candidates() -> None:
    result = rank_host_optimization_candidates(
        _design(),
        default_ecoli_profile(),
    )

    assert result.status == "ready"
    assert len(result.candidates) == 3
    assert result.selected_candidate_id == result.candidates[0].candidate_id
    strategies = {candidate.strategy for candidate in result.candidates}
    assert strategies == {"high_expression", "low_burden", "balanced"}
    assert all(candidate.sequence_overrides for candidate in result.candidates)
    assert result.limitations


def test_host_calibration_summarizes_measurements() -> None:
    result = summarize_host_calibration(
        calibration_id="calibration_1",
        design_id="phase2_design",
        host_profile_id="ecoli_k12_default",
        measurements=[
            ExperimentalMeasurement(
                measurement_id="m1",
                design_id="phase2_design",
                candidate_id="host_candidate_balanced",
                expression_value=1200.0,
                growth_rate=0.72,
                burden_value=0.42,
                on_off_ratio=18.0,
            ),
            ExperimentalMeasurement(
                measurement_id="m2",
                design_id="phase2_design",
                candidate_id="host_candidate_balanced",
                expression_value=1000.0,
                growth_rate=0.68,
                burden_value=0.50,
                on_off_ratio=16.0,
            ),
        ],
    )

    assert result.status == "completed"
    assert result.summary["mean_expression"] == 1100.0
    assert result.summary["mean_growth_rate"] == 0.7
    assert result.summary["mean_on_off_ratio"] == 17.0
    assert result.recommendations


def test_host_optimization_service_returns_readiness_and_stores_calibration(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save_v2(_design())

    ranked = services.host_optimization.rank_candidates(
        "phase2_design",
        {"host_profile_id": "ecoli_k12_default"},
    )
    calibration = services.host_optimization.calibrate(
        {
            "calibration_id": "calibration_service_1",
            "design_id": "phase2_design",
            "host_profile_id": "ecoli_k12_default",
            "measurements": [
                {
                    "measurement_id": "m1",
                    "design_id": "phase2_design",
                    "candidate_id": ranked["optimization"]["selected_candidate_id"],
                    "expression_value": 10.0,
                    "growth_rate": 0.6,
                }
            ],
        }
    )

    assert ranked["ok"] is True
    assert ranked["readiness"]["readiness_status"] == "host_optimized"
    assert calibration["status"] == "completed"
    assert services.host_optimization.get_calibration("calibration_service_1")[
        "measurement_count"
    ] == 1


def test_optimization_workflow_runs_sequence_and_host_stages(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save_v2(_design())

    result = services.optimization_workflows.run(
        "phase2_design",
        {
            "host_profile_id": "ecoli_k12_default",
            "part_ids": ["reporter_cds"],
        },
    )
    saved = services.designs.get_v2("phase2_design")

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["steps"]["sequence_analysis"]["status"] == "warning"
    assert result["steps"]["sequence_optimization"]["status"] == "passed"
    assert result["steps"]["host_optimization"]["optimization"]["status"] == "ready"
    assert result["readiness"]["readiness_status"] == "host_optimized"
    assert result["readiness"]["domain_scores"]["sequence_optimization_score"] == 1.0
    assert result["readiness"]["domain_scores"]["host_optimization_score"] == 1.0
    assert saved is not None
    assert saved.revision.change_type == "sequence_optimization"
    assert len(services.designs.revisions("phase2_design")) == 2


def test_v2_host_optimization_and_calibration_api(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save_v2(_design())
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app) as client:
        ranked = client.post(
            "/api/v2/designs/phase2_design/host-optimization/candidates",
            json={"host_profile_id": "ecoli_k12_default"},
        )
        calibration = client.post(
            "/api/v2/host-optimization/calibrations",
            json={
                "calibration_id": "api_calibration_1",
                "design_id": "phase2_design",
                "host_profile_id": "ecoli_k12_default",
                "measurements": [
                    {
                        "measurement_id": "m1",
                        "design_id": "phase2_design",
                        "expression_value": 42.0,
                    }
                ],
            },
        )
        fetched = client.get("/api/v2/host-optimization/calibrations/api_calibration_1")
    app.dependency_overrides.clear()

    assert ranked.status_code == 200
    assert ranked.json()["data"]["optimization"]["status"] == "ready"
    assert calibration.status_code == 201
    assert calibration.json()["data"]["status"] == "completed"
    assert fetched.status_code == 200
    assert fetched.json()["data"]["calibration_id"] == "api_calibration_1"


def test_v2_optimization_workflow_api(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save_v2(_design())
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app) as client:
        response = client.post(
            "/api/v2/designs/phase2_design/optimization-workflow",
            json={
                "host_profile_id": "ecoli_k12_default",
                "part_ids": ["reporter_cds"],
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["steps"]["sequence_optimization"]["status"] == "passed"
    assert data["steps"]["host_optimization"]["optimization"]["status"] == "ready"
    assert data["readiness"]["readiness_status"] == "host_optimized"


def test_dynamic_calculators() -> None:
    profile = default_ecoli_profile()
    # Test align_rbs_to_sd
    assert align_rbs_to_sd("TAAGGAGG") == 1.0
    assert align_rbs_to_sd("AGGAG") == 0.625
    assert align_rbs_to_sd("") == 0.0

    # Test calculate_rare_codon_fraction
    assert calculate_rare_codon_fraction("CTACTG", profile) == 0.5

    # Test calculate_cai
    assert abs(calculate_cai("ATGCTG", profile) - 1.0) < 1e-4


def test_pareto_strategy_traits() -> None:
    design = _design()
    profile = default_ecoli_profile()
    result = rank_host_optimization_candidates(design, profile)
    
    high_expr = next(c for c in result.candidates if c.strategy == "high_expression")
    low_burden = next(c for c in result.candidates if c.strategy == "low_burden")
    balanced = next(c for c in result.candidates if c.strategy == "balanced")
    
    assert high_expr.objective_scores["expression"] > low_burden.objective_scores["expression"]
    assert low_burden.objective_scores["low_burden"] > high_expr.objective_scores["low_burden"]
    assert high_expr.objective_scores["expression"] >= balanced.objective_scores["expression"] >= low_burden.objective_scores["expression"]
    assert low_burden.objective_scores["low_burden"] >= balanced.objective_scores["low_burden"] >= high_expr.objective_scores["low_burden"]

