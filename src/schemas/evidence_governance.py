from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


EVIDENCE_BOM_SCHEMA_VERSION = "evidence-bom@1.0.0"
LICENSE_DECISION_STATUSES = {
    "allowed",
    "attribution_required",
    "review_required",
    "blocked",
    "unknown",
}
EVIDENCE_AVAILABILITY_STATUSES = {"available", "missing", "inapplicable"}
CLAIM_DECISION_STATUSES = {"supported", "limited", "unsupported", "blocked"}
CLAIM_RELATIONSHIPS = {"supports", "refutes", "derived_from", "not_applicable"}


@dataclass
class EvidenceRecord:
    evidence_id: str
    evidence_type: str
    source_uri: str | None = None
    source_version: str | None = None
    content_hash: str | None = None
    license_expression: str | None = None
    rights_uri: str | None = None
    license_status: str = "unknown"
    attribution_required: bool = False
    permitted_uses: list[str] = field(default_factory=list)
    prohibited_uses: list[str] = field(default_factory=list)
    biological_context: dict[str, Any] = field(default_factory=dict)
    method: str | None = None
    scope: str | None = None
    availability: str = "available"
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimEvidenceLink:
    claim_id: str
    evidence_ids: list[str]
    relationship: str = "supports"
    required: bool = True
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LicenseDecision:
    status: str
    intended_use: str
    evidence_ids: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    attribution_evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimDecision:
    claim_id: str
    status: str
    evidence_ids: list[str]
    license_decision: LicenseDecision
    reason_codes: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_license_decision(
    evidence_records: Iterable[EvidenceRecord],
    *,
    intended_use: str,
) -> LicenseDecision:
    records = list(evidence_records)
    evidence_ids = [record.evidence_id for record in records]
    if not records:
        return LicenseDecision(
            status="unknown",
            intended_use=intended_use,
            reason_codes=["NO_EVIDENCE_RECORDS"],
        )

    blocked = [
        record
        for record in records
        if record.license_status == "blocked" or intended_use in record.prohibited_uses
    ]
    if blocked:
        return LicenseDecision(
            status="blocked",
            intended_use=intended_use,
            evidence_ids=evidence_ids,
            reason_codes=["LICENSE_OR_POLICY_PROHIBITS_USE"],
        )

    unresolved = [
        record
        for record in records
        if record.license_status in {"unknown", "review_required"}
        or not record.license_expression
        or (record.permitted_uses and intended_use not in record.permitted_uses)
    ]
    if unresolved:
        return LicenseDecision(
            status="review_required",
            intended_use=intended_use,
            evidence_ids=evidence_ids,
            reason_codes=["LICENSE_OR_RIGHTS_UNRESOLVED"],
        )

    attribution = [
        record.evidence_id
        for record in records
        if record.attribution_required
        or record.license_status == "attribution_required"
    ]
    if attribution:
        return LicenseDecision(
            status="attribution_required",
            intended_use=intended_use,
            evidence_ids=evidence_ids,
            reason_codes=["ATTRIBUTION_MUST_BE_PRESERVED"],
            attribution_evidence_ids=attribution,
        )

    return LicenseDecision(
        status="allowed",
        intended_use=intended_use,
        evidence_ids=evidence_ids,
    )


def evaluate_claim(
    link: ClaimEvidenceLink,
    evidence_records: Iterable[EvidenceRecord],
    *,
    intended_use: str,
) -> ClaimDecision:
    by_id = {record.evidence_id: record for record in evidence_records}
    selected = [
        by_id[evidence_id] for evidence_id in link.evidence_ids if evidence_id in by_id
    ]
    available = [record for record in selected if record.availability == "available"]
    license_decision = evaluate_license_decision(available, intended_use=intended_use)
    reasons: list[str] = []

    if link.relationship == "refutes" and available:
        return ClaimDecision(
            claim_id=link.claim_id,
            status="blocked",
            evidence_ids=[record.evidence_id for record in available],
            license_decision=license_decision,
            reason_codes=["AVAILABLE_EVIDENCE_REFUTES_CLAIM"],
            note=link.note,
        )

    missing_ids = [
        evidence_id for evidence_id in link.evidence_ids if evidence_id not in by_id
    ]
    unavailable_ids = [
        record.evidence_id for record in selected if record.availability != "available"
    ]
    if link.required and (missing_ids or unavailable_ids or not available):
        reasons.append("REQUIRED_EVIDENCE_UNAVAILABLE")
        return ClaimDecision(
            claim_id=link.claim_id,
            status="unsupported",
            evidence_ids=[record.evidence_id for record in selected],
            license_decision=license_decision,
            reason_codes=reasons,
            note=link.note,
        )

    if license_decision.status == "blocked":
        reasons.append("EVIDENCE_USE_BLOCKED")
        status = "blocked"
    elif license_decision.status in {"review_required", "unknown"}:
        reasons.append("EVIDENCE_RIGHTS_REQUIRE_REVIEW")
        status = "limited"
    elif any(record.metadata.get("claim_eligible") is False for record in available):
        reasons.append("EVIDENCE_NOT_ELIGIBLE_FOR_FULL_CLAIM")
        status = "limited"
    else:
        status = "supported"

    return ClaimDecision(
        claim_id=link.claim_id,
        status=status,
        evidence_ids=[record.evidence_id for record in available],
        license_decision=license_decision,
        reason_codes=reasons,
        note=link.note,
    )


