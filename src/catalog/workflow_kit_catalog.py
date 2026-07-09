from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from catalog.agent_catalog import DEFAULT_CATALOG_ROOT, load_agent_catalog


WORKFLOW_KIT_SCHEMA_VERSION = "workflow-kit-v1"
DEFAULT_WORKFLOW_KIT_ROOT = (
    Path("src/catalog/workflow-kits")
    if Path("src/catalog/workflow-kits").exists()
    else Path("catalog/workflow-kits")
)
VALID_CLAIM_LEVELS = {
    "planning_only",
    "computational_candidate",
    "cello_compatible_candidate",
    "simulation_screening",
    "workflow_memory",
}
REQUIRED_FIELDS = {
    "id",
    "name",
    "schema_version",
    "version",
    "summary",
    "entrypoint",
    "agents",
    "stages",
    "inputs",
    "outputs",
    "claim_level",
    "requires_expert_review",
}


class WorkflowKitCatalogError(ValueError):
    """Raised when a workflow kit catalog entry is malformed."""


@dataclass(frozen=True)
class WorkflowStage:
    id: str
    name: str
    agent: str | None = None
    tool: str | None = None
    optional: bool = False
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowKitMetadata:
    id: str
    name: str
    schema_version: str
    version: str
    summary: str
    entrypoint: str
    agents: list[str]
    stages: list[WorkflowStage]
    inputs: list[str]
    outputs: list[str]
    tools: list[str] = field(default_factory=list)
    sample_prompts: list[str] = field(default_factory=list)
    default_settings: dict[str, Any] = field(default_factory=dict)
    claim_level: str = "computational_candidate"
    requires_expert_review: bool = True
    risk_notes: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stages"] = [stage.to_dict() for stage in self.stages]
        return payload


def load_workflow_kit_catalog(
    root: str | Path = DEFAULT_WORKFLOW_KIT_ROOT,
    *,
    agent_catalog_root: str | Path = DEFAULT_CATALOG_ROOT,
) -> list[WorkflowKitMetadata]:
    root_path = Path(root)
    if not root_path.exists():
        return []

    agent_ids = {entry.id for entry in load_agent_catalog(agent_catalog_root)}
    entries: list[WorkflowKitMetadata] = []
    for kit_path in sorted(root_path.glob("*/kit.json")):
        payload = json.loads(kit_path.read_text(encoding="utf-8"))
        entries.append(
            validate_workflow_kit_metadata(
                payload,
                known_agent_ids=agent_ids,
                metadata_path=kit_path,
            )
        )

    ids = [entry.id for entry in entries]
    duplicates = sorted({kit_id for kit_id in ids if ids.count(kit_id) > 1})
    if duplicates:
        raise WorkflowKitCatalogError(
            f"Duplicate workflow kit ids: {', '.join(duplicates)}"
        )
    return entries


def build_workflow_kit_registry(
    root: str | Path = DEFAULT_WORKFLOW_KIT_ROOT,
    *,
    agent_catalog_root: str | Path = DEFAULT_CATALOG_ROOT,
) -> dict[str, Any]:
    entries = load_workflow_kit_catalog(
        root,
        agent_catalog_root=agent_catalog_root,
    )
    return {
        "schema_version": "workflow-kit-registry-v1",
        "kit_count": len(entries),
        "workflow_kits": [entry.to_dict() for entry in entries],
    }


