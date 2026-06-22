# Demo Checklist / 展示檢查清單

Use this checklist before a demo, supervisor meeting, research discussion, or
major refactor that could affect the visible workflow.

本清單用於展示、指導教授討論、研究討論，或任何可能影響主流程的重構前後。

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

## Pre-Demo Stability

- [ ] Confirm the working tree only contains intentional changes.
- [ ] Run the full test suite:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

- [ ] Confirm all tests pass.
- [ ] Confirm there are no unexpected warnings in the main test output.
- [ ] Confirm dependency commands use the active project environment.

## Streamlit Research UI

- [ ] Start the Streamlit app:

```powershell
.\venv\Scripts\streamlit.exe run app.py
```

- [ ] Open the app in the browser.
- [ ] Enter the fixed demo intent.
- [ ] Confirm PM Agent structured-spec collection is understandable.
- [ ] Confirm the workflow can produce or display a candidate result.
- [ ] Confirm result panels distinguish generated design evidence from
      biological validation.

## FastAPI / Web Workspace

- [ ] Start the API and web workspace:

```powershell
.\venv\Scripts\uvicorn.exe api.main:app --reload --host 127.0.0.1 --port 8000
```

- [ ] Open `http://127.0.0.1:8000/web`.
- [ ] Open `http://127.0.0.1:8000/docs`.
- [ ] Confirm `/api/v1/health` or `/api/v2/health` responds successfully.
- [ ] Confirm run, import, design, benchmark, or research pages load without
      template errors.

## Workflow Evidence

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

## Cello Claim Boundary

- [ ] If `cello_mode` is `mock`, describe the output as workflow/testing
      evidence only.
- [ ] If `cello_mode` is `external`, confirm the Cello command, UCF/library,
      return code, artifact manifest, and mapping status are visible.
- [ ] Do not describe mock output as real biological part assignment.
- [ ] Do not describe any candidate as experimentally validated unless actual
      construction and measurement evidence is provided.

## Result Handoff

- [ ] Note the tested date and command used.
- [ ] Record whether Streamlit, FastAPI `/web`, and OpenAPI loaded.
- [ ] Record whether the fixed demo completed.
- [ ] Record any known blocker, missing artifact, or biological limitation.
- [ ] Keep any generated reports or artifacts under the expected `outputs/`
      location.

## Phase-One Done Criteria

- [ ] The fixed demo path can be run and explained end to end.
- [ ] The full test suite passes.
- [ ] Mock Cello and real Cello are visibly separated in the result.
- [ ] The project's safe claim boundary is stated clearly.
- [ ] A new collaborator can start from `QUICKSTART.md` without reading the
      full repository first.
