from __future__ import annotations

import json
from pathlib import Path
import sys

from schemas.design_diff import compare_designs
from schemas.design_ir import topology_to_design_ir
from schemas.design_operations import replace_part_immutable, validate_replacement
from schemas.state import DesignState
from tools.cello_artifact_parser import CelloV2JsonParser
from tools.cello_wrapper import CelloWrapper
from tools.part_library import PartLibrary


def test_demo_part_library_is_versioned_and_queryable() -> None:
    library = PartLibrary.demo()

    assert library.library_id == "demo-cello-library"
    assert library.version == "1.0.0"
    assert library.evidence_level == "demo_only"
    assert library.get("DEMO_PhlF_CDS") is not None
    assert {
        part.id
        for part in library.compatible_parts(
            part_type="CDS",
            host_organism="Escherichia coli",
            gate_type="NOT",
        )
    } >= {"DEMO_PhlF_CDS", "DEMO_AmtR_CDS"}


def test_cello_v2_json_parser_resolves_library_parts(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    artifact = output_dir / "example_logic_circuit.json"
    artifact.write_text(
        json.dumps(
            {
                "gates": [
                    {
                        "logic_node_id": "regulator_1_n",
                        "gate_type": "NOT",
                        "score": 0.91,
                        "parts": [
                            {
                                "logic_node_id": "regulator_1_n",
                                "part_id": "DEMO_PhlF_CDS",
                                "role": "CDS",
                            },
                            {
                                "logic_node_id": "logic_promoter_1_n",
                                "part_id": "DEMO_PhlF_PROM",
                                "role": "promoter",
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = CelloV2JsonParser(PartLibrary.demo()).parse_directory(tmp_path)

    assert result.parser == "cello_v2_json"
    assert len(result.assignments) == 2
    cds = next(item for item in result.assignments if item["part_type"] == "CDS")
    assert cds["part_id"] == "DEMO_PhlF_CDS"
    assert cds["sequence"].startswith("AAGTAGGAATTG")
    assert cds["library_version"] == "1.0.0"
    assert cds["gate_type"] == "NOT"


def test_cello_wrapper_parses_assignments_from_output_directory(tmp_path: Path) -> None:
    state = DesignState()
    state.verilog_codes = [
        "module c(input A, output Y); wire n; not(n, A); assign Y = n; endmodule"
    ]
    payload = json.dumps(
        {
            "gates": [
                {
                    "logic_node_id": "regulator_1_n",
                    "gate_type": "NOT",
                    "parts": [
                        {
                            "logic_node_id": "regulator_1_n",
                            "part_id": "DEMO_PhlF_CDS",
                            "role": "CDS",
                        }
                    ],
                }
            ]
        }
    )
    script = (
        "import pathlib,sys; "
        "out=pathlib.Path(sys.argv[1]); "
        f"(out/'candidate_logic_circuit.json').write_text({payload!r}, encoding='utf-8'); "
        "print('Gate Assignment Score: 91')"
    )

    result = CelloWrapper(
        cello_command=[sys.executable, "-c", script, "{output_dir}"],
        artifact_dir=tmp_path / "artifacts",
        timeout_seconds=5,
    ).run(state)
    topology = result.candidate_topologies[0]

    assert topology["mapping_status"] == "mapped"
    assert topology["part_assignments"][0]["part_id"] == "DEMO_PhlF_CDS"
    assert topology["cello_parser"]["name"] == "cello_v2_json"
    design = topology_to_design_ir(topology)
    regulator = next(part for part in design.parts if part.id == "regulator_1_n")
    assert regulator.name == "PhlF regulator"
    assert regulator.sequence.startswith("AAGTAGGAATTG")


def test_replacement_validation_rejects_type_mismatch() -> None:
    design = topology_to_design_ir(
        {"verilog": "module c(input A, output GFP); assign GFP = A; endmodule"}
    )

    validation = validate_replacement(
        design,
        target_part_id="output_cds_GFP",
        replacement_part_id="DEMO_PhlF_PROM",
        library=PartLibrary.demo(),
    )

    assert validation.valid is False
    assert validation.checks["part_type"] == "fail"


def test_replacement_creates_immutable_revision_and_design_diff() -> None:
    original = topology_to_design_ir(
        {"verilog": "module c(input A, output GFP); assign GFP = A; endmodule"},
        design_id="original",
    )
    result = replace_part_immutable(
        original,
        target_part_id="output_cds_GFP",
        replacement_part_id="DEMO_GFP_CDS",
        library=PartLibrary.demo(),
    )

    assert result.validation.valid is True
    assert result.design is not None
    revised = result.design
    original_part = next(part for part in original.parts if part.id == "output_cds_GFP")
    revised_part = next(part for part in revised.parts if part.id == "output_cds_GFP")
    assert original_part.sequence is None
    assert original_part.assignment is None
    assert revised_part.sequence.startswith("ATGCGTAAAGGC")
    assert revised.revision.parent_revision_id == original.revision.revision_id
    assert revised.revision.revision_number == original.revision.revision_number + 1

    diff = compare_designs(
        original,
        revised,
        left_metrics={"score": 0.62, "gate_count": 1},
        right_metrics={"score": 0.71, "gate_count": 1},
    )
    assert len(diff.part_changes) == 1
    assert diff.part_changes[0].part_id == "output_cds_GFP"
    score_change = next(item for item in diff.metric_changes if item.metric == "score")
    assert score_change.delta == 0.09
    assert "Right candidate" in diff.recommendation
