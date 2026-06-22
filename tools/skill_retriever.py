from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_SKILL_LIBRARY_PATH = "邏輯設計skill.json"
DEFAULT_EXTRACTED_SKILLS_PATH = "outputs/extracted_skills.jsonl"


@dataclass
class SkillRetriever:
    skills: list[dict[str, Any]] = field(default_factory=list)
    core_skills: list[dict[str, Any]] = field(default_factory=list)
    memory_skills: list[dict[str, Any]] = field(default_factory=list)
    min_confidence: float = 0.5
    tag_hops: int = 1

    def __post_init__(self) -> None:
        if self.core_skills or self.memory_skills:
            self.skills = [*self.core_skills, *self.memory_skills]
        elif self.skills:
            self.memory_skills = self.skills

    @classmethod
    def from_json_file(
        cls,
        path: str | Path = DEFAULT_SKILL_LIBRARY_PATH,
        min_confidence: float = 0.5,
        include_extracted: bool = False,
        extracted_path: str | Path = DEFAULT_EXTRACTED_SKILLS_PATH,
    ) -> "SkillRetriever":
        skill_path = Path(path)
        if not skill_path.exists() and not skill_path.is_absolute():
            repo_relative_path = Path(__file__).resolve().parents[1] / skill_path
            if repo_relative_path.exists():
                skill_path = repo_relative_path
        data = json.loads(skill_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Skill library must be a JSON list: {skill_path}")
        core_skills = [_normalize_skill(record) for record in data if isinstance(record, dict)]
        memory_skills: list[dict[str, Any]] = []
        if include_extracted:
            memory_skills.extend(_load_extracted_skills(extracted_path))
        return cls(core_skills=core_skills, memory_skills=memory_skills, min_confidence=min_confidence)

    def retrieve_skills(self, query: str, mode: str = "Exploration", k: int = 5) -> str:
        sections: list[str] = []
        if self.core_skills:
            sections.append(_format_core_skill_catalog(self.core_skills))

        query_terms = _tokenize(query)
        if not query_terms:
            return "\n\n".join(sections)
        search_pool = self.memory_skills if self.core_skills else self.skills
        retrieved = _retrieve_ranked_skills(
            search_pool,
            query_terms=query_terms,
            mode=mode,
            k=k,
            min_confidence=self.min_confidence,
            tag_hops=self.tag_hops,
        )
        if retrieved:
            sections.append(retrieved)
        return "\n\n".join(sections)


def _retrieve_ranked_skills(
    skills: list[dict[str, Any]],
    query_terms: set[str],
    mode: str,
    k: int,
    min_confidence: float,
    tag_hops: int,
) -> str:
    if not skills:
        return ""
    tag_index = _build_tag_index(skills)
    backlink_index = _build_backlink_index(skills)
    positive_ranked: list[tuple[float, dict[str, Any]]] = []
    avoid_ranked: list[tuple[float, dict[str, Any]]] = []
    for skill in skills:
        confidence = float(skill.get("confidence_score", 1.0))
        if confidence < min_confidence:
            continue
        text = _searchable_text(skill)
        overlap = len(query_terms.intersection(_tokenize(text)))
        mode_bonus = _mode_bonus(skill, mode)
        graph_bonus = _graph_bonus(skill, query_terms, tag_index, backlink_index, tag_hops)
        recency_bonus = float(skill.get("recency_score", 0.0)) * 0.15
        relevance = overlap + graph_bonus
        if relevance <= 0:
            continue
        score = relevance + confidence + mode_bonus + recency_bonus
        if _is_negative_memory(skill):
            avoid_ranked.append((score, skill))
        else:
            positive_ranked.append((score, skill))
    positive_ranked.sort(key=lambda item: item[0], reverse=True)
    avoid_ranked.sort(key=lambda item: item[0], reverse=True)

    sections: list[str] = []
    positive_snippets = [_format_skill_snippet(skill) for _, skill in positive_ranked[:k]]
    if positive_snippets:
        sections.append("Reusable successful patterns:\n" + "\n\n".join(positive_snippets))
    if mode.lower() in {"repair", "exploitation"}:
        avoid_limit = max(1, min(2, k // 2 or 1))
        avoid_snippets = [_format_skill_snippet(skill) for _, skill in avoid_ranked[:avoid_limit]]
        if avoid_snippets:
            sections.append("Patterns to avoid or repair:\n" + "\n\n".join(avoid_snippets))
    return "\n\n".join(sections)


def _format_core_skill_catalog(skills: list[dict[str, Any]]) -> str:
    lines = [
        "Canonical logic skill catalog (always available; use as authoritative design constraints):",
        "- Prefer NOT/NOR/OR for simple Cello-compatible combinational designs.",
        "- Treat XOR/XNOR as high-burden motifs; warn or simplify when possible.",
        "- Do not use cyclic, sequential, oscillator, pulse, or filter motifs unless explicitly requested.",
    ]
    for skill in skills:
        title = str(skill.get("title") or skill.get("skill_name") or "Unnamed skill")
        category = str(skill.get("category") or "unknown")
        boolean_template = str(skill.get("boolean_template") or "N/A")
        depth = skill.get("logic_depth", "N/A")
        repressor_cost = skill.get("estimated_repressor_cost", "N/A")
        cyclic = "yes" if bool(skill.get("is_cyclic", False)) else "no"
        purpose = _compact_text(skill.get("purpose_en") or skill.get("purpose") or "")
        tradeoffs = _compact_text(skill.get("trade_offs") or "")
        risks = _compact_text(skill.get("known_risks") or "")
        detail_parts = [
            f"category={category}",
            f"Boolean template={boolean_template}",
            f"depth={depth}",
            f"repressors={repressor_cost}",
            f"cyclic={cyclic}",
        ]
        if purpose:
            detail_parts.append(f"use={purpose}")
        if tradeoffs:
            detail_parts.append(f"tradeoffs={tradeoffs}")
        if risks:
            detail_parts.append(f"risks={risks}")
        lines.append(f"- {title}: " + "; ".join(detail_parts))
    return "\n".join(lines)


def _compact_text(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _normalize_skill(record: dict[str, Any]) -> dict[str, Any]:
    title = str(record.get("title") or record.get("skill_name") or record.get("motif_name") or "Unnamed skill")
    category = str(record.get("category") or "")
    boolean_template = str(record.get("boolean_template") or "")
    decomposition = str(record.get("decomposition_strategy") or "")
    risks = str(record.get("known_risks") or "")
    tradeoffs = str(record.get("trade_offs") or "")
    purpose = str(record.get("purpose") or record.get("summary") or "")
    tags = _normalize_tags(record.get("tags", [])) + [title, category, boolean_template]
    if record.get("summary") and not any([record.get("skill_name"), record.get("motif_name"), category, boolean_template]):
        summary = str(record["summary"])
    else:
        summary = (
            f"Motif: {title}\n"
            f"Category: {category}\n"
            f"Boolean template: {boolean_template}\n"
            f"Decomposition strategy: {decomposition}\n"
            f"Trade-offs: {tradeoffs}\n"
            f"Known risks: {risks}"
        )
    search_text = " ".join(
        [title, category, purpose, boolean_template, decomposition, tradeoffs, risks, str(record.get("search_text", ""))]
    )
    return {
        **record,
        "title": title,
        "summary": summary,
        "tags": [tag for tag in tags if tag],
        "search_text": search_text,
        "confidence_score": float(record.get("confidence_score", 1.0)),
        "backlinks": record.get("backlinks", []),
    }


def _format_skill_snippet(skill: dict[str, Any]) -> str:
    title = str(skill.get("title") or "")
    summary = str(skill.get("summary") or "")
    if title and summary and title not in summary:
        return f"Skill: {title}\n{summary}"
    return summary or title or str(skill)


def _searchable_text(skill: dict[str, Any]) -> str:
    return " ".join(
        str(skill.get(key, ""))
        for key in ("title", "summary", "tags", "search_text", "backlinks", "source_node")
    ).lower()


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[\w+-]+", str(text).lower()) if token}


def _normalize_tags(tags: Any) -> list[str]:
    if isinstance(tags, str):
        return [tags]
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    return []


def _build_tag_index(skills: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for skill in skills:
        for tag in _normalize_tags(skill.get("tags", [])):
            index.setdefault(tag.lower(), []).append(skill)
    return index


def _build_backlink_index(skills: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for skill in skills:
        title = str(skill.get("title", "")).lower()
        source = str(skill.get("source_node", "")).lower()
        for key in (title, source):
            if key:
                index.setdefault(key, []).append(skill)
    return index


def _graph_bonus(
    skill: dict[str, Any],
    query_terms: set[str],
    tag_index: dict[str, list[dict[str, Any]]],
    backlink_index: dict[str, list[dict[str, Any]]],
    tag_hops: int,
) -> float:
    bonus = 0.0
    seen_titles = {str(skill.get("title", "")).lower()}
    frontier = [tag.lower() for tag in _normalize_tags(skill.get("tags", []))]
    for _ in range(max(0, tag_hops)):
        next_frontier: list[str] = []
        for tag in frontier:
            related = tag_index.get(tag, [])
            for neighbor in related:
                title = str(neighbor.get("title", "")).lower()
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                text = _searchable_text(neighbor)
                if query_terms.intersection(_tokenize(text)):
                    bonus += 0.15 * float(neighbor.get("confidence_score", 1.0))
                next_frontier.extend(t.lower() for t in _normalize_tags(neighbor.get("tags", [])))
        frontier = next_frontier

    for backlink in _normalize_tags(skill.get("backlinks", [])):
        key = backlink.strip("[]").lower()
        for neighbor in backlink_index.get(key, []):
            text = _searchable_text(neighbor)
            if query_terms.intersection(_tokenize(text)):
                bonus += 0.1 * float(neighbor.get("confidence_score", 1.0))
    return min(bonus, 1.0)


def _mode_bonus(skill: dict[str, Any], mode: str) -> float:
    text = _searchable_text(skill)
    normalized_mode = mode.lower()
    if normalized_mode in text:
        return 0.3
    if normalized_mode == "repair" and any(token in text for token in ("failure", "logic-error", "recovery")):
        return 0.25
    if normalized_mode == "exploitation" and any(token in text for token in ("part-error", "mapping", "ode", "physical")):
        return 0.25
    if normalized_mode == "exploration" and any(token in text for token in ("motif", "success", "template")):
        return 0.2
    return 0.0


def _is_negative_memory(skill: dict[str, Any]) -> bool:
    if str(skill.get("memory_kind", "")).lower() in {"avoid", "failure", "negative"}:
        return True
    text = _searchable_text(skill)
    return any(token in text for token in ("dead_end", "dead-end", "avoid", "failure/", "status/dead"))


def _load_extracted_skills(path: str | Path) -> list[dict[str, Any]]:
    memory_path = Path(path)
    if not memory_path.exists() and not memory_path.is_absolute():
        repo_relative_path = Path(__file__).resolve().parents[1] / memory_path
        if repo_relative_path.exists():
            memory_path = repo_relative_path
    if not memory_path.exists():
        return []

    skills: list[dict[str, Any]] = []
    for line in memory_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            skills.append(_normalize_skill(record))
    return skills
