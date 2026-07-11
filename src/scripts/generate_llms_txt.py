from __future__ import annotations

from pathlib import Path

# Ordered list of documents to concatenate for the full context file
DOCUMENTS = [
    "about.md",
    "limitations.md",
    "architecture.md",
    "workflow.md",
    "model_assumptions.md",
    "evaluation_metrics.md",
    "future_roadmap.md",
    "ai_reviewer_guide.md",
    "audiences/synthetic_biology.md",
    "audiences/mathematical_modeling.md",
    "audiences/ai4science_agents.md",
    "audiences/bio_cad_interoperability.md",
    "audiences/potential_collaborators.md",
]


def _normalize_generated_text(text: str) -> str:
    """Keep the generated aggregate stable for CI diff and whitespace checks."""
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(line.rstrip() for line in lines) + "\n"


def main() -> None:
    # Resolve paths relative to the script location
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent
    docs_dir = workspace_root / "docs"
    output_file = workspace_root / "llms-full.txt"

    print(f"Generating aggregated context file at: {output_file.relative_to(workspace_root)}")

    combined_content = []
    combined_content.append("# Evidence-Aware Genetic Circuit Design Research Prototype - Complete Documentation\n")
    combined_content.append("This generated file aggregates the core claim boundaries, methods, roadmap, and audience guides for AI reviewers that need full repository context. Use llms.txt for shorter audience-aware routing.\n\n")

    for filename in DOCUMENTS:
        filepath = docs_dir / filename
        if not filepath.exists():
            print(f"Warning: Expected document {filename} not found at {filepath}")
            continue

        print(f"  Reading {filename}...")
        file_content = filepath.read_text(encoding="utf-8")

        # Clean relative markdown links from root-relative docs path to local doc path (since they are merged)
        # For example, [limitations.md](limitations.md) is fine.
        # We add separator headers
        combined_content.append("\n" + "=" * 80 + "\n")
        combined_content.append(f"## DOCUMENT: docs/{filename}\n")
        combined_content.append("=" * 80 + "\n\n")
        combined_content.append(file_content)
        combined_content.append("\n")

    output_file.write_text(
        _normalize_generated_text("".join(combined_content)),
        encoding="utf-8",
    )
    print("Generation complete!")

if __name__ == "__main__":
    main()
