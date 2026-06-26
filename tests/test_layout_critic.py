from __future__ import annotations

from benchmark_suite.layout_critic import analyze_layout_issues, layout_issues_report
from schemas.design_ir_v2 import (
    DesignIRV2,
    BiologicalPartV2,
    ConstructV2,
    ConstructPart,
    PlasmidV2,
    AttributedValue,
    BiologicalContext,
    DesignSpecification,
)


def _base_design(parts: list[BiologicalPartV2], constructs: list[ConstructV2]) -> DesignIRV2:
    return DesignIRV2(
        design_id="test_layout_critic_design",
        name="Test Layout Critic Design",
        specification=DesignSpecification(outputs=["GFP"]),
        biological_context=BiologicalContext(
            host_organism=AttributedValue(value="Escherichia coli", status="explicit")
        ),
        parts=parts,
        interactions=[],
        constructs=constructs,
        plasmids=[
            PlasmidV2(
                id="plasmid_1",
                name="Test Plasmid",
                construct_ids=[c.id for c in constructs],
                backbone=AttributedValue(value="mock_backbone", status="explicit")
            )
        ]
    )


def test_layout_critic_missing_terminator() -> None:
    # Promoter -> CDS (No Terminator)
    parts = [
        BiologicalPartV2(id="p1", name="p1", part_type="promoter", role="", sequence="ATCG", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="c1", name="c1", part_type="cds", role="", sequence="ATGAAATAA", host_compatibility=["Escherichia coli"]),
    ]
    constructs = [
        ConstructV2(
            id="c_id",
            name="c_name",
            part_instances=[
                ConstructPart(instance_id="p1_inst", part_id="p1", orientation="forward", order=1),
                ConstructPart(instance_id="c1_inst", part_id="c1", orientation="forward", order=2),
            ]
        )
    ]
    design = _base_design(parts, constructs)
    issues = analyze_layout_issues(design, design.plasmids[0])
    
    assert any(issue.code == "MISSING_TERMINATOR" for issue in issues)

    report = layout_issues_report(design, design.plasmids[0])
    assert report["report_type"] == "layout_critic_report"
    assert report["schema_version"] == "1.0.0"
    assert report["issue_count"] == len(issues)
    assert report["issues"][0]["schema_version"] == "1.0.0"
    assert {"code", "severity", "subject_id", "message"} <= set(report["issues"][0])


def test_layout_critic_read_through_risk() -> None:
    # Promoter -> CDS -> Promoter -> Terminator
    parts = [
        BiologicalPartV2(id="p1", name="p1", part_type="promoter", role="", sequence="ATCG", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="c1", name="c1", part_type="cds", role="", sequence="ATGAAATAA", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="p2", name="p2", part_type="promoter", role="", sequence="CGAT", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="t1", name="t1", part_type="terminator", role="", sequence="TTTTT", host_compatibility=["Escherichia coli"]),
    ]
    constructs = [
        ConstructV2(
            id="c_id",
            name="c_name",
            part_instances=[
                ConstructPart(instance_id="p1_inst", part_id="p1", orientation="forward", order=1),
                ConstructPart(instance_id="c1_inst", part_id="c1", orientation="forward", order=2),
                ConstructPart(instance_id="p2_inst", part_id="p2", orientation="forward", order=3),
                ConstructPart(instance_id="t1_inst", part_id="t1", orientation="forward", order=4),
            ]
        )
    ]
    design = _base_design(parts, constructs)
    issues = analyze_layout_issues(design, design.plasmids[0])
    
    assert any(issue.code == "READ_THROUGH_RISK" for issue in issues)


def test_layout_critic_missing_promoter_and_rbs() -> None:
    # CDS standing alone without promoter/RBS
    parts = [
        BiologicalPartV2(id="c1", name="c1", part_type="cds", role="", sequence="ATGAAATAA", host_compatibility=["Escherichia coli"]),
    ]
    constructs = [
        ConstructV2(
            id="c_id",
            name="c_name",
            part_instances=[
                ConstructPart(instance_id="c1_inst", part_id="c1", orientation="forward", order=1),
            ]
        )
    ]
    design = _base_design(parts, constructs)
    issues = analyze_layout_issues(design, design.plasmids[0])
    
    assert any(issue.code == "MISSING_PROMOTER" for issue in issues)


def test_layout_critic_promoter_interference() -> None:
    # Divergent promoters spaced closely (< 50bp)
    # Forward/reverse order:
    # 1. Reverse promoter p1
    # 2. Forward promoter p2
    parts = [
        BiologicalPartV2(id="p1", name="p1", part_type="promoter", role="", sequence="AT", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="p2", name="p2", part_type="promoter", role="", sequence="CG", host_compatibility=["Escherichia coli"]),
    ]
    constructs = [
        ConstructV2(
            id="c_id",
            name="c_name",
            part_instances=[
                ConstructPart(instance_id="p1_inst", part_id="p1", orientation="reverse", order=1),
                ConstructPart(instance_id="p2_inst", part_id="p2", orientation="forward", order=2),
            ]
        )
    ]
    design = _base_design(parts, constructs)
    issues = analyze_layout_issues(design, design.plasmids[0])
    
    assert any(issue.code == "PROMOTER_INTERFERENCE" for issue in issues)


def test_layout_critic_convergent_collision() -> None:
    # Forward CDS -> Reverse CDS without intervening terminator
    parts = [
        BiologicalPartV2(id="p1", name="p1", part_type="promoter", role="", sequence="A", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="c1", name="c1", part_type="cds", role="", sequence="ATG", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="c2", name="c2", part_type="cds", role="", sequence="CAT", host_compatibility=["Escherichia coli"]),
        BiologicalPartV2(id="p2", name="p2", part_type="promoter", role="", sequence="T", host_compatibility=["Escherichia coli"]),
    ]
    constructs = [
        ConstructV2(
            id="c_id",
            name="c_name",
            part_instances=[
                ConstructPart(instance_id="p1_inst", part_id="p1", orientation="forward", order=1),
                ConstructPart(instance_id="c1_inst", part_id="c1", orientation="forward", order=2),
                ConstructPart(instance_id="c2_inst", part_id="c2", orientation="reverse", order=3),
                ConstructPart(instance_id="p2_inst", part_id="p2", orientation="reverse", order=4),
            ]
        )
    ]
    design = _base_design(parts, constructs)
    issues = analyze_layout_issues(design, design.plasmids[0])
    
    assert any(issue.code == "CONVERGENT_COLLISION_RISK" for issue in issues)
