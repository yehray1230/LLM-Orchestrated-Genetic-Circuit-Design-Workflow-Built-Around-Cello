from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def is_successfully_mapped(topology: dict[str, Any] | None) -> bool:
    if not topology:
        return False
    return (
        str(topology.get("cello_mode") or "").lower() == "external"
        and str(topology.get("mapping_status") or "").lower() == "mapped"
        and str(topology.get("cello_claim_level") or "").lower() == "externally_mapped"
        and topology.get("cello_buildable") is True
    )


def topology_selection_key(topology: dict[str, Any] | None) -> tuple[int, float]:
    """Rank verified external mappings before ordinary score comparisons."""
    if not topology:
        return (0, -9999.0)
    try:
        score = float(topology.get("score", -9999.0))
    except (TypeError, ValueError):
        score = -9999.0
    return (1 if is_successfully_mapped(topology) else 0, score)


def select_best_topology(
    topologies: Iterable[dict[str, Any]],
) -> dict[str, Any] | None:
    return max(topologies, key=topology_selection_key, default=None)
