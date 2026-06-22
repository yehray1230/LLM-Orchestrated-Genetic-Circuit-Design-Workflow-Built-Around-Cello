from __future__ import annotations

from io import StringIO
from pathlib import Path
import random

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import FeatureLocation, SeqFeature
from Bio.SeqRecord import SeqRecord
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
    PlasmidV2,
)
from tools.assembly_planner import analyze_restriction_digest


def _sequence(length: int = 260) -> str:
    randomizer = random.Random(982451653)
    while True:
        sequence = "".join(
            randomizer.choice("ACGT") for _ in range(length)
        )
        forbidden = {
            "GGTCTC",
            "GAGACC",
            "CGTCTC",
            "GAGACG",
            "GAATTC",
            "TCTAGA",
            "ACTAGT",
            "CTGCAG",
        }
        if not any(site in sequence for site in forbidden):
            return sequence


def _backbone_genbank(sequence: str | None = None) -> str:
    selected = sequence or _sequence()
    record = SeqRecord(
        Seq(selected),
        id="PLANNER_BACKBONE",
        name="PLANBACKBONE",
        description="Assembly planner test backbone",
        annotations={"molecule_type": "DNA", "topology": "circular"},
        features=[
            SeqFeature(
                FeatureLocation(10, 45, strand=1),
                type="rep_origin",
                qualifiers={"label": ["planner ori"]},
            ),
            SeqFeature(
                FeatureLocation(100, 120, strand=1),
                type="misc_feature",
                qualifiers={"label": ["replaceable cassette"]},
            ),
            SeqFeature(
                FeatureLocation(190, 235, strand=1),
                type="CDS",
                qualifiers={"label": ["planner marker"]},
            ),
        ],
    )
    output = StringIO()
    SeqIO.write(record, output, "genbank")
    return output.getvalue()


def _backbone_payload(sequence: str | None = None) -> dict:
    return {
        "backbone_id": "planner_backbone",
        "version": "1.0.0",
        "name": "Planner backbone",
        "source_type": "user_verified",
        "source_uri": "https://example.org/planner-backbone",
        "genbank": _backbone_genbank(sequence),
        "host_organisms": ["Escherichia coli"],
        "origin_of_replication": "planner ori",
        "selection_marker": "planner marker",
        "copy_number_class": "medium",
        "insertion_regions": [
            {
                "region_id": "mcs",
                "name": "MCS",
                "start": 90,
                "end": 130,
            }
        ],
        "essential_regions": [
            {
                "region_id": "ori",
                "name": "planner ori",
                "start": 10,
                "end": 45,
            },
            {
                "region_id": "marker",
                "name": "planner marker",
                "start": 190,
                "end": 235,
            },
        ],
    }


def _design(insert_sequence: str = "ATGAAACCCGGGTTTTAA") -> DesignIRV2:
    return DesignIRV2(
        design_id="planner_design",
        name="Planner design",
        specification=DesignSpecification(outputs=["reporter"]),
        biological_context=BiologicalContext(
            host_organism=AttributedValue(
                value="Escherichia coli",
                status="explicit",
            )
        ),
        parts=[
            BiologicalPartV2(
                id="insert",
                name="Planner insert",
                part_type="CDS",
                role="reporter",
                sequence=insert_sequence,
                source="test",
                evidence_level="user_verified",
                host_compatibility=["Escherichia coli"],
            )
        ],
        interactions=[],
        constructs=[
            ConstructV2(
                id="construct_1",
                name="Insert construct",
                part_instances=[
                    ConstructPart(
                        instance_id="insert_1",
                        part_id="insert",
                        order=1,
                    )
                ],
            )
        ],
        plasmids=[
            PlasmidV2(
                id="plasmid_1",
                name="Planned plasmid",
                construct_ids=["construct_1"],
            )
        ],
    )


def _services(tmp_path: Path, *, insert_sequence: str | None = None):
    services = create_application_services(tmp_path / "api_data")
    design = _design(insert_sequence or "ATGAAACCCGGGTTTTAA")
    services.designs.repository.save(design.design_id, design.to_dict())
    services.backbones.register(_backbone_payload())
    return services


def test_restriction_digest_reports_linear_and_circular_fragments() -> None:
    sequence = "AAAAGAATTCCCCCCCCCCGAATTCTTTT"

    linear = analyze_restriction_digest(
        "linear",
        sequence,
        ["EcoRI"],
        circular=False,
    )[0]
    circular = analyze_restriction_digest(
        "circular",
        sequence,
        ["EcoRI"],
        circular=True,
    )[0]

    assert len(linear.cut_positions) == 2
    assert sum(linear.fragment_lengths) == len(sequence)
    assert len(linear.fragment_lengths) == 3
    assert sum(circular.fragment_lengths) == len(sequence)
    assert len(circular.fragment_lengths) == 2


def test_gibson_planner_builds_fragments_unique_junctions_and_pydna_product(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)

    result = services.assembly_plans.plan(
        "planner_design",
        plasmid_id="plasmid_1",
        backbone_id="planner_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=100,
        insertion_end=120,
        method="gibson",
        gibson_overlap_length=20,
    )

    assert result["ok"] is True
    plan = result["plan"]
    assert plan["status"] == "ready"
    assert len(plan["fragments"]) == 2
    assert len(plan["junctions"]) == 2
    assert all(item["unique"] for item in plan["junctions"])
    assert all(
        item["scar_type"] == "seamless_homology"
        and item["retained_in_product"] is False
        for item in plan["scars"]
    )
    assert plan["method_details"]["pydna_circular_product_count"] >= 1
    assert plan["target_length"] in plan["method_details"]["pydna_product_lengths"]


