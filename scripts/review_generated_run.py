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

from kiu_pipeline.reports import (
    reconcile_production_quality_with_review,
    write_three_layer_review,
)
from kiu_pipeline.review import review_generated_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score a generated KiU run across source bundle, generated bundle, and usage outputs.",
    )
    parser.add_argument("--run-root", required=True, help="Path to the generated run root.")
    parser.add_argument("--source-bundle", required=True, help="Path to the source bundle.")
    parser.add_argument(
        "--usage-review-dir",
        default=None,
        help="Optional usage-review directory override. Defaults to <run-root>/usage-review.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    review = review_generated_run(
        run_root=args.run_root,
        source_bundle_path=args.source_bundle,
        usage_review_dir=args.usage_review_dir,
    )
    write_three_layer_review(args.run_root, review)
    reconcile_production_quality_with_review(args.run_root, review)
    print(
        json.dumps(
            {
                "run_root": str(Path(args.run_root)),
                "overall_score_100": review["overall_score_100"],
                "source_bundle": review["source_bundle"]["score_100"],
                "generated_bundle": review["generated_bundle"]["score_100"],
                "usage_outputs": review["usage_outputs"]["score_100"],
                "release_gate_overall_ready": review["release_gate"]["overall_ready"],
                "release_gate_reasons": review["release_gate"]["reasons"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
