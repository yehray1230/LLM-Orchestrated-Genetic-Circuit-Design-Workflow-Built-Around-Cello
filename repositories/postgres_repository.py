from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import re
from typing import Any, Iterator

from repositories.json_repository import RepositoryError
from schemas.simulation import canonical_payload_hash


SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
POSTGRES_SCHEMA_VERSION = 2


class PostgresDesignRepository:
    """PostgreSQL DesignIR repository with SQLite-compatible revision semantics."""

    def __init__(self, database_url: str):
        self.database_url = str(database_url or "").strip()
        if not self.database_url:
            raise RepositoryError("PostgreSQL database URL is required.")
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RepositoryError(
                "PostgreSQL support requires psycopg. "
                "Install requirements with the postgres extra."
            ) from exc
        self._psycopg = psycopg
        self._migrate_database()

    def save(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        _validate_id(record_id)
        if str(payload.get("design_id") or record_id) != record_id:
            raise RepositoryError("Record ID does not match payload design_id.")
        selected = json.loads(json.dumps(payload))
        now = _now_iso()
        with self._transaction() as connection:
            current = connection.execute(
                """
                SELECT current_revision, payload_hash, payload_json
                FROM designs WHERE id = %s FOR UPDATE
                """,
                (record_id,),
            ).fetchone()
            content_hash = _content_hash(selected)
            if current and current["payload_hash"] == content_hash:
                return _payload(current["payload_json"])
            revision_number = int(current["current_revision"]) + 1 if current else 1
            parent_revision_id = (
                f"{record_id}_revision_{int(current['current_revision'])}"
                if current
                else None
            )
            revision_id = f"{record_id}_revision_{revision_number}"
            revision = dict(selected.get("revision") or {})
            revision.update(
                {
                    "revision_id": revision_id,
                    "parent_revision_id": parent_revision_id,
                    "revision_number": revision_number,
                    "created_at": revision.get("created_at") or now,
                    "created_by": revision.get("created_by") or "repository",
                    "change_type": revision.get("change_type") or "update",
                    "summary": revision.get("summary")
                    or (
                        "Initial persisted revision."
                        if revision_number == 1
                        else "Persisted design update."
                    ),
                    "changes": list(revision.get("changes") or []),
                }
            )
            selected["revision"] = revision
            payload_hash = canonical_payload_hash(selected)
            serialized = json.dumps(selected, ensure_ascii=False)
            connection.execute(
                """
                INSERT INTO designs(
                    id, name, schema_version, current_revision, payload_json,
                    payload_hash, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                    name = EXCLUDED.name,
                    schema_version = EXCLUDED.schema_version,
                    current_revision = EXCLUDED.current_revision,
                    payload_json = EXCLUDED.payload_json,
                    payload_hash = EXCLUDED.payload_hash,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    record_id,
                    str(selected.get("name") or record_id),
                    str(selected.get("schema_version") or "unknown"),
                    revision_number,
                    serialized,
                    payload_hash,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO design_revisions(
                    design_id, revision_number, revision_id, parent_revision_id,
                    payload_json, payload_hash, created_at, created_by,
                    change_summary
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    record_id,
                    revision_number,
                    revision_id,
                    parent_revision_id,
                    serialized,
                    payload_hash,
                    revision["created_at"],
                    revision["created_by"],
                    revision["summary"],
                ),
            )
        return selected

    def get(self, record_id: str) -> dict[str, Any] | None:
        _validate_id(record_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json, is_archived, is_deleted, is_pinned FROM designs WHERE id = %s",
                (record_id,),
            ).fetchone()
        if row:
            payload = _payload(row["payload_json"])
            payload["is_archived"] = bool(row["is_archived"])
            payload["is_deleted"] = bool(row["is_deleted"])
            payload["is_pinned"] = bool(row["is_pinned"])
            return payload
        return None

    def list(self, show_archived: bool = False, show_deleted: bool = False) -> list[dict[str, Any]]:
        query = "SELECT payload_json, is_archived, is_deleted, is_pinned FROM designs WHERE 1=1"
        if not show_deleted:
            query += " AND is_deleted = FALSE"
        if not show_archived:
            query += " AND is_archived = FALSE"
        query += " ORDER BY updated_at DESC, id"
        with self._connect() as connection:
            rows = connection.execute(query).fetchall()

        results = []
        for row in rows:
            payload = _payload(row["payload_json"])
            payload["is_archived"] = bool(row["is_archived"])
            payload["is_deleted"] = bool(row["is_deleted"])
            payload["is_pinned"] = bool(row["is_pinned"])
            results.append(payload)
        return results

    def exists(self, record_id: str) -> bool:
        _validate_id(record_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM designs WHERE id = %s",
                (record_id,),
            ).fetchone()
        return row is not None

    def list_revisions(self, record_id: str) -> list[dict[str, Any]]:
        _validate_id(record_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT revision_number, revision_id, parent_revision_id,
                       payload_hash, created_at, created_by, change_summary
                FROM design_revisions
                WHERE design_id = %s
                ORDER BY revision_number DESC
                """,
                (record_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_revision(
        self,
        record_id: str,
        revision_number: int,
    ) -> dict[str, Any] | None:
        _validate_id(record_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM design_revisions
                WHERE design_id = %s AND revision_number = %s
                """,
                (record_id, int(revision_number)),
            ).fetchone()
        return _payload(row["payload_json"]) if row else None

    def archive(self, record_id: str) -> None:
        _validate_id(record_id)
        with self._transaction() as connection:
            connection.execute(
                "UPDATE designs SET is_archived = TRUE, updated_at = %s WHERE id = %s",
                (_now_iso(), record_id),
            )

    def unarchive(self, record_id: str) -> None:
        _validate_id(record_id)
        with self._transaction() as connection:
            connection.execute(
                "UPDATE designs SET is_archived = FALSE, updated_at = %s WHERE id = %s",
                (_now_iso(), record_id),
            )

    def soft_delete(self, record_id: str) -> None:
        _validate_id(record_id)
        with self._transaction() as connection:
            connection.execute(
                "UPDATE designs SET is_deleted = TRUE, updated_at = %s WHERE id = %s",
                (_now_iso(), record_id),
            )

    def restore(self, record_id: str) -> None:
        _validate_id(record_id)
        with self._transaction() as connection:
            connection.execute(
                "UPDATE designs SET is_deleted = FALSE, updated_at = %s WHERE id = %s",
                (_now_iso(), record_id),
            )

    def pin(self, record_id: str) -> None:
        _validate_id(record_id)
        with self._transaction() as connection:
            connection.execute(
                "UPDATE designs SET is_pinned = TRUE, updated_at = %s WHERE id = %s",
                (_now_iso(), record_id),
            )

    def unpin(self, record_id: str) -> None:
        _validate_id(record_id)
        with self._transaction() as connection:
            connection.execute(
                "UPDATE designs SET is_pinned = FALSE, updated_at = %s WHERE id = %s",
                (_now_iso(), record_id),
            )

    def purge(self, record_id: str) -> bool:
        _validate_id(record_id)
        with self._transaction() as connection:
            cursor = connection.execute("DELETE FROM designs WHERE id = %s", (record_id,))
            return cursor.rowcount > 0

    def record_payload_migration(
        self,
        *,
        source_id: str,
        source_version: str,
        target_version: str,
        source_hash: str,
        result_hash: str | None,
        status: str,
        report: dict[str, Any],
    ) -> None:
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO migration_records(
                    source_id, source_version, target_version, source_hash,
                    result_hash, status, report_json, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT(source_id, source_hash, target_version) DO UPDATE SET
                    result_hash = EXCLUDED.result_hash,
                    status = EXCLUDED.status,
                    report_json = EXCLUDED.report_json
                """,
                (
                    source_id,
                    source_version,
                    target_version,
                    source_hash,
                    result_hash,
                    status,
                    json.dumps(report, ensure_ascii=False),
                    _now_iso(),
                ),
            )

    @property
    def schema_version(self) -> int:
        return POSTGRES_SCHEMA_VERSION

    def _migrate_database(self) -> None:
        with self._transaction() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS designs(
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    current_revision INTEGER NOT NULL,
                    payload_json JSONB NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    is_pinned BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            connection.execute(
                """
                ALTER TABLE designs ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE designs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
                ALTER TABLE designs ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE;
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS design_revisions(
                    design_id TEXT NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
                    revision_number INTEGER NOT NULL,
                    revision_id TEXT NOT NULL UNIQUE,
                    parent_revision_id TEXT,
                    payload_json JSONB NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    created_by TEXT NOT NULL,
                    change_summary TEXT NOT NULL,
                    PRIMARY KEY(design_id, revision_number)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS migration_records(
                    id BIGSERIAL PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    target_version TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    result_hash TEXT,
                    status TEXT NOT NULL,
                    report_json JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    UNIQUE(source_id, source_hash, target_version)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_designs_schema_version ON designs(schema_version)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_revisions_design_id ON design_revisions(design_id, revision_number)"
            )

    @contextmanager
    def _transaction(self) -> Iterator[Any]:
        with self._connect() as connection:
            try:
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        from psycopg.rows import dict_row

        with self._psycopg.connect(
            self.database_url,
            row_factory=dict_row,
        ) as connection:
            yield connection


def _validate_id(record_id: str) -> None:
    if not SAFE_ID.fullmatch(str(record_id or "")):
        raise RepositoryError(
            "Record ID must use only letters, numbers, underscores, and hyphens."
        )


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return json.loads(json.dumps(value))
    selected = json.loads(str(value))
    if not isinstance(selected, dict):
        raise RepositoryError("Stored payload must contain one JSON object.")
    return selected


def _content_hash(payload: dict[str, Any]) -> str:
    selected = dict(payload)
    selected.pop("revision", None)
    return canonical_payload_hash(selected)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
