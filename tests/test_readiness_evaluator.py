from __future__ import annotations

from benchmark_suite.benchmark_controller import evaluate_candidate
from benchmark_suite.readiness_evaluator import evaluate_readiness
from schemas.assembly_plan import (
    AssemblyFragment,
    AssemblyJunction,
    AssemblyPlan,
    PlanIssue,
    RestrictionDigest,
)
from schemas.design_ir_v2 import (
    BiologicalPartV2,
    DesignIRV2,
    DesignSpecification,
)


def _design() -> DesignIRV2:
    return DesignIRV2(
        design_id="readiness_design",
        name="Readiness design",
        specification=DesignSpecification(outputs=["Y"]),
        parts=[
            BiologicalPartV2(
                id="part_1",
                name="Part 1",
                part_type="CDS",
                role="reporter",
                sequence="ATGAAATAA",
                evidence_level="experimentally_characterized",
            ),
            BiologicalPartV2(
                id="part_2",
                name="Part 2",
                part_type="terminator",
                role="termination",
                sequence="GCCGCC",
                evidence_level="literature_supported",
            ),
        ],
        interactions=[],
        constructs=[],
    )


def _assembly_report(*, blocked: bool = False) -> dict:
    issues = (
        [
            {
                "code": "ESSENTIAL_FEATURE_PROTECTED",
                "message": "Essential feature overlap.",
                "severity": "error",
                "subject_id": "ori",
            }
        ]
        if blocked
        else []
    )
    return {
        "status": "blocked" if blocked else "assembly_check_passed",
        "readiness_status": (
            "conceptual" if blocked else "assembly_check_passed"
        ),
        "issues": issues,
    }


def _plan(*, blocked: bool = False) -> AssemblyPlan:
    issues = (
        [
            PlanIssue(
                code="TYPE_IIS_INTERNAL_SITE",
                message="Insert contains an internal BsaI site.",
                severity="error",
                subject_id="insert",
            )
        ]
        if blocked
        else []
    )
    return AssemblyPlan(
        plan_id="plan_1",
        design_id="readiness_design",
        plasmid_id="plasmid_1",
        method="gibson",
        status="blocked" if blocked else "ready",
        backbone_id="backbone_1",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        target_length=1000,
        target_checksum="cdseguid=test",
        fragments=[
            AssemblyFragment(
                fragment_id="backbone",
                name="Backbone",
                source_type="backbone",
                sequence="AAAA",
                core_sequence="AAAA",
            ),
            AssemblyFragment(
                fragment_id="insert",
                name="Insert",
                source_type="insert",
                sequence="CCCC",
                core_sequence="CCCC",
            ),
        ],
        junctions=[
            AssemblyJunction(
                junction_id="junction_1",
                left_fragment_id="backbone",
                right_fragment_id="insert",
                junction_type="homology",
                sequence="AAAACCCC",
                unique=True,
                direction_valid=True,
            )
        ],
        digests=[
            RestrictionDigest(
                molecule_id="backbone",
                enzyme="EcoRI",
                recognition_site="GAATTC",
                cut_positions=[],
                fragment_lengths=[1000],
                circular=True,
            )
        ],
        issues=issues,
    )


def test_existing_weighted_score_is_preserved_with_explicit_alias() -> None:
    result = evaluate_candidate(
        {
            "verilog": "module c(input A, output Y); assign Y = A; endmodule",
            "functional_score": 0.8,
            "kinetic_score": 0.7,
            "plausibility_score": 0.9,
            "gate_count": 1,
        }
    )

    assert result["computational_design_score"] == result["weighted_total_score"]
    assert result["score"] == result["weighted_total_score"]


