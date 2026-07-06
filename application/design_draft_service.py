from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from repositories.json_repository import JsonRepository
from schemas.design_draft import DesignDraft


class DesignDraftService:
    def __init__(self, repository: JsonRepository):
        self.repository = repository

    def get_active(self) -> dict[str, Any] | None:
        """
        Retrieves the active design draft from the repository.
        """
        try:
            draft_dict = self.repository.get("active_draft")
            if draft_dict:
                return DesignDraft.from_dict(draft_dict).to_dict()
            return None
        except Exception:
            return None

    def save(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Saves or updates the active design draft.
        """
        existing_draft = self.get_active()
        merged = {}
        if existing_draft:
            merged.update(existing_draft)
        merged.update(data)

        # Convert to DesignDraft to apply defaults and filter keys
        draft = DesignDraft.from_dict(merged)
        draft.last_saved = datetime.now(timezone.utc).isoformat()
        
        saved_dict = draft.to_dict()
        self.repository.save("active_draft", saved_dict)
        return saved_dict

    def clear(self) -> None:
        """
        Clears the active draft (e.g., after starting a design run).
        """
        try:
            self.repository.delete("active_draft")
        except Exception:
            pass
