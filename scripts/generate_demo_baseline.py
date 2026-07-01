from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.demo_baseline import run_demo_baseline_freeze  # noqa: E402
from application.services import create_application_services  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the fixed A AND NOT B -> GFP demo baseline packet."
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path("outputs") / "api_data"),
        help="Application data directory used for runs and benchmark reports.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("outputs") / "demo_baseline"),
        help="Directory where the baseline packet artifacts will be written.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Maximum time to wait for the research simulation run.",
    )
    args = parser.parse_args()

    services = create_application_services(args.data_dir)
    packet = run_demo_baseline_freeze(
        services,
        output_dir=args.output_dir,
        timeout_seconds=args.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "packet_hash": packet["packet_hash"],
                "packet_json": packet["artifacts"]["packet_json"],
                "packet_markdown": packet["artifacts"]["packet_markdown"],
                "research_run_id": packet["research_run"]["run_id"],
                "benchmark_run_id": packet["benchmark_run"]["benchmark_run_id"],
                "readiness_status": packet["readiness"]["readiness_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
