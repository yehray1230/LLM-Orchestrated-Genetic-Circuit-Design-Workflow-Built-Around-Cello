from __future__ import annotations

from app import _build_regulatory_graph_dot
from schemas.design_ir import topology_to_design_ir


def test_design_ir_builds_parts_and_constructs_from_primitive_gates() -> None:
    topology = {
        "verilog": (
            "module circuit(input A, input B, output Y); "
            "wire not_b; not(not_b, B); and(Y, A, not_b); endmodule"
        ),
        "cello_mode": "mock",
        "mapping_status": "unmapped",
    }

    design = topology_to_design_ir(topology)

    assert design.inputs == ["A", "B"]
    assert design.outputs == ["Y"]
    assert {part.part_type for part in design.parts} >= {
        "sensor",
        "promoter",
        "RBS",
        "CDS",
        "terminator",
    }
    assert len(design.constructs) == 3
    assert design.validation_status["part_mapping"] == "conceptual"
    assert design.validation_status["assembly_ready"] == "no"


def test_design_ir_builds_output_unit_from_assign_expression() -> None:
    topology = {
        "verilog": "module circuit(input A, input B, output GFP); assign GFP = A & ~B; endmodule",
        "cello_mode": "mock",
        "mapping_status": "unmapped",
    }

    design = topology_to_design_ir(topology, host_organism="E. coli")

    assert design.logic_expression == "GFP = A & ~B"
    assert [construct.name for construct in design.constructs] == [
        "NOT gate transcriptional unit",
        "AND gate transcriptional unit",
        "GFP output transcriptional unit",
    ]
    output_part = next(part for part in design.parts if part.id == "output_cds_GFP")
    assert output_part.host_compatibility == ["E. coli"]
    assert output_part.sequence is None


def test_mock_design_ir_has_explicit_assembly_warnings() -> None:
    design = topology_to_design_ir(
        {
            "verilog": "module circuit(input A, output Y); assign Y = A; endmodule",
            "cello_mode": "mock",
            "mapping_status": "unmapped",
        }
    )

    assert any("conceptual placeholders" in warning for warning in design.warnings)
    assert any("backbone" in warning for warning in design.warnings)
    assert all(
        construct.validation_status["assembly"] == "not_checked"
        for construct in design.constructs
    )


def test_external_mapping_is_distinguished_from_sequence_readiness() -> None:
    design = topology_to_design_ir(
        {
            "verilog": "module circuit(input A, output Y); assign Y = A; endmodule",
            "cello_mode": "external",
            "mapping_status": "mapped",
        }
    )

    assert design.validation_status["part_mapping"] == "external_mapping"
    assert design.validation_status["sequences"] == "missing"
    assert design.validation_status["assembly_ready"] == "no"


def test_regulatory_graph_distinguishes_activation_and_repression() -> None:
    design = topology_to_design_ir(
        {
            "verilog": (
                "module c(input A, input B, output Y); "
                "wire n; not(n, B); and(Y, A, n); endmodule"
            )
        }
    )

    dot = _build_regulatory_graph_dot(design)

    assert 'arrowhead="tee"' in dot
    assert 'arrowhead="normal"' in dot
    assert "P_logic" in dot


def test_design_ir_applies_assignment_sequence_provenance_and_revision() -> None:
    design = topology_to_design_ir(
        {
            "verilog": "module c(input A, output GFP); assign GFP = A; endmodule",
            "cello_mode": "external",
            "mapping_status": "mapped",
            "source": "external_cello_wrapper",
            "cello_artifact_manifest_path": "outputs/cello/artifact_manifest.json",
            "cello_artifact_manifest": {
                "run_id": "cello_123",
                "created_at": "2026-06-06T10:00:00+00:00",
                "files": [{"relative_path": "output/design.json"}],
            },
            "part_assignments": [
                {
                    "logic_node_id": "output_cds_GFP",
                    "part_id": "BBa_E0040",
                    "part_name": "GFP",
                    "part_type": "CDS",
                    "library_id": "demo_library_v1",
                    "sequence": "atg aaa taa",
                    "confidence": 0.94,
                }
            ],
            "design_revision": {
                "revision_id": "revision_2",
                "parent_revision_id": "revision_1",
                "revision_number": 2,
                "change_type": "part_mapping",
                "summary": "Mapped GFP output",
            },
        }
    )

    output_part = next(part for part in design.parts if part.id == "output_cds_GFP")
    assert output_part.sequence == "ATGAAATAA"
    assert output_part.assignment is not None
    assert output_part.assignment.part_id == "BBa_E0040"
    assert output_part.provenance_ids == ["provenance_cello_123"]
    assert design.assignments[0].library_id == "demo_library_v1"
    assert design.provenance[0].artifact_manifest_path.endswith("artifact_manifest.json")
    assert design.revision.revision_id == "revision_2"
    assert design.revision.parent_revision_id == "revision_1"
    assert design.validation_status["sequences"] == "partial"
