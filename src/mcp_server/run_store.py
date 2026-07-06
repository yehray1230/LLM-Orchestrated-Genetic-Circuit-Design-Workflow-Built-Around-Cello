from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from mcp_server.artifact_writer import DEFAULT_OUTPUT_DIR, write_json
from mcp_server.serializers import to_jsonable
from schemas.run_manifest import (
    create_run_manifest,
    finalize_run_manifest,
    run_manifest_from_dict,
)


TERMINAL_STATUSES = {"completed", "needs_human_input", "error", "failed", "cancelled"}
NON_TERMINAL_STATUSES = {"queued", "running", "cancellation_requested"}


class RunStore:
    """Small in-process run manager for the MCP prototype."""

    def __init__(self, base_dir: str | Path | None = None, max_workers: int = 2):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_OUTPUT_DIR / "async_runs"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="mcp-design-run")
        self._futures: dict[str, Future] = {}
        self._lock = threading.RLock()

    def start(
        self,
        task: Callable[[], dict[str, Any]],
        request: dict[str, Any],
        run_id: str | None = None,
    ) -> dict[str, Any]:
        selected_run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        run_dir = self.base_dir / selected_run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        run_manifest_path = run_dir / "run_manifest.json"
        run_manifest = create_run_manifest(selected_run_id, request)
        write_json(run_manifest_path, run_manifest)
        metadata = {
            "run_id": selected_run_id,
            "status": "queued",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "started_at": None,
            "finished_at": None,
            "request": _redact_request(request),
            "run_dir": str(run_dir.resolve()),
            "result_path": str((run_dir / "result.json").resolve()),
            "run_manifest_path": str(run_manifest_path.resolve()),
            "error": None,
            "error_type": None,
            "cancellation_requested": False,
            "stage": "queued",
            "progress": 0.0,
            "event_count": 0,
        }
        self._write_metadata(run_dir, metadata)
        self.append_event(selected_run_id, "run", "queued", 0.0, "Run queued.")

        future = self._executor.submit(self._run_task, selected_run_id, run_dir, task)
        with self._lock:
            self._futures[selected_run_id] = future

        return self.status(selected_run_id)

    def append_event(
        self,
        run_id: str,
        stage: str,
        status: str,
        progress: float,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return _not_found(run_id)
        with self._lock:
            metadata = self._read_metadata(run_dir)
            event_id = int(metadata.get("event_count") or 0) + 1
            event = {
                "event_id": event_id,
                "run_id": run_id,
                "stage": str(stage),
                "status": str(status),
                "progress": max(0.0, min(float(progress), 1.0)),
                "message": str(message),
                "details": to_jsonable(details or {}),
                "timestamp": _now_iso(),
            }
            events_path = run_dir / "events.jsonl"
            with events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            metadata.update(
                {
                    "stage": event["stage"],
                    "progress": event["progress"],
                    "event_count": event_id,
                    "updated_at": event["timestamp"],
                }
            )
            self._write_metadata(run_dir, metadata)
        return event

    def events(self, run_id: str, after_event_id: int = 0, limit: int = 100) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return _not_found(run_id)
        selected_limit = max(1, min(int(limit), 500))
        events_path = run_dir / "events.jsonl"
        events: list[dict[str, Any]] = []
        if events_path.exists():
            for line in events_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if int(event.get("event_id") or 0) > int(after_event_id):
                    events.append(event)
        metadata = self._read_metadata(run_dir)
        return {
            **_public_status(metadata),
            "error": None,
            "error_type": None,
            "events": events[:selected_limit],
            "count": min(len(events), selected_limit),
            "has_more": len(events) > selected_limit,
            "last_event_id": events[min(len(events), selected_limit) - 1]["event_id"] if events else int(after_event_id),
        }

    def status(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return _not_found(run_id)
        metadata = self._read_metadata(run_dir)
        future = self._futures.get(run_id)
        if future and not future.done() and metadata.get("status") == "queued":
            metadata["status"] = "queued"
        return _public_status(metadata)

    def list_runs(self, limit: int = 20) -> dict[str, Any]:
        selected_limit = max(1, min(int(limit), 100))
        runs = []
        for run_dir in self.base_dir.iterdir():
            if not run_dir.is_dir():
                continue
            metadata_path = run_dir / "metadata.json"
            if not metadata_path.exists():
                continue
            try:
                runs.append(_public_status(self._read_metadata(run_dir)))
            except RuntimeError:
                continue
        runs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return {
            "status": "completed",
            "error": None,
            "error_type": None,
            "runs": runs[:selected_limit],
            "count": min(len(runs), selected_limit),
            "total": len(runs),
        }

    def cancel(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return _not_found(run_id)
        metadata = self._read_metadata(run_dir)
        status = str(metadata.get("status") or "unknown")
        if status in TERMINAL_STATUSES:
            return {
                **_public_status(metadata),
                "message": f"Run is already terminal with status: {status}.",
            }

        future = self._futures.get(run_id)
        cancelled = bool(future.cancel()) if future else False
        if cancelled:
            result = {
                "status": "cancelled",
                "error": "Run was cancelled before it started.",
                "error_type": "cancelled",
                "async_run_id": run_id,
                "async_run_dir": str(run_dir.resolve()),
            }
            write_json(run_dir / "result.json", result)
            metadata.update(
                {
                    "status": "cancelled",
                    "finished_at": _now_iso(),
                    "updated_at": _now_iso(),
                    "error": "Run was cancelled before it started.",
                    "error_type": "cancelled",
                    "cancellation_requested": True,
                }
            )
            self._finalize_manifest(
                run_dir,
                metadata,
                "cancelled",
                result,
            )
        else:
            metadata.update(
                {
                    "status": "cancellation_requested",
                    "updated_at": _now_iso(),
                    "cancellation_requested": True,
                    "message": "Cancellation requested. Running Python tasks cannot be force-stopped safely.",
                }
            )
        self._write_metadata(run_dir, metadata)
        return _public_status(metadata)

    def artifacts(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return _not_found(run_id)
        metadata = self._read_metadata(run_dir)
        artifacts = metadata.get("artifacts", {})
        manifest = None
        if isinstance(artifacts, dict):
            manifest_path = artifacts.get("manifest_json")
            if manifest_path and Path(str(manifest_path)).exists():
                manifest = json.loads(Path(str(manifest_path)).read_text(encoding="utf-8"))
        return {
            **_public_status(metadata),
            "error": None,
            "error_type": None,
            "artifacts": artifacts if isinstance(artifacts, dict) else {},
            "manifest": manifest,
        }

    def result(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return _not_found(run_id)
        metadata = self._read_metadata(run_dir)
        status = str(metadata.get("status") or "unknown")
        if status not in TERMINAL_STATUSES:
            return {
                **_public_status(metadata),
                "error_type": None,
                "message": "Run is not finished yet. Call get_design_run_status again later.",
            }

        result_path = Path(str(metadata.get("result_path") or run_dir / "result.json"))
        if not result_path.exists():
            return {
                **_public_status(metadata),
                "error": metadata.get("error") or "Run finished but result.json was not written.",
                "error_type": metadata.get("error_type") or "workflow_error",
            }
        return json.loads(result_path.read_text(encoding="utf-8"))

    def _run_task(self, run_id: str, run_dir: Path, task: Callable[[], dict[str, Any]]) -> None:
        with self._lock:
            metadata = self._read_metadata(run_dir)
            metadata.update({"status": "running", "started_at": _now_iso(), "updated_at": _now_iso()})
            self._write_metadata(run_dir, metadata)
        self.append_event(run_id, "run", "running", 0.02, "Run started.")

        try:
            result = task()
            result = to_jsonable(result)
            status = str(result.get("status") or "completed")
            if status not in TERMINAL_STATUSES:
                status = "completed"
            result["async_run_id"] = run_id
            result["async_run_dir"] = str(run_dir.resolve())
            write_json(run_dir / "result.json", result)
            with self._lock:
                latest_metadata = self._read_metadata(run_dir)
                cancellation_was_requested = bool(latest_metadata.get("cancellation_requested"))
                metadata = latest_metadata
                metadata.update(
                    {
                        "status": status,
                        "finished_at": _now_iso(),
                        "updated_at": _now_iso(),
                        "result_status": result.get("status"),
                        "workflow_run_dir": result.get("run_dir"),
                        "artifacts": result.get("artifacts", {}),
                        "summary": _compact_summary(result.get("summary", {})),
                        "error": result.get("error"),
                        "error_type": result.get("error_type"),
                    }
                )
                if cancellation_was_requested and status in TERMINAL_STATUSES:
                    metadata["message"] = "Cancellation was requested, but the run completed before it could stop."
                self._finalize_manifest(run_dir, metadata, status, result)
                self._write_metadata(run_dir, metadata)
            self._append_terminal_event(
                run_id,
                status,
                "Run finished."
                if status == "completed"
                else f"Run finished with status {status}.",
            )
        except Exception as exc:
            error_result = {
                "status": "failed",
                "async_run_id": run_id,
                "async_run_dir": str(run_dir.resolve()),
                "error": str(exc),
                "error_type": "workflow_error",
            }
            write_json(run_dir / "result.json", error_result)
            with self._lock:
                metadata = self._read_metadata(run_dir)
                metadata.update(
                    {
                        "status": "failed",
                        "finished_at": _now_iso(),
                        "updated_at": _now_iso(),
                        "error": str(exc),
                        "error_type": "workflow_error",
                    }
                )
                self._finalize_manifest(
                    run_dir,
                    metadata,
                    "failed",
                    error_result,
                )
                self._write_metadata(run_dir, metadata)
            self._append_terminal_event(
                run_id,
                "failed",
                f"Run failed: {exc}",
            )

    def _append_terminal_event(
        self,
        run_id: str,
        status: str,
        message: str,
    ) -> None:
        try:
            self.append_event(run_id, "run", status, 1.0, message)
        except (OSError, RuntimeError):
            # The result and terminal metadata are authoritative. A transient
            # event-log write failure must not rewrite a completed run as failed.
            return

    def _run_dir(self, run_id: str) -> Path:
        return self.base_dir / run_id

    def _read_metadata(self, run_dir: Path) -> dict[str, Any]:
        metadata_path = run_dir / "metadata.json"
        last_error: Exception | None = None
        for _ in range(5):
            try:
                return json.loads(metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, FileNotFoundError, PermissionError) as exc:
                last_error = exc
                time.sleep(0.02)
        raise RuntimeError(f"Could not read run metadata at {metadata_path}: {last_error}")

    def _write_metadata(self, run_dir: Path, metadata: dict[str, Any]) -> None:
        metadata_path = run_dir / "metadata.json"
        temp_path = run_dir / f"metadata.{uuid.uuid4().hex}.tmp"
        with self._lock:
            write_json(temp_path, metadata)
            for i in range(10):
                try:
                    temp_path.replace(metadata_path)
                    break
                except PermissionError:
                    if i == 9:
                        raise
                    time.sleep(0.05)

    def _finalize_manifest(
        self,
        run_dir: Path,
        metadata: dict[str, Any],
        status: str,
        result: dict[str, Any],
    ) -> None:
        manifest_path = run_dir / "run_manifest.json"
        if not manifest_path.exists():
            return
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = finalize_run_manifest(
            run_manifest_from_dict(manifest_payload),
            status=status,
            result=result,
            started_at=metadata.get("started_at"),
            finished_at=metadata.get("finished_at"),
        )
        write_json(manifest_path, manifest)
        artifacts = metadata.get("artifacts")
        if not isinstance(artifacts, dict):
            artifacts = {}
        artifacts["run_manifest_json"] = str(manifest_path.resolve())
        metadata["artifacts"] = artifacts


def _public_status(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": metadata.get("run_id"),
        "status": metadata.get("status"),
        "created_at": metadata.get("created_at"),
        "started_at": metadata.get("started_at"),
        "finished_at": metadata.get("finished_at"),
        "updated_at": metadata.get("updated_at"),
        "run_dir": metadata.get("run_dir"),
        "workflow_run_dir": metadata.get("workflow_run_dir"),
        "result_path": metadata.get("result_path"),
        "run_manifest_path": metadata.get("run_manifest_path"),
        "summary": metadata.get("summary", {}),
        "artifacts": metadata.get("artifacts", {}),
        "error": metadata.get("error"),
        "error_type": metadata.get("error_type"),
        "cancellation_requested": metadata.get("cancellation_requested", False),
        "message": metadata.get("message"),
        "stage": metadata.get("stage"),
        "progress": metadata.get("progress", 0.0),
        "event_count": metadata.get("event_count", 0),
    }


def _not_found(run_id: str) -> dict[str, Any]:
    return {
        "status": "not_found",
        "run_id": run_id,
        "error": f"Unknown run_id: {run_id}",
        "error_type": "not_found",
        "summary": {},
        "artifacts": {},
    }


def _compact_summary(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    best_topology = summary.get("best_topology")
    if not isinstance(best_topology, dict):
        best_topology = {}
    return {
        "user_intent": summary.get("user_intent"),
        "host_organism": summary.get("host_organism"),
        "is_completed": summary.get("is_completed"),
        "is_approved": summary.get("is_approved"),
        "requires_human_input": summary.get("requires_human_input"),
        "pause_reason": summary.get("pause_reason"),
        "current_node_id": summary.get("current_node_id"),
        "current_node_status": summary.get("current_node_status"),
        "used_budget": summary.get("used_budget"),
        "compute_budget": summary.get("compute_budget"),
        "latest_critic_feedback": summary.get("latest_critic_feedback"),
        "score": best_topology.get("score"),
        "mapping_status": best_topology.get("mapping_status"),
        "cello_mode": best_topology.get("cello_mode"),
        "cello_claim_level": best_topology.get("cello_claim_level"),
        "cello_warning": best_topology.get("cello_warning"),
        "ode_status": best_topology.get("ode_status"),
    }


def _redact_request(request: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(request)
    if redacted.get("api_key"):
        redacted["api_key"] = "***"
    return to_jsonable(redacted)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
