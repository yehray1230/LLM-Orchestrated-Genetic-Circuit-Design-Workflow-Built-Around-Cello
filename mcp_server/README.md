# MCP Prototype

This folder is an additive MCP adapter for the existing genetic circuit workflow.
It does not replace or modify the Streamlit UI.

## Tools

- `design_genetic_circuit_quick`: runs a compact Builder -> Translator -> Cello -> ODE -> Critic workflow.
- `start_design_run`: starts a longer background design run and returns `run_id`.
- `get_design_run_status`: polls a background run.
- `get_design_run_events`: returns append-only stage events after an optional event cursor.
- `get_design_run_progress`: returns the current stage, progress fraction, and event count.
- `get_design_run_result`: returns a finished background run result.
- `list_design_runs`: lists recent background runs, newest first.
- `cancel_design_run`: requests best-effort cancellation for a queued or running run.
- `get_design_run_artifacts`: returns artifact paths and the run manifest when available.
- `compare_design_runs`: ranks completed runs by score and reports metric differences.
- `diagnose_design_run`: produces deterministic findings and next actions for one run.
- `explain_design_run`: returns selectable score, caveat, and decision-rationale explanations for one run.
- `submit_design_feedback`: stores human constraints and a repair, exploitation, or fallback decision.
- `resume_design_run`: creates a child run from a paused state and submitted guidance.
- `get_design_ir`: materializes or reads the canonical DesignIR for a run revision.
- `list_compatible_replacements`: lists compatible parts from a versioned part library.
- `validate_design_part_replacement`: validates a proposed replacement without changing the design.
- `replace_design_part`: creates an immutable DesignIR revision.
- `compare_design_revisions`: reports part, construct, validation, and metric differences.
- `export_design`: writes BOM CSV, GenBank, and/or SBOL3 artifacts for a revision.
- `evaluate_cello_verilog`: evaluates existing Cello-compatible Verilog without calling an LLM.
- `summarize_mcp_design_state`: compresses a saved state JSON into an Agent-friendly summary.

## Runtime Configuration

The adapter reads model settings from arguments or environment variables:

```powershell
$env:OPENAI_API_KEY="..."
$env:LITELLM_MODEL="gpt-5.4-mini"
python -m mcp_server.server
```

Passing `api_key` as a tool argument is still supported for backward compatibility, but
environment variables are preferred so secrets do not appear in client-side tool traces.
Background run metadata redacts the `api_key` field before writing request details.

The `mcp` Python package is optional for local tests, but required to run the MCP server:

```powershell
pip install mcp
```

## Artifacts

Each run writes files under `outputs/mcp_runs` by default:

- `state.json`
- `summary.json`
- `best_topology.json`
- `best_design.v`
- `run_summary.md`
- `manifest.json`
- `score_breakdown.png`
- `ode_summary.png` when ODE metrics are available
- explanation artifacts when `explain_design_run(write_artifacts=True)` is used:
  - `score_explanation.json`
  - `decision_trace.json`
  - `ode_explanation.json`
  - `explanation_summary.md`
  - `design_rationale.md`

The manifest records each artifact key, path, type, and short description so MCP clients
can inspect outputs without guessing file names.

Background runs also persist `events.jsonl` under their async run directory. Each event
contains `event_id`, `stage`, `status`, `progress`, `message`, `details`, and `timestamp`.
Clients can use `after_event_id` as a cursor instead of repeatedly loading the full history.

Paused runs are immutable. `submit_design_feedback` writes guidance to the parent run and
`resume_design_run` creates a new child run. This preserves the original result and provides
an auditable parent/child execution history.

Design revisions are stored under the workflow artifact directory in `design_revisions/`.
Exports are stored by revision under `design_revisions/exports/<revision_id>/`.

## Response Shape

Tools keep their existing fields and also include a common error envelope:

- Success responses include `error: null` and `error_type: null`.
- Validation and runtime failures include `status`, `error`, `error_type`, `summary`, and `artifacts`.
- Common `error_type` values are `validation_error`, `dependency_error`,
  `workflow_error`, `external_tool_error`, `not_found`, and `cancelled`.

`compare_design_runs` and `diagnose_design_run` are read-only analysis tools. They use
persisted run results and artifact metadata; they do not call an LLM or rerun the workflow.

`explain_design_run` is also read-only with respect to workflow execution. It can write
explanation artifacts next to the run outputs, but it does not rerun Builder, Translator,
Cello, ODE, or Critic stages. Use it when a client needs selective explanation without
loading the full `state.json`.

Supported explanation profiles:

- `brief`: concise headline, key caveats, and next actions.
- `review`: score explanation, decision trace, biological caveats, ODE explanation, next actions, and artifacts.
- `debug`: decision trace, failed branches, next actions, and artifacts.
- `full`: all supported explanation sections.

Supported explanation sections:

- `score`
- `decision_trace`
- `biological_caveats`
- `ode_explanation`
- `failed_branches`
- `next_actions`
- `artifacts`

Long explanation content is persisted as artifacts when `write_artifacts` is true:

- `score_explanation.json`
- `decision_trace.json`
- `ode_explanation.json`
- `explanation_summary.md`
- `design_rationale.md`

The `ode_explanation` section is derived from the stored `ode_trace` when available.
It reports selected trajectory readouts, coarse burden readouts, uncertainty metadata,
coverage warnings, model limitations, and suggested next checks. These values are
screening aids and should not be treated as calibrated expression measurements.

Cello outputs include provenance fields when available:

- `cello_mode`: for example `mock` or `external`.
- `cello_claim_level`: for example `mock_only`, `externally_mapped`, or `external_mapping_failed`.
- `cello_warning`: a human-readable claim-boundary warning.

MCP clients should preserve these fields when summarizing results so mock/demo Cello
outputs are not confused with real part assignment.

## Testing

Install development dependencies before running tests:

```powershell
pip install -r requirements-dev.txt
```

Run MCP-focused tests:

```powershell
.\scripts\test-mcp.ps1
```

Run the full test suite:

```powershell
.\scripts\test-mcp.ps1 -All
```

If Python is not available as `python`, pass the executable path:

```powershell
.\scripts\test-mcp.ps1 -Python "C:\path\to\python.exe"
```

Background run metadata and results are written under `outputs/mcp_runs/async_runs`.
The actual workflow artifacts remain in the normal run folder referenced by `workflow_run_dir`.

## Notes

The asynchronous prototype uses an in-process thread pool. It is suitable for a local MCP server
session, but it is not a durable distributed queue. If the MCP server process stops, completed
results remain readable from disk, while actively running jobs stop with the process.
Running Python work cannot be force-stopped safely; cancellation is best-effort and may be
reported as `cancellation_requested` until the task finishes.
# Current Cello Artifact and Design Data Notes (2026-06-06)

When `output_dir` is supplied to MCP workflow entry points, external Cello artifacts are stored under an associated `cello_artifacts` directory. Candidate topology summaries preserve:

- `cello_artifact_dir`
- `cello_artifact_manifest_path`
- `part_assignments`
- `design_revision`

The Cello artifact manifest includes execution status, command metadata, input/output files, stdout/stderr, byte sizes, media types, and SHA-256 hashes.

Supported Cello v2 JSON circuit/assignment artifacts can populate `part_assignments`. Unsupported output formats remain available through the manifest but are not silently interpreted.

The Streamlit and MCP layers now share the same `DesignIR`, replacement, DesignDiff, BOM,
GenBank, and SBOL3 implementation. MCP replacement operations are immutable and preserve
revision provenance.

This distinction matters for clients:

- persisted topology data can contain parsed assignments and provenance;
- MCP run comparison remains score-oriented;
- exchange-format files can be produced by either Streamlit or `export_design`;
- no MCP response should describe the demonstration library as experimentally validated.