def test_readiness_separates_domains_and_keeps_future_scores_null() -> None:
    evaluation = {
        "weighted_total_score": 0.82,
        "dimension_scores": {
            "logic_function": 0.9,
            "dynamic_behavior": 0.7,
        },
    }

    result = evaluate_readiness(
        _design(),
        assembly_report=_assembly_report(),
        assembly_plan=_plan(),
        computational_evaluation=evaluation,
    )

    assert result.readiness_status == "assembly_planned"
    assert result.computational_design_score == 0.82
    assert result.domain_scores["logic_score"] == 0.9
    assert result.domain_scores["dynamic_score"] == 0.7
    assert result.domain_scores["part_evidence_score"] == 0.9
    assert result.domain_scores["assembly_plan_score"] == 1.0
    assert result.domain_scores["primer_readiness_score"] is None
    assert result.domain_scores["sequence_optimization_score"] is None
    assert result.domain_scores["host_optimization_score"] is None
    assert result.domain_scores["calibration_score"] is None
    assert result.domain_scores["experimental_readiness_score"] is None
    assert result.next_required_stage == "primer_ready"
    assert result.blockers == []


def test_readiness_accepts_sequence_complete_evidence_without_assembly_plan() -> None:
    result = evaluate_readiness(
        _design(),
        assembly_report={
            "status": "sequence_complete",
            "readiness_status": "sequence_complete",
            "issues": [],
        },
        computational_evaluation={
            "weighted_total_score": 0.74,
            "dimension_scores": {
                "logic_function": 0.8,
                "dynamic_behavior": 0.7,
            },
        },
    )

    assert result.readiness_status == "sequence_complete"
    assert result.next_required_stage == "assembly_planned"
    assert result.completed_stages == ["conceptual", "sequence_complete"]
    assert result.domain_scores["sequence_quality_score"] == 1.0


def test_blocker_forces_blocked_status_despite_high_computational_score() -> None:
    result = evaluate_readiness(
        _design(),
        assembly_report=_assembly_report(),
        assembly_plan=_plan(blocked=True),
        computational_evaluation={
            "weighted_total_score": 0.99,
            "dimension_scores": {
                "logic_function": 0.99,
                "dynamic_behavior": 0.99,
            },
        },
    )

    assert result.computational_design_score == 0.99
    assert result.readiness_status == "blocked"
    assert result.domain_scores["assembly_plan_score"] == 0.0
    assert result.blockers[0].code == "TYPE_IIS_INTERNAL_SITE"


def test_primer_stage_only_advances_when_deliverable_is_ready() -> None:
    result = evaluate_readiness(
        _design(),
        assembly_report=_assembly_report(),
        assembly_plan=_plan(),
        primer_result={"status": "ready"},
    )

    assert result.readiness_status == "primer_ready"
    assert result.next_required_stage == "sequence_optimized"
    assert result.domain_scores["primer_readiness_score"] == 1.0
    assert result.domain_scores["sequence_optimization_score"] is None
    assert result.domain_scores["experimental_readiness_score"] == 1.0


def test_non_experimental_primer_gate_does_not_raise_experimental_readiness() -> None:
    result = evaluate_readiness(
        _design(),
        assembly_report=_assembly_report(),
        assembly_plan=_plan(),
        primer_result={
            "status": "ready",
            "experimental_evidence": False,
            "report_type": "demo_primer_readiness_gate",
        },
    )

    assert result.readiness_status == "primer_ready"
    assert result.domain_scores["primer_readiness_score"] == 1.0
    assert result.domain_scores["experimental_readiness_score"] is None


def test_readiness_reports_split_optimization_domains() -> None:
    result = evaluate_readiness(
        _design(),
        primer_result={"status": "ready"},
        sequence_optimization_result={"status": "passed"},
        host_optimization_result={"status": "ready"},
        calibration_result={"status": "completed"},
    )

    assert result.readiness_status == "host_optimized"
    assert result.domain_scores["primer_readiness_score"] == 1.0
    assert result.domain_scores["sequence_optimization_score"] == 1.0
    assert result.domain_scores["host_optimization_score"] == 1.0
    assert result.domain_scores["calibration_score"] == 1.0
    assert result.domain_scores["experimental_readiness_score"] == 1.0