def test_gibson_planner_blocks_nonunique_overlaps(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    design = _design()
    services.designs.repository.save(design.design_id, design.to_dict())
    services.backbones.register(_backbone_payload("A" * 260))

    result = services.assembly_plans.plan(
        "planner_design",
        plasmid_id="plasmid_1",
        backbone_id="planner_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=100,
        insertion_end=120,
        method="gibson",
        gibson_overlap_length=20,
    )

    assert result["ok"] is False
    assert any(
        issue["code"] == "GIBSON_OVERLAP_NOT_UNIQUE"
        for issue in result["plan"]["blockers"]
    )


def test_golden_gate_planner_reports_directional_overhangs(tmp_path: Path) -> None:
    services = _services(tmp_path)

    result = services.assembly_plans.plan(
        "planner_design",
        plasmid_id="plasmid_1",
        backbone_id="planner_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=100,
        insertion_end=120,
        method="golden_gate",
        golden_gate_enzyme="BsaI",
        golden_gate_overhangs=["AATG", "GCTT"],
    )

    assert result["ok"] is True
    plan = result["plan"]
    assert plan["method_details"]["directional"] is True
    assert plan["method_details"]["overhangs"] == ["AATG", "GCTT"]
    assert plan["method_details"]["pydna_circular_product_count"] >= 1
    assert (
        plan["method_details"]["planned_scarred_product_length"]
        in plan["method_details"]["pydna_product_lengths"]
    )
    assert all(item["direction_valid"] for item in plan["junctions"])
    assert all(
        item["scar_type"] == "golden_gate_fusion"
        and item["retained_in_product"] is True
        for item in plan["scars"]
    )


def test_golden_gate_blocks_internal_type_iis_site(tmp_path: Path) -> None:
    services = _services(
        tmp_path,
        insert_sequence="ATGGGTCTCAAATAA",
    )

    result = services.assembly_plans.plan(
        "planner_design",
        plasmid_id="plasmid_1",
        backbone_id="planner_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=100,
        insertion_end=120,
        method="golden_gate",
        golden_gate_enzyme="BsaI",
        golden_gate_overhangs=["AATG", "GCTT"],
    )

    assert result["ok"] is False
    assert any(
        issue["code"] == "TYPE_IIS_INTERNAL_SITE"
        and issue["subject_id"] == "insert"
        for issue in result["plan"]["blockers"]
    )


def test_golden_gate_blocks_reverse_complement_overhang_conflict(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)

    result = services.assembly_plans.plan(
        "planner_design",
        plasmid_id="plasmid_1",
        backbone_id="planner_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=100,
        insertion_end=120,
        method="golden_gate",
        golden_gate_overhangs=["AATG", "CATT"],
    )

    assert result["ok"] is False
    assert any(
        issue["code"] == "GOLDEN_GATE_OVERHANG_CONFLICT"
        for issue in result["plan"]["blockers"]
    )


def test_restriction_cloning_selects_unique_directional_pair(
    tmp_path: Path,
) -> None:
    sequence = list(_sequence())
    sequence[55:61] = list("GAATTC")
    sequence[155:161] = list("TCTAGA")
    services = create_application_services(tmp_path / "api_data")
    design = _design()
    services.designs.repository.save(design.design_id, design.to_dict())
    services.backbones.register(_backbone_payload("".join(sequence)))

    result = services.assembly_plans.plan(
        "planner_design",
        plasmid_id="plasmid_1",
        backbone_id="planner_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=100,
        insertion_end=120,
        method="restriction_cloning",
        restriction_enzymes=["EcoRI", "XbaI"],
    )

    assert result["ok"] is True
    plan = result["plan"]
    assert plan["method_details"]["selected_enzymes"] == ["EcoRI", "XbaI"]
    assert len(plan["junctions"]) == 2
    assert {
        scar["sequence"] for scar in plan["scars"]
    } == {"GAATTC", "TCTAGA"}


def test_assembly_plan_api_returns_fragment_and_junction_report(
    tmp_path: Path,
) -> None:
    services = _services(tmp_path)
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v2/designs/planner_design/assembly-plans",
                json={
                    "plasmid_id": "plasmid_1",
                    "backbone_id": "planner_backbone",
                    "backbone_version": "1.0.0",
                    "insertion_region_id": "mcs",
                    "insertion_start": 100,
                    "insertion_end": 120,
                    "method": "gibson",
                    "restriction_enzymes": ["EcoRI", "BsaI", "BsmBI"],
                    "gibson_overlap_length": 20,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    plan = response.json()["data"]["plan"]
    assert plan["method"] == "gibson"
    assert len(plan["fragments"]) == 2
    assert len(plan["digests"]) == 9
    readiness = response.json()["data"]["readiness"]
    assert readiness["readiness_status"] == "assembly_planned"
    assert readiness["domain_scores"]["assembly_plan_score"] == 1.0
    assert readiness["domain_scores"]["experimental_readiness_score"] is None
