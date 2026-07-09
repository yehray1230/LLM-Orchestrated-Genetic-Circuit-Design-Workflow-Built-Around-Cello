# Phase 7b Context: Governed Scientific Data Integration

This is the `@`-mentionable, non-sensitive context summary for the authoritative private plan at `local_plans_private/phase_7b_science_skills_integration_plan.md`.

## Decision

Integrate external scientific data through provider-neutral capabilities rather than depending directly on a named Codex or DeepMind skill. Providers may be runtime skills, APIs, local databases, cached records, or fixtures. The core workflow must remain deterministic and functional when none are available.

## Required Order

1. Phase 7b.0: capability contracts, provider status, provenance, cache boundary, and fixture tests.
2. Phase 7b.1: explicit-accession reference-sequence retrieval pilot, preferably with one NCBI provider.
3. Phase 7b.2: versioned JASPAR-style motif diagnostics, initially warning-only.
4. Phase 7b.3: traceable literature evidence retrieval without automatic parameter injection.
5. Phase 7b.4: context-aware parameter extraction and explicit promotion to local overrides.

Phase 6-lite, Phase 7-lite, and Phase 9-lite are prerequisites. Phase 8-lite guardrails are required before external sequences enter automated sequence repair or export paths.

## Capability Names

- `sequence_record_lookup`
- `motif_matrix_lookup`
- `binding_evidence_lookup`
- `literature_search`

## Guardrails

- Require explicit accession identifiers in the first sequence pilot; defer ambiguous gene-name resolution.
- Record provider, database version, query, retrieval time, stable record identifier, checksum, cache status, and warnings.
- Never fabricate a sequence when lookup fails.
- Verify that synonymous optimization preserves the declared protein sequence.
- Treat PWM hits as potential sequence-level matches, not proof of in-vivo binding or crosstalk.
- Keep experimental binding evidence separate from motif-model evidence.
- Literature values remain candidates until organism, strain, conditions, method, units, and compatibility are reviewed.
- Never silently replace canonical defaults with mined values.

## Reproducibility

Use fixed fixture tests, recorded adapter-contract tests, and separate opt-in live smoke tests. Benchmarks must pin record versions and response identity; live latest-version queries are not deterministic benchmark inputs.

## Synchronization Rule

The private plan is authoritative. When its stable decisions change, update this context file in the same task. Private notes, credentials, unpublished data, tentative cost details, and raw experiment results must not be copied here.
