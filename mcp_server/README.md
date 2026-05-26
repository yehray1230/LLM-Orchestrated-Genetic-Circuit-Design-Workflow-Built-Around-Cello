# MCP Prototype

This folder is an additive MCP adapter for the existing genetic circuit workflow.
It does not replace or modify the Streamlit UI.

## Tools

- `design_genetic_circuit_quick`: runs a compact Builder -> Translator -> Cello -> ODE -> Critic workflow.
- `start_design_run`: starts a longer background design run and returns `run_id`.
- `get_design_run_status`: polls a background run.
- `get_design_run_result`: returns a finished background run result.
- `list_design_runs`: lists recent background runs, newest first.
- `cancel_design_run`: requests best-effort cancellation for a queued or running run.
- `get_design_run_artifacts`: returns artifact paths and the run manifest when available.
- `compare_design_runs`: ranks completed runs by score and reports metric differences.
- `diagnose_design_run`: produces deterministic findings and next actions for one run.
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

The manifest records each artifact key, path, type, and short description so MCP clients
can inspect outputs without guessing file names.

## Response Shape

Tools keep their existing fields and also include a common error envelope:

- Success responses include `error: null` and `error_type: null`.
- Validation and runtime failures include `status`, `error`, `error_type`, `summary`, and `artifacts`.
- Common `error_type` values are `validation_error`, `dependency_error`,
  `workflow_error`, `external_tool_error`, `not_found`, and `cancelled`.

`compare_design_runs` and `diagnose_design_run` are read-only analysis tools. They use
persisted run results and artifact metadata; they do not call an LLM or rerun the workflow.

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
