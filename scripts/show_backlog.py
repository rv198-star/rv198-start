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

from kiu_pipeline.backlog import build_backlog_view, format_backlog_text, load_backlog


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the canonical KiU backlog board.")
    parser.add_argument(
        "--board",
        default=str(ROOT / "backlog" / "board.yaml"),
        help="Path to backlog board YAML.",
    )
    parser.add_argument("--version", help="Optional target version filter, e.g. v0.6.0.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args()

    board = load_backlog(args.board)
    view = build_backlog_view(board, version=args.version)
    if args.format == "json":
        print(json.dumps(view, ensure_ascii=False, indent=2))
    else:
        print(format_backlog_text(view), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
