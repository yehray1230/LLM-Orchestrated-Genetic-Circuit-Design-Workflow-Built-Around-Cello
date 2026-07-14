from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from src.scripts.verify_evidence_manifest import main


PUBLIC_MANIFEST = Path("docs/evidence/case_01/evidence_manifest.json")


def test_public_proof_gate_passes_and_summarizes_claims(capsys) -> None:
    exit_code = main([str(PUBLIC_MANIFEST)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Evidence Governance Public Proof Gate: PASS" in output
    assert "Evidence: 4 available / 6 total" in output
    assert "1 supported, 1 limited, 2 unsupported, 0 blocked" in output
    assert "experimentally_supported: unsupported" in output
    assert "does not mean every biological claim is supported" in output


def test_public_proof_gate_json_is_machine_readable(capsys) -> None:
    exit_code = main([str(PUBLIC_MANIFEST), "--json"])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert result["status"] == "pass"
    assert result["schema_version"] == "evidence-bom@1.0.0"
    assert result["overall_license_status"] == "attribution_required"
    assert {item["claim_id"]: item["status"] for item in result["claims"]} == {
        "computationally_consistent": "supported",
        "externally_mapped": "unsupported",
        "sequence_supported": "limited",
        "experimentally_supported": "unsupported",
    }


def test_public_proof_gate_fails_when_recorded_decision_is_tampered(
    tmp_path: Path,
    capsys,
) -> None:
    payload = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    tampered = deepcopy(payload)
    tampered["claim_decisions"][0]["status"] = "unsupported"
    path = tmp_path / "tampered_manifest.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    exit_code = main([str(path), "--json"])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["status"] == "fail"
    assert "Recorded claim decisions do not reproduce." in result["errors"]


def test_public_proof_gate_fails_for_missing_file(capsys) -> None:
    exit_code = main(["missing-evidence-manifest.json"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "Evidence Governance Public Proof Gate: FAIL" in output
    assert "Evidence manifest file was not found." in output


def test_public_proof_gate_reports_malformed_manifest_without_traceback(
    tmp_path: Path,
    capsys,
) -> None:
    path = tmp_path / "malformed_manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "evidence-bom@1.0.0",
                "subject": "not-an-object",
                "evidence": "not-a-list",
                "claim_evidence_links": [],
                "claim_decisions": ["not-an-object"],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main([str(path), "--json"])

    result = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert result["status"] == "fail"
    assert "evidence must be a list." in result["errors"]
