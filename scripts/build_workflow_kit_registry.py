from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from catalog.workflow_kit_catalog import (
    DEFAULT_WORKFLOW_KIT_ROOT,
    build_workflow_kit_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the workflow kit registry.")
    parser.add_argument(
        "--kit-root",
        default=str(DEFAULT_WORKFLOW_KIT_ROOT),
        help="Directory containing catalog/workflow-kits/<kit-id>/kit.json entries.",
    )
    parser.add_argument(
        "--agent-catalog-root",
        default="catalog/agents",
        help="Directory containing agent metadata entries used for reference validation.",
    )
    parser.add_argument(
        "--output",
        default="registry/workflow-kit-registry.json",
        help="Path to write the aggregated workflow kit registry JSON.",
    )
    args = parser.parse_args()

    registry = build_workflow_kit_registry(
        args.kit_root,
        agent_catalog_root=args.agent_catalog_root,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {registry['kit_count']} workflow kit entries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
