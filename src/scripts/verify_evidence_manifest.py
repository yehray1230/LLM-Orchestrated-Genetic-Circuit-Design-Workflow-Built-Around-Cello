from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from schemas.evidence_governance import verify_evidence_manifest  # noqa: E402


DEFAULT_MANIFEST = Path("docs/evidence/case_01/evidence_manifest.json")


def _proof_result(
    manifest_path: Path,
    payload: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, Any]:
    if payload is None:
        return {
            "proof_gate": "evidence-governance-public-proof@1.0.0",
            "status": "fail",
            "manifest": str(manifest_path),
            "errors": errors,
        }

    raw_summary = payload.get("summary")
    summary = raw_summary if isinstance(raw_summary, dict) else {}
    raw_subject = payload.get("subject")
    subject = raw_subject if isinstance(raw_subject, dict) else {}
    raw_overall_license = payload.get("overall_license_decision")
    overall_license = (
        raw_overall_license if isinstance(raw_overall_license, dict) else {}
    )
    claims = []
    raw_decisions = payload.get("claim_decisions")
    decisions = raw_decisions if isinstance(raw_decisions, list) else []
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        raw_license_decision = decision.get("license_decision")
        license_decision = (
            raw_license_decision if isinstance(raw_license_decision, dict) else {}
        )
        claims.append(
            {
                "claim_id": decision.get("claim_id"),
                "status": decision.get("status"),
                "license_status": license_decision.get("status", "unknown"),
                "reason_codes": decision.get("reason_codes") or [],
            }
        )
    return {
        "proof_gate": "evidence-governance-public-proof@1.0.0",
        "status": "pass" if not errors else "fail",
        "manifest": str(manifest_path),
        "schema_version": payload.get("schema_version"),
        "subject": subject.get("identifier"),
        "intended_use": payload.get("intended_use"),
        "evidence_count": summary.get("evidence_count"),
        "available_evidence_count": summary.get("available_evidence_count"),
        "overall_license_status": overall_license.get("status"),
        "claim_counts": {
            "supported": summary.get("supported_claim_count"),
            "limited": summary.get("limited_claim_count"),
            "unsupported": summary.get("unsupported_claim_count"),
            "blocked": summary.get("blocked_claim_count"),
        },
        "claims": claims,
        "claim_boundary": payload.get("claim_boundary"),
        "errors": errors,
    }


def _render_human(result: dict[str, Any]) -> str:
    status = str(result["status"]).upper()
    lines = [
        f"Evidence Governance Public Proof Gate: {status}",
        f"Manifest: {result['manifest']}",
    ]
    if status == "FAIL":
        lines.append("Errors:")
        lines.extend(f"  - {error}" for error in result.get("errors") or [])
        return "\n".join(lines)

    counts = result["claim_counts"]
    lines.extend(
        [
            f"Schema: {result['schema_version']}",
            f"Subject: {result['subject']}",
            (
                "Evidence: "
                f"{result['available_evidence_count']} available / "
                f"{result['evidence_count']} total"
            ),
            (
                "Claims: "
                f"{counts['supported']} supported, "
                f"{counts['limited']} limited, "
                f"{counts['unsupported']} unsupported, "
                f"{counts['blocked']} blocked"
            ),
            f"Overall license decision: {result['overall_license_status']}",
            "Claim decisions:",
        ]
    )
    for claim in result["claims"]:
        reasons = ", ".join(claim["reason_codes"]) or "none"
        lines.append(
            f"  - {claim['claim_id']}: {claim['status']} "
            f"(license={claim['license_status']}; reasons={reasons})"
        )
    lines.extend(
        [
            f"Claim boundary: {result['claim_boundary']}",
            (
                "PASS verifies that the recorded decisions reproduce from the "
                "manifest inputs; it does not mean every biological claim is supported."
            ),
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify an Evidence BOM and reproduce its claim, license, and summary "
            "decisions."
        )
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Evidence manifest path (default: {DEFAULT_MANIFEST}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable proof-gate result.",
    )
    args = parser.parse_args(argv)

    payload: dict[str, Any] | None = None
    errors: list[str] = []
    try:
        loaded = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            errors.append("Evidence manifest root must be a JSON object.")
        else:
            payload = loaded
            errors.extend(verify_evidence_manifest(payload))
    except FileNotFoundError:
        errors.append("Evidence manifest file was not found.")
    except json.JSONDecodeError as exc:
        errors.append(f"Evidence manifest is not valid JSON: {exc.msg}.")
    except OSError as exc:
        errors.append(f"Evidence manifest could not be read: {exc}.")

    result = _proof_result(args.manifest, payload, errors)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(_render_human(result))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
