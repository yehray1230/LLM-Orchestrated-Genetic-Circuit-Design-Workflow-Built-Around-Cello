from __future__ import annotations

from exporters.plasmid_assembler import export_plasmid_genbank
from schemas.design_ir import DesignIR, topology_to_design_ir


def _complete_design() -> DesignIR:
    design = topology_to_design_ir(
        {
            "verilog": (
                "module c(input A, output GFP); "
                "wire n; not(n, A); assign GFP = n; endmodule"
            )
        },
        design_id="plasmid_test",
    )
    sequences = {
        "promoter": "TTGACA",
        "RBS": "AGGAGG",
        "CDS": "ATGAAATAA",
        "terminator": "GCCGCC",
        "sensor": "ATGCCCTAA",
    }
    for part in design.parts:
        part.sequence = sequences[part.part_type]
        part.confidence = "test_fixture"
    design.validation_status["sequences"] = "complete"
    return design


def test_plasmid_export_invalid_backbone() -> None:
    design = _complete_design()
    result = export_plasmid_genbank(design, "InvalidBackbone")
    
    assert result.ok is False
    assert result.status == "blocked_invalid_backbone"
    assert any("Unsupported backbone template" in err for err in result.errors)


def test_plasmid_export_blocks_incomplete() -> None:
    design = topology_to_design_ir(
        {"verilog": "module c(input A, output GFP); assign GFP = A; endmodule"}
    )
    result = export_plasmid_genbank(design, "pUC19 (High copy, AmpR)")
    
    assert result.ok is False
    assert result.status == "blocked_missing_sequences"


def test_plasmid_export_blocks_invalid_dna() -> None:
    design = _complete_design()
    # 破壞一個 construct 中的 part sequence，使其不符合 IUPAC DNA 規範
    construct_part_id = design.constructs[0].parts[0]
    part = next(p for p in design.parts if p.id == construct_part_id)
    part.sequence = "ATG_INVALID"
    
    result = export_plasmid_genbank(design, "pUC19 (High copy, AmpR)")
    
    assert result.ok is False
    assert result.status == "blocked_invalid_sequences"
    assert any("non-IUPAC" in err for err in result.errors)


def test_plasmid_export_success_puc19() -> None:
    design = _complete_design()
    result = export_plasmid_genbank(design, "pUC19 (High copy, AmpR)")
    
    assert result.ok is True
    assert result.status == "ready"
    assert "circular" in result.content
    assert "LOCUS       " in result.content
    
    # 檢查是否含有電路元件及骨架元件的 Feature
    assert "pUC ori" in result.content
    assert "AmpR CDS" in result.content
    assert "GFP" in result.content
    
    # 檢查 Linker
    assert "Linker" in result.content


def test_plasmid_export_restriction_site_warnings() -> None:
    design = _complete_design()
    # 插入一個含有 BsaI 位點 (GGTCTC) 的序列到 construct 的 part 中
    construct_part_id = design.constructs[0].parts[0]
    part = next(p for p in design.parts if p.id == construct_part_id)
    part.sequence = "GGTCTC" + part.sequence
    
    result = export_plasmid_genbank(design, "pUC19 (High copy, AmpR)")
    
    assert result.ok is True
    assert any("Restriction site conflict: Found BsaI site" in w for w in result.warnings)
