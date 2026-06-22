from __future__ import annotations

from catalog.agent_catalog import load_agent_catalog
from catalog.workflow_kit_catalog import build_workflow_kit_registry, load_workflow_kit_catalog


def test_workflow_kit_catalog_loads_logic_design_basic() -> None:
    kits = load_workflow_kit_catalog()

    assert len(kits) == 1
    kit = kits[0]
    assert kit.id == "logic-design-basic"
    assert kit.schema_version == "workflow-kit-v1"
    assert kit.entrypoint == "workflows.reflexion_controller.run_reflexion_workflow"
    assert kit.requires_expert_review is True
    assert kit.claim_level == "computational_candidate"
    assert len(kit.stages) >= 8


def test_workflow_kit_references_registered_agents() -> None:
    agent_ids = {entry.id for entry in load_agent_catalog()}

    for kit in load_workflow_kit_catalog():
        assert set(kit.agents).issubset(agent_ids)
        stage_agents = {stage.agent for stage in kit.stages if stage.agent}
        assert stage_agents.issubset(set(kit.agents))


def test_workflow_kit_registry_is_ui_ready() -> None:
    registry = build_workflow_kit_registry()

    assert registry["schema_version"] == "workflow-kit-registry-v1"
    assert registry["kit_count"] == 1
    kit = registry["workflow_kits"][0]
    assert kit["id"] == "logic-design-basic"
    assert "sample_prompts" in kit
    assert "stages" in kit
