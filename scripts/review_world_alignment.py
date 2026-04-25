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

from kiu_pipeline.world_alignment import review_world_alignment, validate_no_web_world_alignment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review v0.7 basic isolated world-alignment artifacts.")
    parser.add_argument("--bundle", required=True, help="Path to a generated bundle root.")
    parser.add_argument("--output", default=None, help="Optional JSON output path.")
    parser.add_argument("--no-web-only", action="store_true", help="Only run the no-web hallucination gate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = validate_no_web_world_alignment(args.bundle) if args.no_web_only else review_world_alignment(args.bundle)
    if args.output:
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("passed", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
