from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RecordRepository(Protocol):
    def save(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, record_id: str) -> dict[str, Any] | None: ...

    def list(self) -> list[dict[str, Any]]: ...

    def exists(self, record_id: str) -> bool: ...


@runtime_checkable
class RevisionRepository(RecordRepository, Protocol):
    def list_revisions(self, record_id: str) -> list[dict[str, Any]]: ...

    def get_revision(
        self,
        record_id: str,
        revision_number: int,
    ) -> dict[str, Any] | None: ...
