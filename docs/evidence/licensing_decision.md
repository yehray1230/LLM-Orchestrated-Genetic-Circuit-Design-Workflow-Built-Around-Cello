# Evidence Licensing Decision Record

Status: Apache-2.0 activated
Reviewed: 2026-07-14

## Accepted decision

The repository owner selected Apache-2.0 for original project code,
documentation, synthetic fixtures, and generated evidence. Redistribution is
allowed when the Apache license and applicable attribution notices are
preserved. Third-party materials keep their own licenses.

## Audited inventory

| Material | Current finding | E-BOM treatment |
| --- | --- | --- |
| Repository source code | Root Apache-2.0 license | `attribution_required` |
| Project documentation | Covered by root Apache-2.0 license | `attribution_required` |
| EXP-003 task set | Synthetic fixture metadata migrated to Apache-2.0 | `attribution_required` |
| `research_smoke_v1` dataset | Synthetic fixture metadata migrated to Apache-2.0 | `attribution_required` |
| Case 01 generated outputs | Project-generated Apache-2.0 evidence | `attribution_required` |
| External Cello mapping | Not present in Case 01 | `unsupported`; no Cello rights are inherited |
| Wet-lab measurements | Not present in Case 01 | `unsupported` |


## External-tool boundary

The project wraps or can call Cello, but Case 01 does not contain an external
Cello run, Cello source code, or UCF data.

- The CIDARLAB Cello repository reports BSD-2-Clause:
  https://github.com/CIDARLAB/cello
- The Cello 2.0 protocol publication describes its referenced source code as
  MIT-licensed:
  https://www.nature.com/articles/s41596-021-00675-2

These findings are version-specific and must not be collapsed into one generic
"Cello license." A future external run must record the exact tool repository,
revision, UCF source, and license/rights URI. UCF and biological-part data may
have terms different from the compiler itself.

## Selected license

For this research-preview software repository, the selected license is
`Apache-2.0` because it is permissive and includes an explicit patent grant
and contribution terms. It also keeps downstream academic and commercial use
possible while requiring preservation of notices.

The simpler alternative is `MIT`. It is shorter and widely recognized, but
does not contain the same explicit patent-license language.

This recommendation is operational guidance, not legal advice. Before
activation, confirm that all committed material is owned by the repository
owner or is separately identified as third-party content.

## Activation record

The activation sequence is:

1. Add the canonical Apache-2.0 text as the root `LICENSE` file.
2. Add `license = { text = "Apache-2.0" }` to `pyproject.toml`.
3. Replace fixture metadata `project-fixture` with `Apache-2.0`.
4. Change project-authored evidence from `review_required` to
   `attribution_required` when notice preservation applies.
5. Add a `THIRD_PARTY_NOTICES.md` entry before distributing bundled external
   code, UCFs, part libraries, or datasets.
6. Regenerate Case 01 so its task-set hash, packet hash, and E-BOM all reflect
   the activated policy.
7. Run the governance tests and full regression suite.

## Go/no-go gate

Public reuse of original project materials is **GO WITH ATTRIBUTION** under
Apache-2.0. Bundled third-party packages, external tools, UCFs, part libraries,
and datasets remain separately gated by `THIRD_PARTY_NOTICES.md` and their
source-specific terms.
