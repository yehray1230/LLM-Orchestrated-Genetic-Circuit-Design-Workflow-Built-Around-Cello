from __future__ import annotations

from io import StringIO
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import FeatureLocation, SeqFeature
from Bio.SeqRecord import SeqRecord
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from exporters.plasmid_tools import assemble_plasmid_v2
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


def _design() -> DesignIRV2:
    return DesignIRV2(
        design_id="assembly_design",
        name="Assembly design",
        specification=DesignSpecification(outputs=["GFP"]),
        biological_context=BiologicalContext(
            host_organism=AttributedValue(
                value="Escherichia coli",
                status="explicit",
            )
        ),
        parts=[
            BiologicalPartV2(
                id="promoter",
                name="Test promoter",
                part_type="promoter",
                role="transcription initiation",
                sequence="AAAAC",
                source="test",
                evidence_level="user_verified",
                host_compatibility=["Escherichia coli"],
            ),
            BiologicalPartV2(
                id="reporter",
                name="Reverse reporter",
                part_type="CDS",
                role="reporter",
                sequence="ATGAAATAA",
                source="test",
                evidence_level="user_verified",
                host_compatibility=["Escherichia coli"],
            ),
        ],
        interactions=[],
        constructs=[
            ConstructV2(
                id="construct_1",
                name="Reporter cassette",
                part_instances=[
                    ConstructPart(
                        instance_id="promoter_1",
                        part_id="promoter",
                        orientation="forward",
                        order=1,
                    ),
                    ConstructPart(
                        instance_id="reporter_1",
                        part_id="reporter",
                        orientation="reverse",
                        order=2,
                    ),
                ],
            )
        ],
        plasmids=[
            PlasmidV2(
                id="plasmid_1",
                name="Test plasmid",
                construct_ids=["construct_1"],
                backbone=AttributedValue(
                    value="test_backbone.gb",
                    status="explicit",
                ),
            )
        ],
    )


def _backbone_genbank() -> str:
    record = SeqRecord(
        Seq("A" * 100),
        id="BACKBONE1",
        name="BACKBONE1",
        description="Test circular backbone",
        annotations={"molecule_type": "DNA", "topology": "circular"},
        features=[
            SeqFeature(
                FeatureLocation(5, 20, strand=1),
                type="rep_origin",
                qualifiers={"label": ["test ori"]},
            ),
            SeqFeature(
                FeatureLocation(40, 50, strand=1),
                type="misc_feature",
                qualifiers={"label": ["replaceable cassette"]},
            ),
            SeqFeature(
                FeatureLocation(70, 80, strand=1),
                type="CDS",
                qualifiers={"label": ["marker"]},
            ),
        ],
    )
    output = StringIO()
    SeqIO.write(record, output, "genbank")
    return output.getvalue()


def _backbone_payload() -> dict:
    return {
        "backbone_id": "test_backbone",
        "version": "1.0.0",
        "name": "Test backbone",
        "source_type": "user_verified",
        "source_uri": "https://example.org/backbones/test_backbone/1.0.0",
        "genbank": _backbone_genbank(),
        "host_organisms": ["Escherichia coli"],
        "origin_of_replication": "test ori",
        "selection_marker": "marker",
        "copy_number_class": "medium",
        "insertion_regions": [
            {
                "region_id": "mcs",
                "name": "Multiple cloning site",
                "start": 35,
                "end": 60,
            }
        ],
        "essential_regions": [
            {
                "region_id": "ori",
                "name": "test ori",
                "start": 5,
                "end": 20,
            },
            {
                "region_id": "marker",
                "name": "marker",
                "start": 70,
                "end": 80,
            },
        ],
    }


def test_assemble_plasmid_v2_round_trips_real_genbank() -> None:
    result = assemble_plasmid_v2(
        _design(),
        plasmid_id="plasmid_1",
        backbone_genbank=_backbone_genbank(),
        insertion_start=40,
        insertion_end=50,
        assembly_method="direct_insertion",
    )

    assert result.ok is True
    assert result.report.status == "assembly_check_passed"
    assert result.report.backbone_length == 100
    assert result.report.insert_length == 14
    assert result.report.assembled_length == 104
    assert result.report.removed_backbone_features == ["replaceable cassette"]
    assert result.report.pydna_circular is True
    assert result.report.sequence_checksum.startswith("cdseguid=")
    assert result.report.external_tools["biopython"] != "unavailable"
    assert result.report.external_tools["pydna"] != "unavailable"

    assembled = SeqIO.read(StringIO(result.genbank), "genbank")
    assert str(assembled.seq[40:54]) == "AAAACTTATTTCAT"
    reporter = next(
        feature
        for feature in assembled.features
        if feature.qualifiers.get("part_id") == ["reporter"]
    )
    marker = next(
        feature
        for feature in assembled.features
        if feature.qualifiers.get("label") == ["marker"]
    )
    assert reporter.location.strand == -1
    assert int(marker.location.start) == 74


