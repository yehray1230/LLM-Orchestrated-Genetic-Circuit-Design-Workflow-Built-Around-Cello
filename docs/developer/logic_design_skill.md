# Logic Design Skill Maintenance Guide

This project keeps the runtime skill library in `邏輯設計skill.json`.

Use JSON as the source of truth for application behavior because `SkillRetriever` parses fields directly and builds the prompt context from structured values. Use this Markdown file as the human maintenance guide for adding or editing entries.

## Runtime Contract

- Keep `邏輯設計skill.json` valid UTF-8 JSON.
- Keep it as a top-level JSON list of objects.
- Add new stable design knowledge to this file when Builder or Translator should always see it in the canonical logic skill catalog.
- Add workflow-derived memories to `outputs/extracted_skills.jsonl`; those are query-ranked separately and should not be copied into the canonical file unless they become general policy.
- Keep `motif_name` for backward compatibility. Use `skill_name` as the canonical identifier for new entries.

## Required Fields

Every canonical entry should include:

- `skill_name`: stable uppercase identifier, such as `NOR_GATE` or `DESIGN_REPAIR_PLAYBOOK`.
- `motif_name`: backward-compatible alias; for non-motif skills, set it equal to `skill_name`.
- `category`: one of the established categories or a deliberate new category.
- `tags`: short searchable tags.
- `memory_kind`: usually `success` for canonical guidance.
- `confidence_score`: usually `1.0` for curated entries.
- `purpose`: concise Chinese purpose.
- `purpose_en`: concise English purpose.
- `boolean_template`: Boolean expression, policy summary, or repair summary.
- `decomposition_strategy`: how an agent should translate the skill into design action.
- `trade_offs`: important benefits and costs.
- `known_risks`: failure modes or misuse risks.
- `application_scenarios`: at least one concrete scenario with keywords and a user-intent example.

## Motif Fields

Use these fields for biological or logic motifs:

- `is_cyclic`: true for feedback, memory, or oscillator motifs.
- `logic_depth`: integer depth for combinational motifs; use `-1` for feedback/dynamic motifs where static depth is misleading.
- `estimated_repressor_cost`: approximate repressor burden.
- `cost_description`: short implementation cost.
- `truth_table`: representative truth table or dynamic-state rows.
- `verilog_template`: Cello-compatible template when possible. If the motif is dynamic or not directly Cello-mappable, keep the template illustrative and explain the limitation in `known_risks`.

## Policy Fields

Use these fields for design rules such as `CELLO_COMPATIBILITY_POLICY`:

- `allowed_verilog_constructs`: constructs the Translator may emit.
- `forbidden_verilog_constructs`: constructs that should trigger repair or rejection.
- `preferred_design_rules`: concise rules the Builder and Translator should follow.

Policy entries should have `logic_depth: 0`, `estimated_repressor_cost: 0`, and `truth_table: []`.

## Repair Playbook Fields

Use these fields for repair guidance such as `DESIGN_REPAIR_PLAYBOOK`:

- `repair_rules`: list of objects with `failure_type` and `action`.

Repair entries should map Critic, Benchmark, or Cello-wrapper failures to minimal corrective rewrites. They should not introduce new biological claims unless those claims are already supported by motif or policy entries.

## Requirement Analysis Fields

Use these fields for PM elicitation guidance such as `REQUIREMENT_ANALYSIS_PLAYBOOK`:

- `required_spec_fields`: fields that must be completed before Builder can reliably act.
- `optional_spec_fields`: constraints to preserve when explicitly stated, but not invent as defaults.
- `elicitation_rules`: concise rules for turning natural language into structured spec fields or clarification prompts.

Requirement-analysis entries should help PM Agent separate explicit user intent from safe defaults. They should not make optional timing, memory, safety, or payload constraints mandatory unless the product flow intentionally changes.

## Prompt Formatting Notes

`SkillRetriever` currently includes these fields in the compact canonical catalog:

- `title`, derived from `title`, `skill_name`, or `motif_name`
- `category`
- `boolean_template`
- `logic_depth`
- `estimated_repressor_cost`
- `is_cyclic`
- `purpose_en` or `purpose`
- `trade_offs`
- `known_risks`

Fields such as `truth_table`, `verilog_template`, `allowed_verilog_constructs`, `repair_rules`, and `elicitation_rules` remain available in JSON for future formatters and tests, but are not fully expanded in the compact catalog today.

## Editing Checklist

1. Edit `邏輯設計skill.json`.
2. Validate JSON loading.
3. Run `SkillRetriever.from_json_file()` and confirm the new entry appears in the canonical logic skill catalog.
4. Update tests when the canonical count changes.
5. Keep this guide current if new entry types or fields are introduced.
