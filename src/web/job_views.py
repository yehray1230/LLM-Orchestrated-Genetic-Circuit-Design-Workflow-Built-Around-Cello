from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from application.services import ApplicationServices

TERMINAL_RUN_STATUSES = {"completed", "failed", "cancelled", "error"}

@dataclass
class JobContextView:
    id: str
    kind: str  # "design" or "research"
    status: str  # "running", "completed", "failed", "cancelled", "needs_human_input", etc.
    stage: str
    progress: float
    created_at: str | None
    updated_at: str | None
    terminal: bool
    result_summary: dict[str, Any] | None
    warnings: list[str]
    artifacts: list[dict[str, str]]
    can_cancel: bool
    can_resume: bool
    can_retry: bool
    next_poll_ms: int | None

def build_job_view(
    run_id: str,
    kind: str,  # "design" or "research"
    services: ApplicationServices,
) -> JobContextView:
    if kind == "design":
        status = services.runs.status(run_id)
        if status.get("status") == "not_found":
            raise ValueError(f"Design run {run_id} not found.")

        is_term = status.get("status") in TERMINAL_RUN_STATUSES
        res_data = services.runs.result(run_id) if is_term else None

        artifacts_raw = services.runs.artifacts(run_id).get("artifacts", {})
        artifacts = []
        for name, path in artifacts_raw.items():
            artifacts.append({
                "name": name,
                "url": f"/api/v1/designs/{run_id}/exports/{name}"  # Or custom path
            })

        return JobContextView(
            id=run_id,
            kind="design",
            status=status.get("status", "unknown"),
            stage=status.get("stage", "initial"),
            progress=status.get("progress", 0.0),
            created_at=status.get("created_at"),
            updated_at=status.get("updated_at"),
            terminal=is_term,
            result_summary=res_data,
            warnings=status.get("warnings") or [],
            artifacts=artifacts,
            can_cancel=not is_term,
            can_resume=status.get("status") == "needs_human_input",
            can_retry=status.get("status") in ["failed", "cancelled", "error"],
            next_poll_ms=None if is_term else 2000,
        )
    elif kind == "research":
        status = services.research.status(run_id)
        if status.get("status") == "not_found":
            raise ValueError(f"Research run {run_id} not found.")

        is_term = status.get("status") in TERMINAL_RUN_STATUSES
        res_data = services.research.result(run_id) if is_term else None

        artifacts_raw = status.get("artifacts", {})
        if not artifacts_raw and res_data:
            artifacts_raw = res_data.get("artifacts", {})

        artifacts = []
        for name, path in artifacts_raw.items():
            artifacts.append({
                "name": name,
                "url": f"/api/v2/research/runs/{run_id}/artifacts/{name}"
            })

        return JobContextView(
            id=run_id,
            kind="research",
            status=status.get("status", "unknown"),
            stage=status.get("stage", "initial"),
            progress=status.get("progress", 0.0),
            created_at=status.get("created_at"),
            updated_at=status.get("updated_at"),
            terminal=is_term,
            result_summary=res_data,
            warnings=status.get("warnings") or [],
            artifacts=artifacts,
            can_cancel=not is_term,
            can_resume=False,
            can_retry=status.get("status") in ["failed", "cancelled", "error"],
            next_poll_ms=None if is_term else 2000,
        )
    else:
        raise ValueError(f"Unknown job kind: {kind}")
