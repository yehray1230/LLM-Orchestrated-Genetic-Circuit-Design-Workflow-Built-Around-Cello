# Evidence Governance and Evidence BOM Specification

Status: MVP contract
Schema: `evidence-bom@1.0.0`

## Purpose

This specification defines how the project records evidence provenance, usage
rights, biological scope, and claim eligibility. Its goal is to make every
public claim traceable to named evidence while preventing missing, restricted,
or context-mismatched evidence from silently supporting a stronger claim.

The Evidence Bill of Materials (E-BOM) is a machine-readable companion to a
design or public evidence snapshot. It does not replace SBOL, provenance
standards, repository licensing, or legal review.

## Core records

Each `EvidenceRecord` has a stable `evidence_id`, type, source and version
identifiers, optional content hash, license and rights fields, biological
context, method, scope, availability, notes, and metadata.

Minimum governance fields are:

- `license_expression`: SPDX expression or a documented `LicenseRef-*`.
- `rights_uri`: source-specific rights or terms URL when available.
- `license_status`: `allowed`, `attribution_required`,
  `review_required`, `blocked`, or `unknown`.
- `permitted_uses` and `prohibited_uses`: explicit project policy inputs.
- `availability`: `available`, `missing`, or `inapplicable`.
- `biological_context`, `method`, and `scope`: boundaries needed to judge
  whether the evidence is relevant to a biological claim.

A `ClaimEvidenceLink` maps a stable claim ID to evidence IDs and records
whether that evidence supports, refutes, derives from, or is not applicable to
the claim.

## Deterministic license gate

For a named intended use, the MVP evaluator applies the following precedence:

| Condition | Decision |
| --- | --- |
| Any record blocks the use or lists it as prohibited | `blocked` |
| License is missing/unknown, requires review, or the use is outside a non-empty allow-list | `review_required` |
| At least one otherwise usable record requires attribution | `attribution_required` |
| All available records explicitly permit the use | `allowed` |
| No available evidence records were supplied | `unknown` |

This is a policy gate, not an automated legal opinion. `review_required` is
the safe state whenever the repository or source rights are not explicit.

## Deterministic claim gate

Claims resolve to one of four states:

| Condition | Claim decision |
| --- | --- |
| Required evidence is absent or unavailable | `unsupported` |
| Available evidence refutes the claim or its use is blocked | `blocked` |
| Rights require review or evidence is marked ineligible for a full claim | `limited` |
| Required evidence is available, permitted, and claim-eligible | `supported` |

A claim decision contains the evidence IDs, the nested license decision, and
machine-readable reason codes. Missing experimental evidence therefore produces
`unsupported`; it never counts as evidence that an experiment failed.

## Case 01 contract

The tracked `A AND NOT B -> GFP` snapshot uses intended use
`public_evidence_review`. Original project material is Apache-2.0 and its
license decision is `attribution_required`.

Expected decisions are:

- `computationally_consistent`: `supported` because computational evidence
  is present and the Apache-2.0 attribution requirement is explicit.
- `externally_mapped`: `unsupported` because no Cello mapping was produced.
- `sequence_supported`: `limited` because illustrative sequence checks are
  not empirical part characterization.
- `experimentally_supported`: `unsupported` because no wet-lab measurements
  are included.

## Standards alignment

The MVP uses concepts compatible with:

- SBOL 3 and W3C PROV-O for identity, derivation, and activity provenance.
- SPDX expressions and `LicenseRef-*` identifiers for license declarations.
- DataCite and RO-Crate concepts for persistent identifiers, creators, files,
  checksums, and research-object packaging.

This release does not claim full conformance with those standards. A later
adapter may export the E-BOM into their native representations without changing
the claim-gating contract.

## Repository license policy

The current machine-readable policy is tracked at
[`docs/evidence/license_policy.json`](evidence/license_policy.json), with the
owner-facing rationale and activation gate in
[`docs/evidence/licensing_decision.md`](evidence/licensing_decision.md).
Its active Apache-2.0 policy permits reuse with attribution. Third-party
software, UCFs, part libraries, and datasets retain separate source-level gates.

## Non-goals

The MVP does not interpret third-party terms, certify biological validity,
infer wet-lab reproducibility, or authorize an experimental protocol. Human
review remains mandatory for unresolved rights and for claims beyond the
recorded computational boundary.

## Acceptance criteria

An implementation conforms to this MVP when:

1. Old Design IR provenance records still load with conservative defaults.
2. The four license outcomes are covered by automated tests.
3. Missing required evidence cannot yield a supported claim.
4. A manifest has unique evidence IDs and only references known IDs.
5. Case 01 ships a valid tracked manifest with the expected conservative
   decisions.
6. Demo packet hashing masks manifest generation timestamps.
7. The public proof command rebuilds claim, license, and summary decisions from
   manifest inputs and exits non-zero for invalid or inconsistent evidence.
