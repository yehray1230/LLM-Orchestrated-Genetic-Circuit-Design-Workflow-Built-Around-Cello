# Demo Checklist

Use this checklist before a demo, supervisor meeting, research discussion, or
publishing a front-end migration milestone to GitHub.

## Demo Scope

Fixed demo intent:

```text
Activate GFP only when input A is present and input B is absent.
```

Safe project claim:

```text
This project generates and evaluates computational candidate designs for
regulatory logic circuits. It does not yet produce complete, buildable,
experimentally validated genetic circuits.
```

## 1. GitHub Upload Readiness

- [ ] Confirm the working tree only contains intentional changes.
- [ ] Remove or ignore local temp outputs such as `tmp/` and `tmp_test_runs/`.
- [ ] Confirm `.gitignore` covers local caches, test outputs, and generated
      artifacts that should not be committed.
- [ ] Review `git diff --stat` to make sure the change set matches the plan.
- [ ] Review `git diff` for accidental debug code, temporary comments, or
      leaked local-only files.
- [ ] Confirm README and quickstart docs still match the current entry point
      and workflow.
- [ ] If this is a large milestone, create or use a feature branch and publish
      via pull request instead of pushing directly to `main`.

## 2. Core Verification

- [ ] Run the full test suite:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

- [ ] Confirm all tests pass.
- [ ] Confirm there are no unexpected warnings in the main test output.
- [ ] Confirm dependency commands use the active project environment.

If the repo also uses linting or formatting checks, run those too:

- [ ] Lint passes.
- [ ] Formatting passes.
- [ ] Type checks pass, if the project has them.

## 3. Front-End Migration Checks

### FastAPI / Web Workspace (Primary)

- [ ] Start the API and web workspace:

```powershell
.\venv\Scripts\uvicorn.exe src.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

- [ ] Open `http://127.0.0.1:8000/web`.
- [ ] Open `http://127.0.0.1:8000/docs`.
- [ ] Confirm `/api/v1/health` or `/api/v2/health` responds successfully.
- [ ] Confirm run, import, design, benchmark, or research pages load without
      template errors.

### Streamlit Research UI (Legacy / Maintenance-only)

> [!WARNING]
> This interface has entered maintenance-only mode. Use this check only if you
> still need to compare the legacy entry point with the HTML workspace.

- [ ] Start the Streamlit app:

```powershell
.\venv\Scripts\streamlit.exe run app.py
```

- [ ] Confirm the app starts without dependency errors.
- [ ] Confirm the legacy path is clearly distinguished from the new HTML
      workspace.

### UI Behavior

- [ ] Confirm the homepage loads correctly.
- [ ] Confirm navigation links work.
- [ ] Confirm forms submit successfully.
- [ ] Confirm downloads, filters, and state toggles still work.
- [ ] Confirm there are no broken assets, missing templates, or JavaScript
      console errors on the key pages.
- [ ] Confirm the layout remains usable on desktop and a narrow/mobile width.

## 4. Workflow Evidence

For the fixed demo, confirm the available result includes:

- [ ] Natural-language intent.
- [ ] Structured specification or assumptions.
- [ ] Truth table or logic representation.
- [ ] Cello-compatible Verilog.
- [ ] `cello_mode`.
- [ ] `cello_claim_level`.
- [ ] `cello_warning`.
- [ ] `mapping_status`.
- [ ] ODE readouts or an explicit explanation that simulation evidence is not
      available.
- [ ] Benchmark score or evaluation summary.
- [ ] Readiness report or stage/blocker status.
- [ ] Export artifacts, or explicit warnings explaining missing sequence
      evidence.

## 5. Demo Baseline Freeze Packet

Generate the fixed baseline evidence packet:

```powershell
.\venv\Scripts\python.exe scripts\generate_demo_baseline.py --timeout-seconds 60
```

Confirm the generated packet reports the staged baseline progression:

```text
conceptual -> sequence_complete -> assembly_planned -> primer_ready
```

