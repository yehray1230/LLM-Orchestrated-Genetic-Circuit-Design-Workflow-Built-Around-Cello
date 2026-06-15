from __future__ import annotations

import json

import pytest

from importers.genbank_importer import genbank_to_import_draft
from schemas.import_draft import (
    DraftInteraction,
    DraftPart,
    FieldEvidence,
    ImportDraft,
    import_draft_from_json,
    import_draft_to_design_ir,
    validate_import_draft,
)


def _valid_draft() -> ImportDraft:
    return ImportDraft(
        draft_id="toggle_switch_2000",
        name="Literature toggle switch",
        source_type="literature",
        source_uri="https://doi.org/10.1038/35002131",
        citation="Gardner et al. (2000)",
        host_organism="Escherichia coli",
        inputs=["IPTG", "aTc"],
        outputs=["GFP"],
        logic_expression="Mutual repression toggle controlling GFP",
        validation_status="experimentally_validated",
        validation_notes="Switching behavior was reported in the source publication.",
        parts=[
            DraftPart(
                id="p_lac",
                name="pLac",
                part_type="promoter",
                role="LacI-regulated promoter",
                evidence=FieldEvidence(
                    field_path="parts.p_lac",
                    status="explicit",
                    locator="Figure 1",
                ),
            ),
            DraftPart(
                id="gfp",
                name="GFP",
                part_type="CDS",
                role="Reporter",
                sequence="atg aaa taa",
                evidence=FieldEvidence(
                    field_path="parts.gfp",
                    status="derived",
                    confidence=0.8,
                ),
            ),
        ],
        interactions=[
            DraftInteraction(
                source="p_lac",
                target="gfp",
                interaction_type="expression",
            )
        ],
        evidence=[
            FieldEvidence(
                field_path="design_summary",
                status="explicit",
                locator="Figure 1 and Methods",
            )
        ],
    )


def test_import_draft_json_round_trip() -> None:
    draft = _valid_draft()

    restored = import_draft_from_json(draft.to_json())

    assert restored.draft_id == draft.draft_id
    assert restored.inputs == ["IPTG", "aTc"]
    assert restored.parts[1].sequence == "atg aaa taa"
    assert restored.parts[0].evidence is not None
    assert restored.parts[0].evidence.locator == "Figure 1"


def test_validation_reports_coverage_without_penalizing_unknown_host() -> None:
    draft = _valid_draft()
    draft.host_organism = "not_reported"

    report = validate_import_draft(draft)

    assert report.can_import is True
    assert "logic" in report.applicable_sections
    assert "host_context" not in report.applicable_sections
    assert any("Host organism" in warning for warning in report.warnings)
    assert 0.0 < report.completeness < 1.0


def test_duplicate_part_ids_block_import() -> None:
    draft = _valid_draft()
    draft.parts.append(
        DraftPart(id="gfp", name="Duplicate GFP", part_type="CDS")
    )

    report = validate_import_draft(draft)

    assert report.can_import is False
    assert any("unique" in error for error in report.errors)
    with pytest.raises(ValueError, match="Cannot import draft"):
        import_draft_to_design_ir(draft)


def test_import_to_design_ir_preserves_provenance_and_partial_sequence_status() -> None:
    design = import_draft_to_design_ir(_valid_draft())

    assert design.design_id == "toggle_switch_2000"
    assert design.validation_status["experimental_validation"] == (
        "experimentally_validated"
    )
    assert design.validation_status["sequences"] == "partial"
    assert design.validation_status["assembly_ready"] == "unknown"
    assert design.provenance[0].source_uri.endswith("35002131")
    assert design.provenance[0].metadata["citation"] == "Gardner et al. (2000)"
    assert design.parts[1].sequence == "ATGAAATAA"
    assert design.parts[1].provenance_ids == ["provenance_toggle_switch_2000"]


def test_json_import_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError, match="one object"):
        import_draft_from_json(json.dumps([{"name": "invalid"}]))


def test_genbank_import_extracts_supported_features_without_inventing_logic() -> None:
    genbank = """LOCUS       TESTCIRCUIT              30 bp    DNA
SOURCE      synthetic DNA construct
  ORGANISM  Escherichia coli
FEATURES             Location/Qualifiers
     promoter        1..6
                     /label="pTet"
                     /note="TetR-regulated promoter"
     RBS             7..12
                     /label="RBS1"
     CDS             13..24
                     /gene="gfp"
                     /product="green fluorescent protein"
ORIGIN
        1 aaaaaacccccc atgaaataataa gggggg
//
"""

    draft = genbank_to_import_draft(genbank, filename="test.gb")

    assert draft.name == "TESTCIRCUIT"
    assert draft.host_organism == "Escherichia coli"
    assert draft.logic_expression == ""
    assert draft.inputs == []
    assert draft.outputs == []
    assert [part.part_type for part in draft.parts] == ["promoter", "RBS", "CDS"]
    assert draft.parts[0].name == "pTet"
    assert draft.parts[2].name == "gfp"
    assert draft.parts[2].sequence == "ATGAAATAATAA"
    assert draft.evidence[0].status == "explicit"