def validate_workflow_kit_metadata(
    payload: dict[str, Any],
    *,
    known_agent_ids: set[str],
    metadata_path: str | Path | None = None,
) -> WorkflowKitMetadata:
    missing = sorted(REQUIRED_FIELDS - set(payload))
    if missing:
        raise WorkflowKitCatalogError(
            f"{_label(metadata_path)} missing required fields: {', '.join(missing)}"
        )
    if payload["schema_version"] != WORKFLOW_KIT_SCHEMA_VERSION:
        raise WorkflowKitCatalogError(
            f"{_label(metadata_path)} unsupported schema_version: "
            f"{payload['schema_version']!r}"
        )

    agents = _require_string_list(payload["agents"], "agents", metadata_path)
    unknown_agents = sorted(set(agents) - known_agent_ids)
    if unknown_agents:
        raise WorkflowKitCatalogError(
            f"{_label(metadata_path)} references unknown agents: "
            f"{', '.join(unknown_agents)}"
        )

    stages = _parse_stages(payload["stages"], agents, metadata_path)
    claim_level = str(payload["claim_level"])
    if claim_level not in VALID_CLAIM_LEVELS:
        raise WorkflowKitCatalogError(
            f"{_label(metadata_path)} invalid claim_level: {claim_level!r}"
        )

    return WorkflowKitMetadata(
        id=str(payload["id"]),
        name=str(payload["name"]),
        schema_version=str(payload["schema_version"]),
        version=str(payload["version"]),
        summary=str(payload["summary"]),
        entrypoint=str(payload["entrypoint"]),
        agents=agents,
        stages=stages,
        inputs=_require_string_list(payload["inputs"], "inputs", metadata_path),
        outputs=_require_string_list(payload["outputs"], "outputs", metadata_path),
        tools=_optional_string_list(payload, "tools", metadata_path),
        sample_prompts=_optional_string_list(payload, "sample_prompts", metadata_path),
        default_settings=dict(payload.get("default_settings", {})),
        claim_level=claim_level,
        requires_expert_review=_as_bool(payload["requires_expert_review"]),
        risk_notes=_optional_string_list(payload, "risk_notes", metadata_path),
        success_criteria=_optional_string_list(payload, "success_criteria", metadata_path),
        tags=_optional_string_list(payload, "tags", metadata_path),
        source_path=_source_path(metadata_path),
    )


def _parse_stages(
    value: Any,
    agents: list[str],
    metadata_path: str | Path | None,
) -> list[WorkflowStage]:
    if not isinstance(value, list) or not value:
        raise WorkflowKitCatalogError(f"{_label(metadata_path)} stages must be a non-empty list")
    stages: list[WorkflowStage] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkflowKitCatalogError(
                f"{_label(metadata_path)} stages[{index}] must be an object"
            )
        stage_id = str(item.get("id") or "")
        name = str(item.get("name") or "")
        if not stage_id or not name:
            raise WorkflowKitCatalogError(
                f"{_label(metadata_path)} stages[{index}] requires id and name"
            )
        agent = item.get("agent")
        tool = item.get("tool")
        if agent is not None and str(agent) not in agents:
            raise WorkflowKitCatalogError(
                f"{_label(metadata_path)} stage {stage_id!r} references agent "
                f"{agent!r} that is not declared by the kit"
            )
        if agent is None and tool is None:
            raise WorkflowKitCatalogError(
                f"{_label(metadata_path)} stage {stage_id!r} must reference an agent or tool"
            )
        stages.append(
            WorkflowStage(
                id=stage_id,
                name=name,
                agent=str(agent) if agent is not None else None,
                tool=str(tool) if tool is not None else None,
                optional=_as_bool(item.get("optional", False)),
                summary=str(item.get("summary", "")),
            )
        )
    return stages


def _require_string_list(
    value: Any,
    field_name: str,
    metadata_path: str | Path | None,
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkflowKitCatalogError(
            f"{_label(metadata_path)} {field_name} must be a list of strings"
        )
    return list(value)


def _optional_string_list(
    payload: dict[str, Any],
    field_name: str,
    metadata_path: str | Path | None,
) -> list[str]:
    if field_name not in payload:
        return []
    return _require_string_list(payload[field_name], field_name, metadata_path)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    raise WorkflowKitCatalogError(f"Expected boolean value, got {value!r}")


def _label(path: str | Path | None) -> str:
    return str(path) if path else "workflow kit metadata"


def _source_path(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return Path(path).as_posix()
