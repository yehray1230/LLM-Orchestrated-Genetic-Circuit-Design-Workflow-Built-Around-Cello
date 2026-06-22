"""Persistence adapters for application services."""

from repositories.json_repository import JsonRepository, RepositoryError
from repositories.protocols import RecordRepository, RevisionRepository
from repositories.factory import create_design_repository, repository_backend
from repositories.postgres_repository import (
    POSTGRES_SCHEMA_VERSION,
    PostgresDesignRepository,
)
from repositories.sqlite_repository import (
    DATABASE_SCHEMA_VERSION,
    SqliteDesignRepository,
    canonical_payload_hash,
)

__all__ = [
    "DATABASE_SCHEMA_VERSION",
    "JsonRepository",
    "RecordRepository",
    "RepositoryError",
    "RevisionRepository",
    "SqliteDesignRepository",
    "POSTGRES_SCHEMA_VERSION",
    "PostgresDesignRepository",
    "create_design_repository",
    "repository_backend",
    "canonical_payload_hash",
]
