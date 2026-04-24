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

from kiu_pipeline.blind_review_pack import build_blind_review_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an anonymous A/B blind review pack from a benchmark JSON report.")
    parser.add_argument("--benchmark-report", required=True, help="Reference benchmark JSON with same_scenario_usage cases.")
    parser.add_argument("--output-dir", required=True, help="Output directory for reviewer pack and private key.")
    parser.add_argument("--review-id", required=True, help="Stable review id.")
    parser.add_argument("--max-cases", type=int, default=None, help="Optional maximum number of cases to include.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_blind_review_pack(
        benchmark_report_path=args.benchmark_report,
        output_dir=args.output_dir,
        review_id=args.review_id,
        max_cases=args.max_cases,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
