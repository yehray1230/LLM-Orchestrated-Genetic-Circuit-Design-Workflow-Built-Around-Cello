from __future__ import annotations

import json
from pathlib import Path

import pytest

from application.services import create_application_services
from api.dependencies import get_services
from api.main import app
from fastapi.testclient import TestClient
from mcp_server.run_store import RunStore
from repositories.json_repository import JsonRepository, RepositoryError
from repositories.sqlite_repository import (
    DATABASE_SCHEMA_VERSION,
    SqliteDesignRepository,
)
from schemas.design_ir import topology_to_design_ir
from schemas.design_migrations import (
    design_ir_v2_to_v1_payload,
    migrate_design_ir_v1_to_v2,
)
from scripts.migrate_designs_v1_to_v2 import migrate_design_directory


def _v1_design() -> dict:
    return topology_to_design_ir(
        {
            "verilog": (
                "module c(input A, output GFP); assign GFP = A; endmodule"
            ),
            "cello_mode": "mock",
            "mapping_status": "unmapped",
        },
        host_organism="Escherichia coli",
        design_id="migration_test",
    ).to_dict()


def test_v1_to_v2_migration_layers_construct_context_and_assumptions() -> None:
    result = migrate_design_ir_v1_to_v2(_v1_design())
    design = result.design

    assert design.schema_version == "2.0"
    assert design.specification.outputs == ["GFP"]
    assert design.biological_context.host_organism.value == "Escherichia coli"
    assert design.biological_context.host_organism.status == "derived"
    assert design.constructs[0].part_instances[0].order == 1
    assert design.plasmids == []
    assert result.warnings
    assert design.validate() == []


def test_provenance_license_fields_survive_v1_v2_round_trip() -> None:
    payload = _v1_design()
    payload["provenance"][0].update(
        {
            "license_expression": "CC-BY-4.0",
            "rights_uri": "https://example.org/rights",
            "license_status": "attribution_required",
            "attribution_required": True,
            "permitted_uses": ["public_evidence_review"],
            "prohibited_uses": ["commercial_distribution"],
        }
    )

    migrated = migrate_design_ir_v1_to_v2(payload).design
    provenance = migrated.provenance[0]
    assert provenance.license_expression == "CC-BY-4.0"
    assert provenance.rights_uri == "https://example.org/rights"
    assert provenance.license_status == "attribution_required"
    assert provenance.attribution_required is True
    assert provenance.permitted_uses == ["public_evidence_review"]
    projected = design_ir_v2_to_v1_payload(migrated.to_dict())
    assert projected["provenance"][0]["license_expression"] == "CC-BY-4.0"
    assert projected["provenance"][0]["prohibited_uses"] == [
        "commercial_distribution"
    ]


def test_v2_to_v1_projection_preserves_existing_consumers() -> None:
    migrated = migrate_design_ir_v1_to_v2(_v1_design()).design
    projected = design_ir_v2_to_v1_payload(migrated.to_dict())

    assert projected["design_id"] == "migration_test"
    assert projected["logic_expression"] == "GFP = A"
    assert projected["constructs"][0]["parts"]
    assert projected["parts"][0]["host_compatibility"] == [
        "Escherichia coli"
    ]


def test_sqlite_repository_creates_revisions_and_is_idempotent(
    tmp_path: Path,
) -> None:
    repository = SqliteDesignRepository(tmp_path / "research.db")
    payload = migrate_design_ir_v1_to_v2(_v1_design()).design.to_dict()

    first = repository.save("migration_test", payload)
    duplicate = repository.save("migration_test", payload)
    changed = dict(payload)
    changed["name"] = "Updated name"
    second = repository.save("migration_test", changed)

    assert repository.schema_version == DATABASE_SCHEMA_VERSION
    assert first["revision"]["revision_number"] == 1
    assert duplicate["revision"]["revision_number"] == 1
    assert second["revision"]["revision_number"] == 2
    assert second["revision"]["parent_revision_id"].endswith("revision_1")
    assert len(repository.list_revisions("migration_test")) == 2
    assert repository.get_revision("migration_test", 1)["name"] != "Updated name"