def build_evidence_manifest(
    *,
    subject: dict[str, Any],
    claim_boundary: str,
    evidence_records: Iterable[EvidenceRecord],
    claim_links: Iterable[ClaimEvidenceLink],
    intended_use: str = "public_research_distribution",
    generated_at: str | None = None,
) -> dict[str, Any]:
    records = list(evidence_records)
    links = list(claim_links)
    decisions = [
        evaluate_claim(link, records, intended_use=intended_use) for link in links
    ]
    overall_license = evaluate_license_decision(
        [record for record in records if record.availability == "available"],
        intended_use=intended_use,
    )
    return {
        "schema_version": EVIDENCE_BOM_SCHEMA_VERSION,
        "generated_at": generated_at,
        "subject": subject,
        "intended_use": intended_use,
        "claim_boundary": claim_boundary,
        "evidence": [record.to_dict() for record in records],
        "claim_evidence_links": [link.to_dict() for link in links],
        "claim_decisions": [decision.to_dict() for decision in decisions],
        "overall_license_decision": overall_license.to_dict(),
        "summary": {
            "evidence_count": len(records),
            "available_evidence_count": sum(
                record.availability == "available" for record in records
            ),
            "supported_claim_count": sum(
                decision.status == "supported" for decision in decisions
            ),
            "limited_claim_count": sum(
                decision.status == "limited" for decision in decisions
            ),
            "unsupported_claim_count": sum(
                decision.status == "unsupported" for decision in decisions
            ),
            "blocked_claim_count": sum(
                decision.status == "blocked" for decision in decisions
            ),
        },
    }


def validate_evidence_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != EVIDENCE_BOM_SCHEMA_VERSION:
        errors.append("Unsupported evidence manifest schema version.")
    records = payload.get("evidence")
    links = payload.get("claim_evidence_links")
    decisions = payload.get("claim_decisions")
    if not isinstance(records, list):
        return errors + ["evidence must be a list."]
    if not isinstance(links, list):
        return errors + ["claim_evidence_links must be a list."]
    if not isinstance(decisions, list):
        return errors + ["claim_decisions must be a list."]

    evidence_ids = [
        str(item.get("evidence_id") or "") for item in records if isinstance(item, dict)
    ]
    if any(not evidence_id for evidence_id in evidence_ids):
        errors.append("Every evidence record requires an evidence_id.")
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("Evidence IDs must be unique.")

    known_ids = set(evidence_ids)
    for item in records:
        if not isinstance(item, dict):
            errors.append("Every evidence record must be an object.")
            continue
        if item.get("license_status") not in LICENSE_DECISION_STATUSES:
            errors.append(
                f"Invalid license status for evidence {item.get('evidence_id')}."
            )
        if item.get("availability") not in EVIDENCE_AVAILABILITY_STATUSES:
            errors.append(
                f"Invalid availability for evidence {item.get('evidence_id')}."
            )
    for link in links:
        if not isinstance(link, dict):
            errors.append("Every claim-evidence link must be an object.")
            continue
        if link.get("relationship") not in CLAIM_RELATIONSHIPS:
            errors.append(f"Invalid relationship for claim {link.get('claim_id')}.")
        for evidence_id in link.get("evidence_ids") or []:
            if evidence_id not in known_ids:
                errors.append(
                    f"Claim {link.get('claim_id')} references unknown evidence {evidence_id}."
                )
    for decision in decisions:
        if not isinstance(decision, dict):
            errors.append("Every claim decision must be an object.")
            continue
        if decision.get("status") not in CLAIM_DECISION_STATUSES:
            errors.append(f"Invalid claim decision for {decision.get('claim_id')}.")
    return errors


def verify_evidence_manifest(payload: dict[str, Any]) -> list[str]:
    """Verify that recorded governance decisions reproduce from their inputs."""

    errors = validate_evidence_manifest(payload)
    if errors:
        return errors

    try:
        records = [EvidenceRecord(**item) for item in payload["evidence"]]
        links = [
            ClaimEvidenceLink(**item) for item in payload["claim_evidence_links"]
        ]
        rebuilt = build_evidence_manifest(
            subject=payload.get("subject") or {},
            claim_boundary=str(payload.get("claim_boundary") or ""),
            evidence_records=records,
            claim_links=links,
            intended_use=str(
                payload.get("intended_use") or "public_research_distribution"
            ),
            generated_at=payload.get("generated_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        return [f"Evidence manifest cannot be deterministically rebuilt: {exc}"]

    comparisons = (
        ("claim_decisions", "Recorded claim decisions do not reproduce."),
        (
            "overall_license_decision",
            "Recorded overall license decision does not reproduce.",
        ),
        ("summary", "Recorded evidence summary does not reproduce."),
    )
    for field_name, message in comparisons:
        if payload.get(field_name) != rebuilt[field_name]:
            errors.append(message)
    return errors
