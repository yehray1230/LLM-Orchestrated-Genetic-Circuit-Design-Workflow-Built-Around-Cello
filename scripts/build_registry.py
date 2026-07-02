from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from catalog.agent_catalog import DEFAULT_CATALOG_ROOT, build_agent_registry  # noqa: E402
from catalog.workflow_kit_catalog import (  # noqa: E402
    DEFAULT_WORKFLOW_KIT_ROOT,
    build_workflow_kit_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify all generated catalog registries."
    )
    parser.add_argument(
        "--agent-catalog-root",
        default=str(DEFAULT_CATALOG_ROOT),
        help="Directory containing catalog/agents/<agent-id>/metadata.yaml entries.",
    )
    parser.add_argument(
        "--workflow-kit-root",
        default=str(DEFAULT_WORKFLOW_KIT_ROOT),
        help="Directory containing catalog/workflow-kits/<kit-id>/kit.json entries.",
    )
    parser.add_argument(
        "--registry-dir",
        default="registry",
        help="Directory for generated registry JSON files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if generated registries differ from files on disk.",
    )
    args = parser.parse_args()

    registry_dir = Path(args.registry_dir)
    outputs = {
        registry_dir / "agent-registry.json": build_agent_registry(
            args.agent_catalog_root
        ),
        registry_dir / "workflow-kit-registry.json": build_workflow_kit_registry(
            args.workflow_kit_root,
            agent_catalog_root=args.agent_catalog_root,
        ),
    }

    if args.check:
        return _check_outputs(outputs)

    registry_dir.mkdir(parents=True, exist_ok=True)
    for path, payload in outputs.items():
        _write_json(path, payload)
        print(f"Wrote {path}")
    return 0


def _check_outputs(outputs: dict[Path, dict]) -> int:
    mismatches: list[str] = []
    for path, payload in outputs.items():
        expected = _json_text(payload)
        if not path.exists():
            mismatches.append(f"{path} is missing")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            mismatches.append(f"{path} is stale")

    if mismatches:
        for mismatch in mismatches:
            print(mismatch, file=sys.stderr)
        print(
            "Run `python scripts/build_registry.py` and commit the updated registry files.",
            file=sys.stderr,
        )
        return 1

    print("Registry files are up to date.")
    return 0


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(payload), encoding="utf-8")


def _json_text(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
