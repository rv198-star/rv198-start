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

from kiu_graph.migrate import migrate_bundle_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate a KiU source bundle graph from v0.1 to provenance-first v0.2.",
    )
    parser.add_argument("bundle_path", help="Path to the bundle root to migrate in place.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = migrate_bundle_graph(args.bundle_path)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
