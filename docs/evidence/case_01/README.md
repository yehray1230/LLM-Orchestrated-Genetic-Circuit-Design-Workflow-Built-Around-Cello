# Case 01 Public Evidence Snapshot

This directory is the public, sanitized evidence index for the fixed
`A AND NOT B -> GFP` demonstration. It is intended to make the values quoted in
the demo report inspectable without committing local run directories or
workstation-specific paths.

The tracked [`evidence_manifest.json`](evidence_manifest.json) is the Case 01
Evidence Bill of Materials (E-BOM). It maps public claim IDs to source,
checksum, biological scope, availability, and license-policy decisions. The
project-authored evidence is licensed under Apache-2.0 and requires preservation
of the applicable license and attribution notices.

The active repository-level [license policy](../license_policy.json) permits
reuse of original project material with attribution. External tools, UCFs,
biological-part libraries, and datasets remain subject to their own terms; see
[`THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md).

## One-minute public proof gate

From the repository root, run:

```powershell
.\venv\Scripts\python.exe -m src.scripts.verify_evidence_manifest
```

Expected first line:

```text
Evidence Governance Public Proof Gate: PASS
```

The verifier does more than check JSON syntax. It reconstructs the evidence
records and claim links, recalculates every claim and license decision, and
checks the recorded summary. Any schema error, unknown evidence reference,
tampered decision, inconsistent summary, unreadable file, or invalid JSON
produces `FAIL` and a non-zero process exit code.

Use a specific manifest path or request machine-readable output when needed:

```powershell
.\venv\Scripts\python.exe -m src.scripts.verify_evidence_manifest docs/evidence/case_01/evidence_manifest.json --json
```

`PASS` means that the governance decisions reproduce from the recorded inputs.
It deliberately does **not** mean that every claim is supported or that the
candidate has been experimentally validated.

## Public claim decisions

| Claim | Decision | License decision | Reason | Safe interpretation |
| --- | --- | --- | --- | --- |
| `computationally_consistent` | `supported` | `attribution_required` | Available computational evidence reproduces the recorded result. | The fixed candidate is consistent under the recorded computational checks. |
| `externally_mapped` | `unsupported` | `unknown` | `REQUIRED_EVIDENCE_UNAVAILABLE` | No external Cello/UCF mapping evidence is present. |
| `sequence_supported` | `limited` | `attribution_required` | `EVIDENCE_NOT_ELIGIBLE_FOR_FULL_CLAIM` | Sequence checks exist, but they do not establish a buildable construct. |
| `experimentally_supported` | `unsupported` | `unknown` | `REQUIRED_EVIDENCE_UNAVAILABLE` | No wet-lab measurement is present; this is missing evidence, not a failed experiment. |

Current manifest summary: 6 evidence records, 4 available; 1 supported claim,
1 limited claim, 2 unsupported claims, and 0 blocked claims. The overall
license decision is `attribution_required` for the available project-authored
evidence.

## Claim boundary

This snapshot records deterministic computational screening results. It is not
external Cello mapping, experimental validation, a buildable plasmid, a primer
design, an oligo order, a PCR protocol, or evidence of in vivo function.

## Reproduce locally

From the repository root on the recorded source revision, run:

```powershell
.\venv\Scripts\python.exe -m src.scripts.generate_demo_baseline --timeout-seconds 60
```

The command writes the full local packet under `outputs/demo_baseline/`.
Because `outputs/` can contain workstation-specific paths and transient run
artifacts, it remains gitignored. Compare the generated files against
[`snapshot.json`](snapshot.json), which records the scientific identifiers,
reported results, limitations, and SHA-256 hashes from the captured run.

The packet hash is designed to be stable after masking known run-specific
identifiers. Individual file hashes may differ when absolute artifact paths or
other environment-specific metadata differ; inspect the reported configuration,
result, scoring, and packet hashes before treating two runs as equivalent.

## Interpretation

- `weighted_total_score = 0.85` and `grade = Excellent` are heuristic results
  under `research-v2-preview@1.9.0`, not calibrated probabilities.
- `research_smoke_v1@1.0.0` contains four synthetic infrastructure fixtures,
  not measured genetic circuits.
- `primer_ready` means that a non-experimental primer-planning gate found the
  abstract assembly representation structurally reviewable. No primer sequences
  were generated and `experimental_readiness_score` is null.
- The assembly method is `abstract_non_experimental_ordering`; no backbone or
  experimental assembly method was selected.
