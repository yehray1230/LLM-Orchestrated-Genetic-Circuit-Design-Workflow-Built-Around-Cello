# Research Workspace v2.0

FastAPI serves both the versioned JSON API and a lower-density,
server-rendered HTML interface. The existing Streamlit application remains
available for detailed research inspection.

## Run

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

- HTML: `http://127.0.0.1:8000/web`
- OpenAPI: `http://127.0.0.1:8000/docs`
- Schema: `http://127.0.0.1:8000/openapi.json`

## API Endpoints

```text
GET  /api/v1/health

POST /api/v1/imports/drafts/validate
POST /api/v1/imports/json
POST /api/v1/imports/genbank
POST /api/v1/imports/{draft_id}/confirm

GET  /api/v1/designs
GET  /api/v1/designs/{design_id}
GET  /api/v1/designs/{design_id}/ir-v2
GET  /api/v1/designs/{design_id}/simulation-spec
GET  /api/v1/designs/{design_id}/revisions
POST /api/v1/comparisons
POST /api/v1/evaluations
GET  /api/v1/evaluation/profiles
GET  /api/v1/simulation/models
POST /api/v1/simulations
GET  /api/v1/benchmarks/datasets
GET  /api/v1/benchmarks/datasets/{dataset_id}
POST /api/v1/benchmarks/runs
GET  /api/v1/benchmarks/runs
GET  /api/v1/benchmarks/runs/{benchmark_run_id}
POST /api/v1/benchmarks/comparisons
GET  /api/v1/designs/{design_id}/exports/{format}
POST /api/v2/backbones
GET  /api/v2/backbones
GET  /api/v2/backbones/{backbone_id}/versions/{version}
POST /api/v2/designs/{design_id}/plasmid-assemblies

POST /api/v1/runs
GET  /api/v1/runs
GET  /api/v1/runs/{run_id}
GET  /api/v1/runs/{run_id}/events
GET  /api/v1/runs/{run_id}/result
GET  /api/v1/runs/{run_id}/artifacts
POST /api/v1/runs/{run_id}/cancel
POST /api/v1/runs/{run_id}/feedback
POST /api/v1/runs/{run_id}/resume

GET  /api/v2/health
POST /api/v2/research/runs
GET  /api/v2/research/runs
GET  /api/v2/research/runs/{run_id}
GET  /api/v2/research/runs/{run_id}/result
GET  /api/v2/research/runs/{run_id}/artifacts/{artifact_key}
POST /api/v2/research/runs/{run_id}/cancel
POST /api/v2/research/comparisons
```

`POST /api/v1/runs` returns `202 Accepted` with a run ID. Clients poll status
and events instead of holding one HTTP request open.

## HTML Pages

```text
/web                 Dashboard
/web/new-design      Start a background design run
/web/runs            Run list
/web/runs/{run_id}   Progress, events, feedback, and result
/web/imports         Guided and file-based external import
/web/designs         Confirmed design library
/web/benchmarks      Versioned benchmark datasets and reports
/web/compare         Design comparison
/web/research        v2 research workspace
/web/research/runs/{run_id}  Simulation, evaluation, and reports
/web/research/compare        Version-aware research comparison
```

The HTML layer uses Jinja2 and a small local polling helper. It is intentionally
server rendered so a later HTMX or React client can reuse the same API and
application services.

## Persistence

```text
outputs/api_data/
  drafts/
  research.db
  benchmark_runs/
  benchmark_reports/
  runs/
```

Set `GENETIC_CIRCUIT_API_DATA_DIR` to use a different root. Draft JSON records
use validated identifiers and atomic replacement. Confirmed DesignIR v2
records, revision history, and migration audit records use SQLite. Legacy
`designs/*.json` records are imported idempotently. Run metadata, events,
feedback, results, artifacts, and reproducibility manifests use the persistent
`RunStore`.

The public v1 design endpoint remains backward compatible. Use `/ir-v2` to
inspect biological context, construct/plasmid layers, field provenance, and
assumptions.

## Batch Migration

```powershell
python -m scripts.migrate_designs_v1_to_v2 `
  outputs/api_data/designs outputs/api_data/research.db --dry-run
```

Remove `--dry-run` to write validated records. Repeated execution skips
existing design IDs and does not create duplicate revisions.

## Research Evaluation

`POST /api/v1/evaluations` accepts `profile_id`. The default API profile is
`research-v1.8`; direct workflow calls retain `legacy-weighted` unless a
profile is selected explicitly.

Each evaluation records the scoring profile and semantic version, immutable
configuration hash, weighted total, grade, seven research dimensions,
original component scores, diagnostic details, and applicability metadata.

Benchmark manifests include a version, content hash, source provenance,
expected score checks, and case tags. Reports are emitted as JSON, CSV, and
Markdown. The bundled smoke dataset is synthetic and must not be presented as
experimental validation.

## Simulation Foundation

The v1.9 endpoints expose versioned `SimulationSpec` and `SimulationResult`
contracts. Results record the ODE model version, configuration hash,
parameter-set hash, scenario-set hash, seed configuration, and result hash.
The optional `research-v2-preview@1.9.0` profile links evaluation output to
these identifiers while `research-v1.8` remains the API default.

Simulation outputs are computational screening estimates, not experimental
protocols or evidence of wet-lab viability.

## v2 Research Runs

`POST /api/v2/research/runs` accepts either a stored `design_id` or a direct
topology. It queues a background task that:

1. builds the versioned simulation configuration,
2. runs the resource-aware ODE model,
3. evaluates the candidate with a versioned scoring profile,
4. writes JSON, CSV, and Markdown reports,
5. persists a reproducibility manifest.

Research comparisons reject unfinished runs and mark comparisons as
descriptive when simulation-model or scoring versions differ.

## PostgreSQL

SQLite remains the default local backend. Set:

```powershell
$env:GENETIC_CIRCUIT_DATABASE_URL="postgresql://user:password@host/database"
```

to use PostgreSQL for DesignIR v2 records and revision history. The adapter
creates equivalent design, revision, and migration tables during startup.

Set `GENETIC_CIRCUIT_CORS_ORIGINS` to a comma-separated list when a future
frontend runs on other origins.

## Credential Boundary

API and HTML requests do not accept provider API keys. Configure model
credentials through server environment variables such as `LITELLM_API_KEY` or
`OPENAI_API_KEY`.
