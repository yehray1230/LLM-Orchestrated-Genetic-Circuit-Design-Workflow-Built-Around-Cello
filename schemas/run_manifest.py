from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
from typing import Any


RUN_MANIFEST_SCHEMA_VERSION = "1.0"


@dataclass
class ArtifactDigest:
    key: str
    path: str
    sha256: str | None = None
    size_bytes: int | None = None


@dataclass
class RunManifest:
    run_id: str
    request: dict[str, Any]
    request_sha256: str
    status: str = "queued"
    schema_version: str = RUN_MANIFEST_SCHEMA_VERSION
    application_version: str = "1.9.0"
    workflow_version: str = "1.9"
    model: dict[str, Any] = field(default_factory=dict)
    simulation: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] = field(default_factory=dict)
    datasets: list[dict[str, Any]] = field(default_factory=list)
    input_design: dict[str, Any] | None = None
    software: dict[str, Any] = field(default_factory=dict)
    artifacts: list[ArtifactDigest] = field(default_factory=list)
    result_sha256: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_run_manifest(
    run_id: str,
    request: dict[str, Any],
) -> RunManifest:
    safe_request = _redacted(request)
    model = {
        "name": safe_request.get("model_name"),
        "api_base": safe_request.get("api_base"),
        "parameters": {
            "compute_budget": safe_request.get("compute_budget"),
            "monte_carlo_samples": safe_request.get("monte_carlo_samples"),
        },
    }
    return RunManifest(
        run_id=run_id,
        request=safe_request,
        request_sha256=payload_sha256(safe_request),
        model=model,
        simulation=dict(safe_request.get("simulation") or {}),
        scoring={
            "profile": str(safe_request.get("scoring_profile") or "legacy_default"),
            "version": str(safe_request.get("scoring_version") or "1.x"),
        },
        datasets=list(safe_request.get("datasets") or []),
        input_design=(
            dict(safe_request["input_design"])
            if isinstance(safe_request.get("input_design"), dict)
            else None
        ),
        software={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "git_commit": os.getenv("GIT_COMMIT"),
        },
    )


def finalize_run_manifest(
    manifest: RunManifest,
    *,
    status: str,
    result: dict[str, Any],
    started_at: str | None,
    finished_at: str | None,
) -> RunManifest:
    manifest.status = status
    manifest.started_at = started_at
    manifest.finished_at = finished_at
    manifest.result_sha256 = payload_sha256(result)
    manifest.simulation = _simulation_metadata(result) or manifest.simulation
    artifacts = result.get("artifacts")
    manifest.artifacts = [
        _artifact_digest(str(key), value)
        for key, value in (artifacts.items() if isinstance(artifacts, dict) else [])
    ]
    return manifest


def run_manifest_from_dict(payload: dict[str, Any]) -> RunManifest:
    selected = dict(payload)
    selected["artifacts"] = [
        ArtifactDigest(**item)
        for item in selected.get("artifacts", [])
        if isinstance(item, dict)
    ]
    return RunManifest(**selected)


def payload_sha256(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _artifact_digest(key: str, value: Any) -> ArtifactDigest:
    path = Path(str(value))
    if not path.is_file():
        return ArtifactDigest(key=key, path=str(value))
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return ArtifactDigest(
        key=key,
        path=str(path.resolve()),
        sha256=digest.hexdigest(),
        size_bytes=path.stat().st_size,
    )


def _redacted(request: dict[str, Any]) -> dict[str, Any]:
    selected = json.loads(json.dumps(request, default=str))
    for key in ("api_key", "authorization", "token", "password"):
        if selected.get(key):
            selected[key] = "***"
    return selected


def _simulation_metadata(result: dict[str, Any]) -> dict[str, Any]:
    candidates = [result]
    summary = result.get("summary")
    if isinstance(summary, dict):
        candidates.append(summary)
        summary_best = summary.get("best_topology")
        if isinstance(summary_best, dict):
            candidates.append(summary_best)
    best = result.get("best_topology")
    if isinstance(best, dict):
        candidates.append(best)
    for candidate in candidates:
        simulation_result = candidate.get("simulation_result")
        simulation_spec = candidate.get("simulation_spec")
        if not isinstance(simulation_result, dict) and not isinstance(simulation_spec, dict):
            continue
        result_payload = simulation_result if isinstance(simulation_result, dict) else {}
        spec_payload = simulation_spec if isinstance(simulation_spec, dict) else {}
        return {
            "model_id": result_payload.get("model_id", spec_payload.get("model_id")),
            "model_version": result_payload.get(
                "model_version",
                spec_payload.get("model_version"),
            ),
            "configuration_hash": result_payload.get(
                "configuration_hash",
                spec_payload.get("configuration_hash"),
            ),
            "parameter_set_hash": result_payload.get(
                "parameter_set_hash",
                spec_payload.get("parameter_set_hash"),
            ),
            "scenario_set_hash": result_payload.get(
                "scenario_set_hash",
                spec_payload.get("scenario_set_hash"),
            ),
            "result_hash": result_payload.get("result_hash"),
        }
    return {}
