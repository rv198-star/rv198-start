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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve the blind-review reference source mode for v0.6.x audits.")
    parser.add_argument(
        "--reference-source",
        default="internal-mock",
        choices=("internal-mock", "upstream-cangjie", "none"),
        help="Reference source to use for blind-review preparation.",
    )
    parser.add_argument("--internal-reference-pack", default=None, help="Path to an internal control/reference pack.")
    parser.add_argument(
        "--upstream-cangjie-root",
        default=str(ROOT / ".references" / "cangjie-skill"),
        help="Vendored upstream cangjie-skill checkout root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = _resolve_reference_source(args)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["ready"] else 2


def _resolve_reference_source(args: argparse.Namespace) -> dict[str, object]:
    if args.reference_source == "none":
        return {
            "schema_version": "kiu.blind-review-reference-source/v0.1",
            "reference_source": "none",
            "ready": True,
            "path": None,
            "notes": ["No reference artifact will be included; use for KiU-only smoke checks."],
        }
    if args.reference_source == "internal-mock":
        path = (
            Path(args.internal_reference_pack)
            if args.internal_reference_pack
            else ROOT / "evidence" / "archive" / "reports" / "blind-review-packs" / "v0.6.7-shiji-control-style-B"
        )
        return {
            "schema_version": "kiu.blind-review-reference-source/v0.1",
            "reference_source": "internal-mock",
            "ready": path.exists(),
            "path": str(path),
            "notes": ["Internal benchmark/control style only; not an upstream project result."],
        }
    root = Path(args.upstream_cangjie_root)
    skill = root / "SKILL.md"
    return {
        "schema_version": "kiu.blind-review-reference-source/v0.1",
        "reference_source": "upstream-cangjie",
        "ready": skill.exists(),
        "path": str(root),
        "notes": [
            "Uses vendored upstream cangjie-skill reference material as explicit benchmark/reference input.",
            "This does not make upstream artifacts hidden inputs to KiU generation.",
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
