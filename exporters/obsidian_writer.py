from __future__ import annotations

from pathlib import Path
import re

from exporters.obsidian_skill_formatter import format_skill_card


def write_skill_card(skill: dict, vault_dir: str | Path) -> Path:
    vault_path = Path(vault_dir)
    vault_path.mkdir(parents=True, exist_ok=True)
    title = str(skill.get("title", "untitled-skill"))
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", title).strip("-").lower() or "untitled-skill"
    output_path = vault_path / f"{slug}.md"
    source_node = str(skill.get("source_node") or "").strip()
    if output_path.exists() and source_node:
        output_path = vault_path / f"{slug}-{source_node}.md"
    output_path.write_text(format_skill_card(skill), encoding="utf-8")
    return output_path
