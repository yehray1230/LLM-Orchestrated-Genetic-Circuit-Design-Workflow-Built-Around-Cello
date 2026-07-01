from __future__ import annotations

from dataclasses import replace

import pytest

from benchmark_suite.design_task_dataset import (
    CANONICAL_EXP003_CATEGORIES,
    load_design_task_set,
    validate_exp003_task_set,
)


def test_exp003_task_set_has_exactly_five_canonical_categories() -> None:
    task_set = load_design_task_set("exp003_design_tasks_v1")

    assert len(task_set.tasks) == 5
    assert {task.category for task in task_set.tasks} == set(
        CANONICAL_EXP003_CATEGORIES
    )
    assert validate_exp003_task_set(task_set) == []
    assert len(task_set.content_hash) == 64
    assert task_set.content_hash == load_design_task_set(
        "exp003_design_tasks_v1"
    ).content_hash


def test_exp003_tasks_express_logic_temporal_and_clarification_expectations() -> None:
    task_set = load_design_task_set("exp003_design_tasks_v1")

    cello = task_set.task("cello_a_and_not_b_gfp_v1")
    toggle = task_set.task("toggle_set_reset_v1")
    oscillator = task_set.task("oscillator_repressilator_v1")
    ambiguous = task_set.task("ambiguous_stress_output_v1")

    assert cello.expected["truth_table"][2] == {"A": 1, "B": 0, "GFP": 1}
    assert toggle.expected["evaluation_mode"] == "stateful_temporal"
    assert oscillator.expected["evaluation_mode"] == "oscillatory_temporal"
    assert ambiguous.expected["candidate_generation_allowed"] is False
    assert len(ambiguous.expected["required_clarifications"]) == 3


def test_exp003_validation_rejects_missing_or_duplicate_categories() -> None:
    task_set = load_design_task_set("exp003_design_tasks_v1")
    duplicated_tasks = [*task_set.tasks[:-1], task_set.tasks[0]]
    invalid = replace(task_set, tasks=duplicated_tasks)

    errors = validate_exp003_task_set(invalid)

    assert any("Duplicate task IDs" in error for error in errors)
    assert any("Missing EXP-003 categories: ambiguous" in error for error in errors)
    assert any("Duplicate EXP-003 categories: reporter" in error for error in errors)


def test_design_task_loader_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Invalid design task-set ID"):
        load_design_task_set("../exp003_design_tasks_v1")
