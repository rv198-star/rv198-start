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

from kiu_pipeline.blind_review_pack import merge_blind_review_response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge anonymous reviewer response with private key into blind evidence JSON.")
    parser.add_argument("--response", required=True, help="Filled reviewer-response JSON.")
    parser.add_argument("--private-key", required=True, help="private-unblind-key.json retained by maintainers.")
    parser.add_argument("--output", required=True, help="Output blind-preference-review-v0.1 JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = merge_blind_review_response(
        response_path=args.response,
        key_path=args.private_key,
        output_path=args.output,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
