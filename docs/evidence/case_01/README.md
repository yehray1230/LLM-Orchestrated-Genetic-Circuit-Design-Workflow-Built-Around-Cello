# Case 01 Public Evidence Snapshot

This directory is the public, sanitized evidence index for the fixed
`A AND NOT B -> GFP` demonstration. It is intended to make the values quoted in
the demo report inspectable without committing local run directories or
workstation-specific paths.

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
