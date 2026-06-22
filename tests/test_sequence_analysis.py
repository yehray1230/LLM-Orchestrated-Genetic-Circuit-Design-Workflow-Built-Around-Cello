from __future__ import annotations

from benchmark_suite.readiness_evaluator import evaluate_readiness
from schemas.design_ir_v2 import (
    AttributedValue,
    BiologicalContext,
    BiologicalPartV2,
    DesignIRV2,
    DesignSpecification,
)
from schemas.sequence_optimization import SequenceOptimizationRequest
from tools.sequence_analyzer import analyze_design_sequences, analyze_part_sequence
from tools.sequence_optimization import evaluate_sequence_optimization


def _design() -> DesignIRV2:
    return DesignIRV2(
        design_id="sequence_design",
        name="Sequence design",
        specification=DesignSpecification(outputs=["GFP"]),
        biological_context=BiologicalContext(
            host_organism=AttributedValue(
                value="Escherichia coli",
                status="explicit",
            )
        ),
        parts=[
            BiologicalPartV2(
                id="cds_problem",
                name="Problem CDS",
                part_type="CDS",
                role="reporter",
                sequence="ATGAAATAAGGTCTCCCCCCCTAA",
                evidence_level="user_verified",
                host_compatibility=["Escherichia coli"],
            ),
            BiologicalPartV2(
                id="promoter_clean",
                name="Clean promoter",
                part_type="promoter",
                role="expression",
                sequence="TTGACATATAAT",
                evidence_level="user_verified",
                host_compatibility=["Escherichia coli"],
            ),
        ],
        interactions=[],
        constructs=[],
    )


def test_sequence_analyzer_reports_cds_and_type_iis_issues() -> None:
    result = analyze_part_sequence(
        _design().parts[0],
        host_organism="Escherichia coli",
        homopolymer_threshold=6,
    )

    codes = {issue.code for issue in result.issues}

    assert result.status == "blocked"
    assert result.checksum is not None
    assert result.metrics["type_iis_site_count"] == 1
    assert "CDS_INTERNAL_STOP" in codes
    assert "INTERNAL_BSAI_SITE" in codes
    assert "HOMOPOLYMER_RUN" in codes


def test_design_sequence_analysis_rolls_up_summary() -> None:
    result = analyze_design_sequences(_design())

    assert result.status == "blocked"
    assert result.summary["part_count"] == 2
    assert result.summary["blocked_count"] == 1
    assert result.results[1].status == "passed"


def test_sequence_optimization_evaluation_preserves_protein_contract() -> None:
    design = _design()
    request = SequenceOptimizationRequest(
        design_id=design.design_id,
        objective="remove_type_iis_sites",
        host_profile_id="ecoli_default",
        part_ids=["cds_problem"],
        optimized_sequences={
            "cds_problem": "ATGAAAAAAGGTTTACCCAAATAA",
        },
    )

    result = evaluate_sequence_optimization(design, request)[0]

    assert result.status == "blocked"
    assert result.protein_preserved is False
    assert result.changes
    assert result.before_analysis.sequence_id == "cds_problem"
    assert result.after_analysis is not None
    assert result.issues[0]["code"] == "PROTEIN_SEQUENCE_CHANGED"


def test_readiness_accepts_sequence_optimization_result_schema() -> None:
    design = _design()
    request = SequenceOptimizationRequest(
        design_id=design.design_id,
        part_ids=["promoter_clean"],
    )
    optimization = evaluate_sequence_optimization(design, request)[0].to_dict()

    readiness = evaluate_readiness(
        design,
        assembly_report={
            "status": "assembly_check_passed",
            "readiness_status": "assembly_check_passed",
            "issues": [],
        },
        assembly_plan={"status": "ready", "issues": []},
        primer_result={"status": "ready"},
        sequence_optimization_result=optimization,
    )

    assert readiness.readiness_status == "primer_ready"
    assert readiness.next_required_stage == "sequence_optimized"
    assert readiness.domain_scores["primer_readiness_score"] == 1.0
    assert readiness.domain_scores["sequence_optimization_score"] == 0.5
    assert readiness.domain_scores["experimental_readiness_score"] == 0.75
