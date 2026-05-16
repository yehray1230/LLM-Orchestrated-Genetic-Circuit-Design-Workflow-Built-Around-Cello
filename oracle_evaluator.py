from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from schemas.state import DesignState


def evaluate_truth_table(expected: list[int], observed: list[int]) -> dict:
    total = max(len(expected), 1)
    matches = sum(1 for left, right in zip(expected, observed) if left == right)
    return {"accuracy": matches / total, "matches": matches, "total": total}


def export_best_verilog(state: DesignState, output_dir: str | Path = "artifacts/verilog") -> dict[str, Any]:
    topology, node_id = _select_export_topology(state)
    if not topology:
        return {"ok": False, "path": None, "module_name": None, "error": "No topology with Verilog was available."}

    verilog = str(topology.get("verilog") or "")
    if not verilog.strip():
        return {"ok": False, "path": None, "module_name": None, "error": "Selected topology does not contain Verilog."}

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    module_name = _extract_module_name(verilog) or _safe_name(state.user_intent or node_id or "genetic_circuit")
    filename = f"{_safe_name(module_name)}.v"
    target = output_path / filename
    target.write_text(_normalize_verilog(verilog), encoding="utf-8")
    topology["verilog_export_path"] = str(target)
    return {"ok": True, "path": str(target), "module_name": module_name, "error": None}


def _select_export_topology(state: DesignState) -> tuple[dict[str, Any] | None, str | None]:
    candidates: list[tuple[float, dict[str, Any], str | None]] = []
    if state.best_topology and state.best_topology.get("verilog"):
        candidates.append((float(state.best_topology.get("score", 0.0)), state.best_topology, state.current_node_id))
    if state.current_node_id and state.current_node_id in state.tree_nodes:
        node = state.tree_nodes[state.current_node_id]
        for topology in node.candidate_topologies:
            if topology.get("verilog"):
                bonus = 1.0 if node.is_approved else 0.0
                candidates.append((bonus + float(topology.get("score", 0.0)), topology, node.node_id))
    for node in state.tree_nodes.values():
        for topology in node.candidate_topologies:
            if topology.get("verilog"):
                bonus = 1.0 if node.is_approved else 0.0
                candidates.append((bonus + float(topology.get("score", 0.0)), topology, node.node_id))
    if not candidates:
        return None, None
    _, topology, node_id = max(candidates, key=lambda item: item[0])
    return topology, node_id


def _extract_module_name(verilog: str) -> str | None:
    match = re.search(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)", verilog)
    return match.group(1) if match else None


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    if not safe:
        safe = "genetic_circuit"
    if safe[0].isdigit():
        safe = f"circuit_{safe}"
    return safe[:80]


def _normalize_verilog(verilog: str) -> str:
    text = verilog.strip()
    return text if text.endswith("\n") else f"{text}\n"