- [ ] `demo_baseline_packet.json` exists under `outputs/demo_baseline/`.
- [ ] `demo_baseline_summary.md` exists under `outputs/demo_baseline/`.
- [ ] `sequence_analysis.json` exists and reports zero blocked parts.
- [ ] `assembly_plan.json` exists and uses
      `abstract_non_experimental_ordering`.
- [ ] `primer_readiness.json` exists and reports `status: ready`.
- [ ] The final readiness status is `primer_ready`.
- [ ] The next required stage is `sequence_optimized`.
- [ ] `primer_readiness.json` reports
      `actual_primer_sequences_generated: false`.
- [ ] `primer_readiness.json` states that no primer sequences, oligo order
      information, PCR conditions, or wet-lab protocol are included.
- [ ] `experimental_readiness_score` remains null/empty for this demo gate.
- [ ] The packet claim boundary still says the result is computational
      screening evidence, not wet-lab validation or an experimental protocol.

Recommended focused validation before pushing this milestone:

```powershell
.\venv\Scripts\python.exe -m pytest tests\test_demo_baseline_freeze.py tests\test_readiness_evaluator.py -q
```

Recommended review / commit scope for the baseline-freeze milestone:

- `application/demo_baseline.py`
- `scripts/generate_demo_baseline.py`
- `tests/test_demo_baseline_freeze.py`
- `tests/test_readiness_evaluator.py`
- `benchmark_suite/readiness_evaluator.py`
- `DEMO_CHECKLIST.md`

Generated `outputs/demo_baseline/` packets are local evidence artifacts. Keep
them out of the commit unless a specific frozen artifact is intentionally being
published.

## 6. Phase 1/2 API Validation

- [ ] Create a local/private fitted snapshot with
      `POST /api/v1/benchmarks/parameter-fits`.
- [ ] Confirm the snapshot is listed by
      `GET /api/v1/benchmarks/parameter-fits`.
- [ ] Run `POST /api/v1/simulations` with `parameter_fit_snapshot_id` and
      confirm the candidate includes `applied_parameter_fit_snapshot`.
- [ ] Run
      `POST /api/v1/benchmarks/parameter-fits/{snapshot_id}/comparison` and
      confirm `default_run`, `fitted_run`, `metric_deltas`,
      `provenance_delta`, and `report_hash` are present.
- [ ] Run `POST /api/v1/simulations/sweep` for a parameter such as
      `copy_number` or `ribosome_total`, and confirm the response includes
      `report_type`, `schema_version`, `host_profile_id`, and row-level
      dynamic margin, SNR, kinetic score, and burden fields.
- [ ] Compare host profile effects by running the same simulation with
      `ecoli_k12_default`, `yeast_sc_default`, and `mammalian_cho_default`;
      confirm the resulting `biokinetic_parameters.host` and provenance
      summaries change.
- [ ] If temporal inputs are demonstrated, use the structured
      `temporal_inputs` schema and confirm the simulation configuration hash
      changes when the temporal pattern changes.
- [ ] If layout critique is demonstrated, confirm layout issues are reported
      with `schema_version`, `code`, `severity`, `subject_id`, and `message`.

## 7. Cello Claim Boundary

- [ ] If `cello_mode` is `mock`, describe the output as workflow/testing
      evidence only.
- [ ] If `cello_mode` is `external`, confirm the Cello command, UCF/library,
      return code, artifact manifest, and mapping status are visible.
- [ ] Do not describe mock output as real biological part assignment.
- [ ] Do not describe any candidate as experimentally validated unless actual
      construction and measurement evidence is provided.

## 8. Result Handoff

- [ ] Note the tested date and command used.
- [ ] Record whether Streamlit, FastAPI `/web`, and OpenAPI loaded.
- [ ] Record whether the fixed demo completed.
- [ ] Record any known blocker, missing artifact, or biological limitation.
- [ ] Keep any generated reports or artifacts under the expected `outputs/`
      location.

## 9. Phase-One Done Criteria

- [ ] The fixed demo path can be run and explained end to end.
- [ ] The full test suite passes.
- [ ] Mock Cello and real Cello are visibly separated in the result.
- [ ] The project's safe claim boundary is stated clearly.
- [ ] A new collaborator can start from `QUICKSTART.md` without reading the
      full repository first.
