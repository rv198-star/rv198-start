#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.regression import run_v06_regression_baseline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the fixed v0.6 regression baseline for the current KiU repository.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Root directory for regression artifacts. Defaults to "
            "/tmp/kiu-local-artifacts/regression-baseline or "
            "$KIU_LOCAL_OUTPUT_ROOT/regression-baseline."
        ),
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python interpreter used to execute the baseline checks.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only the named check id. Can be repeated.",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Skip the named check id. Can be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run_v06_regression_baseline(
            repo_root=ROOT,
            output_root=args.output_root,
            python_executable=args.python_executable,
            only=args.only,
            skip=args.skip,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "report_path": report["report_path"],
                "executed": report["summary"]["executed"],
                "passed": report["summary"]["passed"],
                "failed": report["summary"]["failed"],
                "selected_check_ids": report["selected_check_ids"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
