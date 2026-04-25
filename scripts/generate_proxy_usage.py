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

from kiu_pipeline.proxy_usage import write_proxy_usage_reviews


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic randomized proxy usage cases for a KiU run.")
    parser.add_argument("--run-root", required=True, help="Path to a generated run root containing bundle/.")
    parser.add_argument("--cases-per-skill", type=int, default=8, help="Number of proxy cases per skill.")
    parser.add_argument("--seed", default="kiu-v070-proxy-usage", help="Stable seed for deterministic case selection.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = write_proxy_usage_reviews(
        args.run_root,
        cases_per_skill=args.cases_per_skill,
        seed=args.seed,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
