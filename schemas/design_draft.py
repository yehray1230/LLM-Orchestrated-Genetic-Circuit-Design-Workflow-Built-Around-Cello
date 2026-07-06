from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class DesignDraft:
    draft_id: str = field(default_factory=lambda: f"draft_{uuid4().hex[:12]}")
    current_step: int = 1
    user_intent: str = ""
    host_organism: str = "Escherichia coli"
    compute_budget: int = 6
    enable_rag: bool = True
    enable_ode: bool = True
    enable_skill_extraction: bool = True
    model_name: str = ""
    api_base: str = ""
    last_saved: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    structured_spec: dict[str, Any] = field(default_factory=dict)
    pm_chat_history: list[dict[str, str]] = field(default_factory=list)
    pending_proposal: dict[str, Any] = field(default_factory=dict)
    pm_stage: str = "elicitation"

    @classmethod
    def empty(cls) -> DesignDraft:
        return cls(
            draft_id=f"draft_{uuid4().hex[:12]}",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DesignDraft:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        # Ensure default values are populated if keys are missing
        return cls(**filtered)
