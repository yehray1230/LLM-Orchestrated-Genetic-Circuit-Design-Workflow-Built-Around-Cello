# Quickstart

This guide is the shortest path for running and verifying the local research
prototype. For project scope, biological claim boundaries, and architecture,
read `README.md`, `docs/limitations.md`, `docs/architecture.md`, and
`docs/workflow.md`.

## 1. Environment

Use the checked-in virtual environment if it is already available:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

If you need to create a fresh environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 2. Run Tests

Run the full test suite before and after demo-facing changes:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Expected stability target for the current stage:

```text
All tests pass, and no unexpected warning appears during the main suite.
```

## 3. FastAPI / Web Workspace (預設主介面 / Default Interface)

Use this interface for the server-rendered workspace, persistent runs, API
inspection, imports, benchmarks, and design-library flows.

```powershell
.\venv\Scripts\uvicorn.exe api.main:app --reload --host 127.0.0.1 --port 8000
```

If `uvicorn.exe` is unavailable in the environment, use:

```powershell
.\venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
HTML workspace: http://127.0.0.1:8000/web
OpenAPI docs:   http://127.0.0.1:8000/docs
OpenAPI schema: http://127.0.0.1:8000/openapi.json
```

Useful workspace entry points:

```text
Runs and live monitor: /web/runs
Research workspace:    /web/research
Benchmarks:            /web/benchmarks
Guided imports:        /web/imports
Assembly workspace:    /web/assembly
Design library:        /web/designs
```

The OpenAPI document also exposes simulation sweeps and bifurcation reports,
parameter-fit snapshots, host/sequence optimization, readiness-related
artifacts, assembly deliverables, and asynchronous run feedback/resume APIs.

## 4. Streamlit Research UI (Legacy / Maintenance-only)

> [!WARNING]
> This interface has entered maintenance-only mode. All new demo-facing work
> should use the HTML Web Workspace.

Use this interface only as a backup or for legacy research inspection.

```powershell
.\venv\Scripts\streamlit.exe run app.py
```

If `streamlit.exe` is unavailable in the environment, use:

```powershell
.\venv\Scripts\python.exe -m streamlit run app.py
```

## 5. Fixed Demo Intent

Use one stable demo intent for first-pass validation:

```text
Activate GFP only when input A is present and input B is absent.
```

The expected workflow evidence is:

```text
natural-language intent
structured design specification
truth table or logic matrix
Cello-compatible Verilog
explicit Cello mode and claim level
ODE simulation readouts when available
benchmark score
readiness report
exportable artifacts when enough sequence evidence exists
```

## 6. Mock Cello vs Real Cello

The default local workflow may use mock Cello output when no external Cello
command is configured.

Always distinguish these fields in demos and reports:

```text
cello_mode
cello_claim_level
cello_warning
mapping_status
```

Interpretation:

```text
mock Cello:
  Workflow placeholder for UI, parsing, scoring, and control-flow testing.
  It is not real biological part mapping.

real Cello:
  Requires an external Cello command plus compatible UCF/library data.
  Only externally mapped outputs should be described as Cello mapping results.
```

## 7. Demo Readiness Rule

Before showing the project to another person, complete
`docs/developer/demo_checklist.md`.

The phase-one completion target is:

```text
1. The fixed demo path can be run and explained.
2. The full test suite passes.
3. Mock and real Cello claims are visibly separated.
4. Known limitations are stated before biological claims are made.
```
