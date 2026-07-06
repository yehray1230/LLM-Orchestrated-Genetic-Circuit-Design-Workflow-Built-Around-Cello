from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from repositories.json_repository import JsonRepository
from repositories.sqlite_repository import (
    SqliteDesignRepository,
    canonical_payload_hash,
)
from schemas.design_migrations import migrate_design_payload_to_v2


def migrate_design_directory(
    source_dir: str | Path,
    database_path: str | Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    source = JsonRepository(source_dir)
    repository = None if dry_run else SqliteDesignRepository(database_path)
    report: dict[str, Any] = {
        "dry_run": dry_run,
        "source_dir": str(Path(source_dir).resolve()),
        "database_path": str(Path(database_path).resolve()),
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
        "records": [],
    }
    for payload in source.list():
        design_id = str(payload.get("design_id") or "").strip()
        record = {"design_id": design_id, "status": "pending"}
        try:
            if not design_id:
                raise ValueError("The source record does not contain design_id.")
            migration = migrate_design_payload_to_v2(payload)
            target_payload = migration.design.to_dict()
            if repository and repository.exists(design_id):
                record["status"] = "skipped"
                report["skipped"] += 1
            elif repository:
                stored = repository.save(design_id, target_payload)
                repository.record_payload_migration(
                    source_id=design_id,
                    source_version=migration.source_version,
                    target_version=migration.target_version,
                    source_hash=canonical_payload_hash(payload),
                    result_hash=canonical_payload_hash(stored),
                    status="completed",
                    report=migration.to_dict(),
                )
                record["status"] = "migrated"
                report["migrated"] += 1
            else:
                record["status"] = "would_migrate"
                report["migrated"] += 1
            record["warnings"] = migration.warnings
            record["assumptions"] = migration.assumptions
        except (OSError, TypeError, ValueError) as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            report["failed"] += 1
        report["records"].append(record)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate DesignIR v1 JSON records into the v1.6 SQLite store."
    )
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("database_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = migrate_design_directory(
        args.source_dir,
        args.database_path,
        dry_run=args.dry_run,
    )
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
