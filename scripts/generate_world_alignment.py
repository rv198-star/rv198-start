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

from kiu_pipeline.world_alignment import build_world_alignment_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate v0.7 basic isolated world-alignment artifacts for a KiU bundle.")
    parser.add_argument("--bundle", required=True, help="Path to a generated bundle root.")
    parser.add_argument("--skill-id", action="append", default=None, help="Skill id to align. May be repeated. Defaults to all skills.")
    parser.add_argument("--no-web", action="store_true", help="Generate in no-web mode. This is the v0.7.0 default policy.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_world_alignment_artifacts(
        args.bundle,
        no_web_mode=True if args.no_web else True,
        selected_skill_ids=args.skill_id,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
