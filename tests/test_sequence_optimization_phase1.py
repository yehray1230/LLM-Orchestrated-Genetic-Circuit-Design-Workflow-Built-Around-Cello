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
    ConstructPart,
    ConstructV2,
    DesignIRV2,
    DesignSpecification,
)
from schemas.host_profile import default_ecoli_profile
from schemas.sequence_optimization import SequenceOptimizationRequest
from tools.sequence_analyzer import analyze_part_sequence
from tools.sequence_optimization import (
    evaluate_sequence_optimization,
    generate_host_optimized_sequences,
)


def _design() -> DesignIRV2:
    return DesignIRV2(
        design_id="phase1_design",
        name="Phase 1 design",
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
        constructs=[
            ConstructV2(
                id="tu_1",
                name="Expression unit",
                part_instances=[
                    ConstructPart(
                        instance_id="reporter_cds_1",
                        part_id="reporter_cds",
                        order=1,
                    )
                ],
            )
        ],
    )


def test_host_profile_guides_safe_synonymous_codon_optimization() -> None:
    design = _design()
    profile = default_ecoli_profile()

    generated = generate_host_optimized_sequences(design, profile)
    request = SequenceOptimizationRequest(
        design_id=design.design_id,
        objective="codon_optimization",
        host_profile_id=profile.profile_id,
        part_ids=["reporter_cds"],
        optimized_sequences=generated,
        dry_run=False,
    )
    result = evaluate_sequence_optimization(design, request)[0]

    assert generated["reporter_cds"] != "ATGGGTCTCTAA"
    assert "GGTCTC" not in generated["reporter_cds"]
    assert result.status == "passed"
    assert result.protein_preserved is True
    assert analyze_part_sequence(
        _design().parts[0],
        host_organism="Escherichia coli",
    ).status == "warning"
    assert result.after_analysis is not None
    assert result.after_analysis.status == "passed"


def test_sequence_optimization_revision_is_saved_with_diff_and_readiness(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save_v2(_design())

    response = services.sequence_quality.create_optimized_revision(
        "phase1_design",
        {
            "host_profile_id": "ecoli_k12_default",
            "part_ids": ["reporter_cds"],
            "objective": "codon_optimization",
        },
    )

    saved = services.designs.get_v2("phase1_design")

    assert response["ok"] is True
    assert response["status"] == "passed"
    assert saved is not None
    assert saved.parts[0].sequence != "ATGGGTCTCTAA"
    assert saved.revision.change_type == "sequence_optimization"
    assert saved.validation_status["sequence_optimization"] == "passed"
    assert response["diff"]["part_changes"][0]["part_id"] == "reporter_cds"
    assert response["readiness"]["readiness_status"] == "sequence_optimized"
    assert len(services.designs.revisions("phase1_design")) == 2


def test_v2_host_profile_and_sequence_optimization_revision_api(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save_v2(_design())
    app.dependency_overrides[get_services] = lambda: services
    with TestClient(app) as client:
        profiles = client.get("/api/v2/host-profiles")
        revision = client.post(
            "/api/v2/designs/phase1_design/sequence-optimization/revisions",
            json={
                "host_profile_id": "ecoli_k12_default",
                "part_ids": ["reporter_cds"],
            },
        )
    app.dependency_overrides.clear()

    assert profiles.status_code == 200
    assert profiles.json()["data"]["count"] >= 1
    assert revision.status_code == 200
    data = revision.json()["data"]
    assert data["optimization"]["status"] == "passed"
    assert data["design"]["revision"]["change_type"] == "sequence_optimization"
