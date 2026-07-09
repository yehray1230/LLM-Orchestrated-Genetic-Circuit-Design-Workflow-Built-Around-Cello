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
]

def main() -> None:
    # Resolve paths relative to the script location
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent
    docs_dir = workspace_root / "docs"
    output_file = workspace_root / "llms-full.txt"
    
    print(f"Generating aggregated context file at: {output_file.relative_to(workspace_root)}")
    
    combined_content = []
    combined_content.append("# LLM-Orchestrated Genetic Circuit Design Workflow - Complete Documentation\n")
    combined_content.append("This file aggregates all core documentation files for this repository to allow AI reviewers or agents to consume the entire codebase context in a single request.\n\n")
    
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
        
    output_file.write_text("".join(combined_content), encoding="utf-8")
    print("Generation complete!")

if __name__ == "__main__":
    main()
