from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from application.demo_baseline import make_reproducible_packet
from application.case01_evidence import _stable_benchmark_evidence_hash
from schemas.evidence_governance import (
    ClaimEvidenceLink,
    EvidenceRecord,
    build_evidence_manifest,
    evaluate_claim,
    evaluate_license_decision,
    validate_evidence_manifest,
)


def _evidence(**overrides: object) -> EvidenceRecord:
    values: dict[str, object] = {
        "evidence_id": "evidence_1",
        "evidence_type": "computational",
        "license_expression": "MIT",
        "license_status": "allowed",
        "permitted_uses": ["public_evidence_review"],
    }
    values.update(overrides)
    return EvidenceRecord(**values)


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (_evidence(), "allowed"),
        (
            _evidence(
                license_expression="CC-BY-4.0",
                license_status="attribution_required",
                attribution_required=True,
            ),
            "attribution_required",
        ),
        (
            _evidence(
                license_expression=None,
                license_status="unknown",
                permitted_uses=[],
            ),
            "review_required",
        ),
        (
            _evidence(
                license_status="blocked",
                prohibited_uses=["public_evidence_review"],
            ),
            "blocked",
        ),
    ],
)
def test_license_decision_covers_four_governance_states(
    record: EvidenceRecord,
    expected: str,
) -> None:
    decision = evaluate_license_decision(
        [record],
        intended_use="public_evidence_review",
    )

    assert decision.status == expected


def test_claim_is_limited_when_evidence_rights_require_review() -> None:
    record = _evidence(
        license_expression="LicenseRef-project-license-not-yet-declared",
        license_status="review_required",
        permitted_uses=["internal_evaluation"],
    )
    decision = evaluate_claim(
        ClaimEvidenceLink(
            claim_id="computationally_consistent",
            evidence_ids=[record.evidence_id],
        ),
        [record],
        intended_use="public_evidence_review",
    )

    assert decision.status == "limited"
    assert decision.license_decision.status == "review_required"
    assert "EVIDENCE_RIGHTS_REQUIRE_REVIEW" in decision.reason_codes


def test_claim_is_unsupported_when_required_evidence_is_missing() -> None:
    record = _evidence(
        evidence_id="experimental",
        evidence_type="experimental_measurement",
        license_expression=None,
        license_status="unknown",
        availability="missing",
    )
    decision = evaluate_claim(
        ClaimEvidenceLink(
            claim_id="experimentally_supported",
            evidence_ids=[record.evidence_id],
        ),
        [record],
        intended_use="public_evidence_review",
    )

    assert decision.status == "unsupported"
    assert decision.reason_codes == ["REQUIRED_EVIDENCE_UNAVAILABLE"]


def test_reproducible_packet_masks_manifest_generation_time() -> None:
    first = {"evidence_manifest": {"generated_at": "2026-07-14T01:00:00+00:00"}}
    second = {"evidence_manifest": {"generated_at": "2026-07-14T02:00:00+00:00"}}

    assert make_reproducible_packet(first) == make_reproducible_packet(second)


def test_case01_benchmark_evidence_hash_ignores_transient_result_hash() -> None:
    benchmark = {
        "dataset_id": "research_smoke_v1",
        "dataset_version": "1.0.0",
        "dataset_license": "Apache-2.0",
        "profile_id": "research-v1.8",
        "scoring_version": "1.8.0",
        "case_count": 4,
        "passed_count": 4,
        "failed_count": 0,
        "pass_rate": 1.0,
        "mean_score": 0.716625,
        "result_hash": "run-specific-hash-a",
    }
    changed_run = {**benchmark, "result_hash": "run-specific-hash-b"}

    assert _stable_benchmark_evidence_hash(benchmark) == (
        _stable_benchmark_evidence_hash(changed_run)
    )


def test_manifest_is_machine_validatable() -> None:
    record = _evidence()
    manifest = build_evidence_manifest(
        subject={"identifier": "case_01"},
        claim_boundary="Computational evidence only.",
        evidence_records=[record],
        claim_links=[
            ClaimEvidenceLink(
                claim_id="computationally_consistent",
                evidence_ids=[record.evidence_id],
            )
        ],
        intended_use="public_evidence_review",
    )

    assert validate_evidence_manifest(manifest) == []
    assert manifest["claim_decisions"][0]["status"] == "supported"
    assert manifest["summary"]["supported_claim_count"] == 1


def test_apache_license_activation_separates_optional_gpl_dependency() -> None:
    license_text = Path("LICENSE").read_text(encoding="utf-8")
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    base_requirements = Path("requirements.txt").read_text(encoding="utf-8")
    optional_requirements = Path("requirements-optional.txt").read_text(
        encoding="utf-8"
    )
    notices = Path("THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "Apache License" in license_text
    assert metadata["project"]["license"]["text"] == "Apache-2.0"
    assert "LICENSE" in metadata["tool"]["setuptools"]["license-files"]
    assert "NOTICE" in metadata["tool"]["setuptools"]["license-files"]
    assert "THIRD_PARTY_NOTICES.md" in metadata["tool"]["setuptools"]["license-files"]
    assert "primer3-py" not in base_requirements
    assert "primer3-py>=2.3" in optional_requirements
    assert "GPL-2.0" in notices
    assert "not vendored" in notices


def test_license_policy_activates_apache_with_third_party_boundaries() -> None:
    path = Path("docs/evidence/license_policy.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "evidence-license-policy@1.0.0"
    assert payload["status"] == "active"
    assert payload["selected_license_expression"] == "Apache-2.0"
    assert payload["public_reuse_gate"] == "go_with_attribution"
    assert {item["license_status"] for item in payload["project_materials"]} == {
        "attribution_required"
    }
    assert payload["decision_options"][0]["license_expression"] == "Apache-2.0"
    assert payload["decision_options"][0]["recommendation"] == "selected"
    assert all(
        item["bundled_or_ingested"] is False for item in payload["external_sources"]
    )

    primer3_policy = next(
        item
        for item in payload["external_sources"]
        if item["source_id"] == "primer3_py"
    )
    assert primer3_policy["decision"] == "optional_dependency_separate_from_apache_base"


def test_tracked_case01_manifest_is_valid_and_conservative() -> None:
    path = Path("docs/evidence/case_01/evidence_manifest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert validate_evidence_manifest(payload) == []
    decisions = {
        item["claim_id"]: item["status"] for item in payload["claim_decisions"]
    }
    assert decisions == {
        "computationally_consistent": "supported",
        "externally_mapped": "unsupported",
        "sequence_supported": "limited",
        "experimentally_supported": "unsupported",
    }
    assert payload["overall_license_decision"]["status"] == "attribution_required"
    available = [
        item for item in payload["evidence"] if item["availability"] == "available"
    ]
    assert {item["license_expression"] for item in available} == {"Apache-2.0"}
    assert all(item["attribution_required"] is True for item in available)
