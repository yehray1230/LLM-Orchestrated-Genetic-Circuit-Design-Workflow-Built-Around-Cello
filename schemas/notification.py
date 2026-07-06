from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Notification:
    notification_id: str
    category: str  # "info", "warning", "success", "error"
    title: str
    message: str
    read: bool
    timestamp: str
    link: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Notification:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)
