from __future__ import annotations


def format_skill_card(skill: dict) -> str:
    title = skill.get("title", "Untitled design skill")
    confidence = skill.get("confidence_score", 0.0)
    summary = skill.get("summary", "")
    tags = skill.get("tags", [])
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    return (
        "---\n"
        f"confidence_score: {confidence}\n"
        "tags:\n"
        f"{tag_lines}\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{summary}\n"
    )
