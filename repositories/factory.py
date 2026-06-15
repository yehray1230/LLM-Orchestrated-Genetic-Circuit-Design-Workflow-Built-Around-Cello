from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from repositories.postgres_repository import PostgresDesignRepository
from repositories.sqlite_repository import SqliteDesignRepository


def create_design_repository(
    sqlite_path: str | Path,
    database_url: str | None = None,
) -> Any:
    selected_url = (
        database_url
        if database_url is not None
        else os.getenv("GENETIC_CIRCUIT_DATABASE_URL")
    )
    if selected_url and selected_url.startswith(("postgresql://", "postgres://")):
        return PostgresDesignRepository(selected_url)
    return SqliteDesignRepository(sqlite_path)


def repository_backend(repository: Any) -> str:
    if isinstance(repository, PostgresDesignRepository):
        return "postgresql"
    if isinstance(repository, SqliteDesignRepository):
        return "sqlite"
    return repository.__class__.__name__
