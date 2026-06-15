from __future__ import annotations

import hashlib
import json
import mimetypes
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from benchmark_suite.cello_constraint_evaluator import evaluate_cello_constraints
from schemas.state import DesignState
from tools.cello_artifact_parser import CelloV2JsonParser
from tools.part_library import PartLibrary


class CelloWrapper:
    def __init__(
        self,
        cello_command: str | list[str] | None = None,
        ucf_path: str | None = None,
        work_dir: str | Path | None = None,
        artifact_dir: str | Path | None = None,
        part_library_path: str | Path | None = None,
        timeout_seconds: int = 120,
        max_log_chars: int = 4000,
    ):
        self.cello_command = cello_command
        self.ucf_path = ucf_path
        self.work_dir = Path(work_dir) if work_dir else None
        self.artifact_dir = Path(artifact_dir) if artifact_dir else Path("outputs") / "cello_artifacts"
        self.part_library = (
            PartLibrary.from_json(part_library_path)
            if part_library_path
            else PartLibrary.demo()
        )
        self.artifact_parser = CelloV2JsonParser(self.part_library)
        self.timeout_seconds = timeout_seconds
        self.max_log_chars = max_log_chars

    def run(self, state: DesignState) -> DesignState:
        node = state.tree_nodes.get(state.current_node_id) if state.current_node_id else None
        codes = node.verilog_codes if node else state.verilog_codes
        valid_codes = [code for code in codes if code and not code.startswith("ERROR:")]
        if not valid_codes:
            state.last_error = "ERROR: CelloWrapper received no valid Verilog."
            return state

        if self.cello_command is None:
            topologies = [self._mock_topology(index, code) for index, code in enumerate(valid_codes)]
        else:
            topologies = [self._run_external_cello(index, code) for index, code in enumerate(valid_codes)]

        proposals = node.logic_proposals if node else state.logic_proposals
        for i, topo in enumerate(topologies):
            copy_number = 1
            chassis = state.host_organism
            if proposals and i < len(proposals):
                try:
                    data = json.loads(proposals[i])
                    copy_number = int(data.get("copy_number", 1))
                    chassis = str(data.get("chassis") or state.host_organism)
                except Exception:
                    pass
            topo["copy_number"] = copy_number
            topo["chassis"] = chassis

        if node:
            node.candidate_topologies = topologies
        state.candidate_topologies = topologies
        state.last_error = None
        return state

    def _mock_topology(self, index: int, code: str) -> dict[str, Any]:
        return {
            "source": "mock_cello_wrapper",
            "cello_mode": "mock",
            "cello_claim_level": "mock_only",
            "cello_warning": "Mock Cello output is only a workflow placeholder. Do not interpret it as real part mapping or buildability.",
            "verilog_index": index,
            "verilog": code,
            "score": 0.0,
            "mapping_status": "unmapped",
            "orthogonality_score": 1.0,
            "cello_assignment_score": 0.0,
            "cello_buildable": False,
        }

    def _run_external_cello(self, index: int, code: str) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(dir=self.work_dir) as temp_dir:
            temp_path = Path(temp_dir)
            netlist_path = temp_path / f"candidate_{index}.v"
            output_dir = temp_path / "output"
            output_dir.mkdir(exist_ok=True)
            netlist_path.write_text(code, encoding="utf-8")
            command = self._build_command(netlist_path, output_dir)
            completed: subprocess.CompletedProcess[str] | None = None
            try:
                completed = subprocess.run(
                    command,
                    cwd=temp_path,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = _exception_stream_text(exc.stdout)
                stderr = _exception_stream_text(exc.stderr)
                artifact_data = self._persist_artifacts(
                    index=index,
                    temp_path=temp_path,
                    command=command,
                    status="timeout",
                    stdout=stdout,
                    stderr=stderr,
                    return_code=None,
                )
                return self._failed_topology(
                    index,
                    code,
                    "TIMEOUT",
                    f"Cello mapping timed out after {self.timeout_seconds} seconds.",
                    stdout + "\n" + stderr,
                    artifact_data=artifact_data,
                )
            except Exception as exc:
                artifact_data = self._persist_artifacts(
                    index=index,
                    temp_path=temp_path,
                    command=command,
                    status="wrapper_exception",
                    stdout="",
                    stderr=repr(exc),
                    return_code=None,
                )
                return self._failed_topology(
                    index,
                    code,
                    "WRAPPER_EXCEPTION",
                    f"Cello wrapper crashed before mapping: {exc}",
                    repr(exc),
                    artifact_data=artifact_data,
                )

            log = f"STDOUT:\n{completed.stdout or ''}\nSTDERR:\n{completed.stderr or ''}"
            if completed.returncode != 0:
                category = _classify_error_log(log)
                artifact_data = self._persist_artifacts(
                    index=index,
                    temp_path=temp_path,
                    command=command,
                    status="mapping_failed",
                    stdout=completed.stdout or "",
                    stderr=completed.stderr or "",
                    return_code=completed.returncode,
                )
                return self._failed_topology(
                    index,
                    code,
                    category,
                    _summarize_error(category, log),
                    log,
                    return_code=completed.returncode,
                    artifact_data=artifact_data,
                )

            artifact_data = self._persist_artifacts(
                index=index,
                temp_path=temp_path,
                command=command,
                status="mapped",
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                return_code=completed.returncode,
            )
            parse_result = self.artifact_parser.parse_directory(
                artifact_data["cello_artifact_dir"]
            )
            topology = {
                "source": "external_cello_wrapper",
                "cello_mode": "external",
                "cello_claim_level": "externally_mapped",
                "cello_warning": "External Cello completed. Buildability still depends on the selected UCF/library and expert review.",
                "verilog_index": index,
                "verilog": code,
                "score": 0.0,
                "mapping_status": "mapped",
                "orthogonality_score": 1.0,
                "cello_assignment_score": 0.0,
                "cello_buildable": True,
                "cello_stdout": _truncate_error_log(completed.stdout or "", self.max_log_chars),
                "ucf_path": self.ucf_path,
                "part_assignments": parse_result.assignments,
                "cello_parser": {
                    "name": parse_result.parser,
                    "version": parse_result.parser_version,
                    "source_files": parse_result.source_files,
                    "warnings": parse_result.warnings,
                },
                "part_library": {
                    "library_id": self.part_library.library_id,
                    "version": self.part_library.version,
                    "evidence_level": self.part_library.evidence_level,
                    "source_path": self.part_library.source_path,
                },
                **artifact_data,
            }
            topology.update(_topology_cello_metrics(topology))
            return topology

    def _build_command(self, netlist_path: Path, output_dir: Path) -> list[str]:
        command = shlex.split(self.cello_command) if isinstance(self.cello_command, str) else list(self.cello_command or [])
        expanded: list[str] = []
        for part in command:
            expanded.append(
                part.replace("{input_netlist}", str(netlist_path))
                .replace("{output_dir}", str(output_dir))
                .replace("{ucf_path}", self.ucf_path or "")
            )
        return expanded

    def _failed_topology(
        self,
        index: int,
        code: str,
        category: str,
        summary: str,
        raw_log: str,
        return_code: int | None = None,
        artifact_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        topology = {
            "source": "external_cello_wrapper",
            "cello_mode": "external",
            "cello_claim_level": "external_mapping_failed",
            "cello_warning": "External Cello was attempted but mapping failed. Do not claim Cello assignment or buildability.",
            "verilog_index": index,
            "verilog": code,
            "score": 0.0,
            "mapping_status": "MAPPING_FAILED",
            "error_type": "PART_ERROR",
            "orthogonality_score": 1.0,
            "cello_assignment_score": 0.0,
            "cello_buildable": False,
            "mapping_error_category": category,
            "mapping_error_summary": summary,
            "raw_error_log": _truncate_error_log(raw_log, self.max_log_chars),
            "return_code": return_code,
            "ucf_path": self.ucf_path,
            **(artifact_data or {}),
        }
        topology.update(_topology_cello_metrics(topology))
        return topology

    def _persist_artifacts(
        self,
        *,
        index: int,
        temp_path: Path,
        command: list[str],
        status: str,
        stdout: str,
        stderr: str,
        return_code: int | None,
    ) -> dict[str, Any]:
        created_at = datetime.now(timezone.utc)
        run_id = f"candidate_{index}_{created_at.strftime('%Y%m%dT%H%M%S%fZ')}_{uuid4().hex[:8]}"
        artifact_root = self.artifact_dir.resolve()
        artifact_root.mkdir(parents=True, exist_ok=True)
        persistent_dir = artifact_root / run_id

        (temp_path / "stdout.log").write_text(stdout, encoding="utf-8")
        (temp_path / "stderr.log").write_text(stderr, encoding="utf-8")
        shutil.copytree(temp_path, persistent_dir)

        manifest_path = persistent_dir / "artifact_manifest.json"
        file_entries = [
            _artifact_file_entry(path, persistent_dir)
            for path in sorted(persistent_dir.rglob("*"))
            if path.is_file() and path != manifest_path
        ]
        manifest = {
            "schema_version": "1.0",
            "run_id": run_id,
            "candidate_index": index,
            "created_at": created_at.isoformat(),
            "status": status,
            "command": command,
            "return_code": return_code,
            "ucf_path": str(Path(self.ucf_path).resolve()) if self.ucf_path else None,
            "artifact_root": str(persistent_dir.resolve()),
            "files": file_entries,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "cello_artifact_dir": str(persistent_dir.resolve()),
            "cello_artifact_manifest_path": str(manifest_path.resolve()),
            "cello_artifact_manifest": manifest,
            "cello_artifacts": file_entries,
        }


def _topology_cello_metrics(topology: dict[str, Any]) -> dict[str, Any]:
    metrics = evaluate_cello_constraints(topology)
    return {
        "orthogonality_score": metrics["orthogonality_score"],
        "cello_assignment_score": metrics["cello_assignment_score"],
        "cello_buildable": metrics["cello_buildable"],
        "toxicity": metrics["toxicity"],
        "toxicity_score": metrics["toxicity_score"],
        "cello_constraint_report": metrics,
    }


def _artifact_file_entry(path: Path, root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    media_type, _ = mimetypes.guess_type(path.name)
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "absolute_path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "media_type": media_type or "application/octet-stream",
    }


def _exception_stream_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _classify_error_log(log: str) -> str:
    lowered = log.lower()
    if "ucf" in lowered and any(token in lowered for token in ("missing", "mismatch", "incompatible", "constraint")):
        return "UCF_INCOMPATIBLE"
    if any(token in lowered for token in ("syntax error", "parse error", "verilog")):
        return "VERILOG_SYNTAX_ERROR"
    if any(token in lowered for token in ("unsupported gate", "unsupported primitive", "cannot map")):
        return "UNSUPPORTED_GATE"
    if any(token in lowered for token in ("part unavailable", "no gate", "not found in library")):
        return "PART_UNAVAILABLE"
    if "timeout" in lowered:
        return "TIMEOUT"
    return "MAPPING_FAILED"


def _summarize_error(category: str, log: str) -> str:
    first_line = next((line.strip() for line in log.splitlines() if line.strip()), "")
    last_exception = next(
        (
            line.strip()
            for line in reversed(log.splitlines())
            if any(token in line.lower() for token in ("exception", "error", "failed"))
        ),
        "",
    )
    detail = last_exception or first_line or "Cello mapping failed."
    return f"{category}: {detail[:500]}"


def _truncate_error_log(log: str, max_chars: int = 4000) -> str:
    text = (log or "").strip()
    if len(text) <= max_chars:
        return text
    head_len = max(500, max_chars // 2)
    tail_len = max(500, max_chars - head_len - 120)
    head = text[:head_len].rstrip()
    tail = text[-tail_len:].lstrip()
    omitted = len(text) - len(head) - len(tail)
    return f"{head}\n\n... [truncated {omitted} chars of middle stack trace/log] ...\n\n{tail}"