def test_sqlite_repository_rejects_invalid_ids(tmp_path: Path) -> None:
    repository = SqliteDesignRepository(tmp_path / "research.db")

    with pytest.raises(RepositoryError):
        repository.get("../outside")


def test_application_services_store_v2_and_return_v1_compatibility(
    tmp_path: Path,
) -> None:
    services = create_application_services(tmp_path / "api_data")
    design = topology_to_design_ir(
        {
            "verilog": "module c(input A, output Y); assign Y = A; endmodule",
        },
        design_id="service_design",
    )

    persisted = services.designs.save(design)
    v2 = services.designs.get_v2("service_design")

    assert persisted.design_id == "service_design"
    assert services.designs.get("service_design").outputs == ["Y"]
    assert v2 is not None
    assert v2.schema_version == "2.0"
    assert services.designs.revisions("service_design")[0][
        "revision_number"
    ] == 1


def test_services_migrate_legacy_json_designs_once(tmp_path: Path) -> None:
    base_dir = tmp_path / "api_data"
    legacy = JsonRepository(base_dir / "designs")
    legacy.save("migration_test", _v1_design())

    first = create_application_services(base_dir)
    second = create_application_services(base_dir)

    assert first.designs.get_v2("migration_test") is not None
    assert len(second.designs.revisions("migration_test")) == 1


def test_batch_migration_supports_dry_run_and_repeat_execution(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "legacy"
    JsonRepository(source_dir).save("migration_test", _v1_design())
    database_path = tmp_path / "research.db"

    dry_run = migrate_design_directory(
        source_dir,
        database_path,
        dry_run=True,
    )
    assert dry_run["records"][0]["status"] == "would_migrate"
    assert not database_path.exists()

    migrated = migrate_design_directory(source_dir, database_path)
    repeated = migrate_design_directory(source_dir, database_path)

    assert migrated["migrated"] == 1
    assert repeated["skipped"] == 1


def test_run_store_writes_reproducible_manifest(tmp_path: Path) -> None:
    store = RunStore(base_dir=tmp_path / "runs", max_workers=1)
    response = store.start(
        lambda: {
            "status": "completed",
            "summary": {"score": 0.8},
            "artifacts": {},
        },
        {
            "user_intent": "Express GFP.",
            "model_name": "test-model",
            "api_key": "secret",
        },
        run_id="run_manifest_test",
    )
    future = store._futures["run_manifest_test"]
    future.result(timeout=5)

    status = store.status(response["run_id"])
    manifest_path = Path(status["run_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["request"]["api_key"] == "***"
    assert manifest["request_sha256"]
    assert manifest["result_sha256"]
    assert manifest["model"]["name"] == "test-model"
    assert status["artifacts"]["run_manifest_json"] == str(
        manifest_path.resolve()
    )


def test_api_exposes_v2_payload_and_revision_history(tmp_path: Path) -> None:
    services = create_application_services(tmp_path / "api_data")
    services.designs.save(
        topology_to_design_ir(
            {
                "verilog": (
                    "module c(input A, output Y); assign Y = A; endmodule"
                )
            },
            design_id="api_v2_design",
        )
    )
    app.dependency_overrides[get_services] = lambda: services
    try:
        with TestClient(app) as client:
            v2_response = client.get(
                "/api/v1/designs/api_v2_design/ir-v2"
            )
            revisions_response = client.get(
                "/api/v1/designs/api_v2_design/revisions"
            )
    finally:
        app.dependency_overrides.clear()

    assert v2_response.status_code == 200
    assert v2_response.json()["data"]["schema_version"] == "2.0"
    assert revisions_response.json()["data"]["count"] == 1
