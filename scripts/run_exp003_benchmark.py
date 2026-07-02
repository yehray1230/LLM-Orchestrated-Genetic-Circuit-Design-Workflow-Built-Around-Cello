from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.design_task_benchmark import (  # noqa: E402
    run_exp003_design_task_benchmark,
)
from application.services import create_application_services  # noqa: E402
from schemas import (  # noqa: E402
    DEFAULT_TEMPORAL_CONFIG,
    TEMPORAL_EVALUATOR_CONFIGS,
    get_temporal_evaluator_config,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the fixed EXP-003 five-task deterministic benchmark."
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path("outputs") / "api_data"),
        help="Application data directory used for research run artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path("outputs") / "exp003_benchmark"),
        help="Directory where aggregate benchmark artifacts are written.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Maximum wait for each supported task simulation.",
    )
    parser.add_argument(
        "--temporal-evaluator-version",
        choices=sorted(TEMPORAL_EVALUATOR_CONFIGS),
        default=DEFAULT_TEMPORAL_CONFIG.version,
        help="Versioned temporal evaluator profile used for Toggle and Oscillator.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    services = create_application_services(args.data_dir)
    packet = run_exp003_design_task_benchmark(
        services,
        output_dir=args.output_dir,
        timeout_seconds=args.timeout_seconds,
        evaluator_config=get_temporal_evaluator_config(
            args.temporal_evaluator_version
        ),
    )
    print(
        json.dumps(
            {
                "stable_result_hash": packet["stable_result_hash"],
                "temporal_evaluator_version": packet["runner"][
                    "temporal_evaluator_version"
                ],
                "summary": packet["summary"],
                "packet_json": packet["artifacts"]["packet_json"],
                "summary_markdown": packet["artifacts"]["summary_markdown"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
