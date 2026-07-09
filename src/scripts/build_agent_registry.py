from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from catalog.agent_catalog import DEFAULT_CATALOG_ROOT, build_agent_registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the agent catalog registry.")
    parser.add_argument(
        "--catalog-root",
        default=str(DEFAULT_CATALOG_ROOT),
        help="Directory containing catalog/agents/<agent-id>/metadata.yaml entries.",
    )
    parser.add_argument(
        "--output",
        default="src/registry/agent-registry.json" if Path("src/registry").exists() else "registry/agent-registry.json",
        help="Path to write the aggregated registry JSON.",
    )
    args = parser.parse_args()

    registry = build_agent_registry(args.catalog_root)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {registry['agent_count']} agent entries to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