def test_assemble_plasmid_v2_blocks_missing_part_sequence() -> None:
    design = _design()
    design.parts[1].sequence = None

    result = assemble_plasmid_v2(
        design,
        plasmid_id="plasmid_1",
        backbone_genbank=_backbone_genbank(),
        insertion_start=40,
        insertion_end=50,
    )

    assert result.ok is False
    assert result.report.status == "blocked"
    assert result.genbank == ""
    assert result.report.blockers[0].code == "MISSING_SEQUENCE"


def test_assemble_plasmid_v2_rejects_invalid_window() -> None:
    try:
        assemble_plasmid_v2(
            _design(),
            plasmid_id="plasmid_1",
            backbone_genbank=_backbone_genbank(),
            insertion_start=90,
            insertion_end=110,
        )
    except ValueError as exc:
        assert "exceeds backbone length" in str(exc)
    else:
        raise AssertionError("Expected invalid insertion coordinates to fail.")


def test_v2_api_assembles_saved_design(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.repository.save("assembly_design", _design().to_dict())
    services.backbones.register(_backbone_payload())
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v2/designs/assembly_design/plasmid-assemblies",
                json={
                    "plasmid_id": "plasmid_1",
                    "backbone_id": "test_backbone",
                    "backbone_version": "1.0.0",
                    "insertion_region_id": "mcs",
                    "insertion_start": 40,
                    "insertion_end": 50,
                    "assembly_method": "gibson",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ok"] is True
    assert data["report"]["status"] == "assembly_check_passed"
    assert data["report"]["assembly_method"] == "gibson"
    assert data["report"]["readiness_status"] == "assembly_check_passed"
    assert data["report"]["readiness_history"] == [
        "conceptual",
        "sequence_complete",
        "assembly_method_selected",
        "assembly_check_passed",
    ]
    assert any(
        issue["code"] == "GIBSON_OVERLAPS_NOT_DESIGNED"
        for issue in data["report"]["issues"]
    )
    assert data["genbank"].startswith("LOCUS")


def test_v2_api_registers_lists_and_fetches_backbone(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v2/backbones",
                json=_backbone_payload(),
            )
            listed = client.get("/api/v2/backbones")
            fetched = client.get(
                "/api/v2/backbones/test_backbone/versions/1.0.0"
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["data"]["sequence_checksum"].startswith("sha256:")
    assert listed.json()["data"]["count"] == 1
    assert fetched.status_code == 200
    assert fetched.json()["data"]["insertion_regions"][0]["region_id"] == "mcs"


def test_backbone_registry_rejects_unknown_source(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    payload = _backbone_payload()
    payload["source_type"] = "unknown"

    try:
        services.backbones.register(payload)
    except ValueError as exc:
        assert "trusted source" in str(exc)
    else:
        raise AssertionError("Expected an unknown backbone source to fail.")


def test_backbone_registry_versions_are_checksum_immutable(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")
    original = services.backbones.register(_backbone_payload())
    changed = _backbone_payload()
    changed["genbank"] = changed["genbank"].replace(
        "aaaaaaaaaa",
        "caaaaaaaaa",
        1,
    )

    try:
        services.backbones.register(changed)
    except ValueError as exc:
        assert "different checksum" in str(exc)
    else:
        raise AssertionError("Expected checksum drift to fail.")
    assert services.backbones.get(
        original.backbone_id,
        original.version,
    ) == original


def test_registered_assembly_blocks_essential_region(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.repository.save("assembly_design", _design().to_dict())
    services.backbones.register(_backbone_payload())

    result = services.plasmid_assemblies.assemble(
        "assembly_design",
        plasmid_id="plasmid_1",
        backbone_id="test_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=10,
        insertion_end=15,
    )

    assert result.ok is False
    assert result.report.readiness_status == "conceptual"
    assert {
        issue.code for issue in result.report.blockers
    } >= {
        "INSERTION_OUTSIDE_LEGAL_REGION",
        "ESSENTIAL_FEATURE_PROTECTED",
    }


def test_registered_assembly_blocks_illustrative_part(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    design = _design()
    design.parts[0].evidence_level = "illustrative"
    services.designs.repository.save("assembly_design", design.to_dict())
    services.backbones.register(_backbone_payload())

    result = services.plasmid_assemblies.assemble(
        "assembly_design",
        plasmid_id="plasmid_1",
        backbone_id="test_backbone",
        backbone_version="1.0.0",
        insertion_region_id="mcs",
        insertion_start=40,
        insertion_end=50,
    )

    assert result.ok is False
    assert any(
        issue.code == "PART_EVIDENCE_INSUFFICIENT"
        for issue in result.report.blockers
    )
