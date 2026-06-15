from __future__ import annotations

import json
from pathlib import Path
import re
import threading
from typing import Any
from uuid import uuid4


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class RepositoryError(ValueError):
    pass


class JsonRepository:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def save(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._path(record_id)
        temp_path = self.base_dir / f".{record_id}.{uuid4().hex}.tmp"
        serialized = json.dumps(payload, indent=2, ensure_ascii=False)
        with self._lock:
            temp_path.write_text(serialized, encoding="utf-8")
            temp_path.replace(path)
        return payload

    def get(self, record_id: str) -> dict[str, Any] | None:
        path = self._path(record_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RepositoryError(f"Invalid JSON record: {record_id}") from exc
        if not isinstance(payload, dict):
            raise RepositoryError(f"Record must contain one JSON object: {record_id}")
        return payload

    def list(self) -> list[dict[str, Any]]:
        records = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return records

    def exists(self, record_id: str) -> bool:
        return self._path(record_id).exists()

    def _path(self, record_id: str) -> Path:
        if not SAFE_ID.fullmatch(record_id):
            raise RepositoryError(
                "Record ID must use only letters, numbers, underscores, and hyphens."
            )
        path = (self.base_dir / f"{record_id}.json").resolve()
        base = self.base_dir.resolve()
        if path.parent != base:
            raise RepositoryError("Record path escaped the repository root.")
        return path
