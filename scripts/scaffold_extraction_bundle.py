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

from kiu_pipeline.extraction_bundle import scaffold_extraction_bundle
from kiu_pipeline.local_paths import resolve_output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a minimal KiU source bundle from extraction artifacts.",
    )
    parser.add_argument("--source-chunks", required=True, help="Path to source-chunks JSON.")
    parser.add_argument("--graph", required=True, help="Path to materialized graph JSON.")
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Root directory where the scaffolded bundle will be written. "
            "Defaults to /tmp/kiu-local-artifacts/sources or "
            "$KIU_LOCAL_OUTPUT_ROOT/sources."
        ),
    )
    parser.add_argument(
        "--inherits-from",
        default="default",
        help="Shared profile inheritance target for automation.yaml.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional human title override for manifest.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_output_root(args.output_root, bucket="sources")
    if args.output_root is None:
        output_root = output_root / Path(args.source_chunks).stem
    bundle_root = scaffold_extraction_bundle(
        source_chunks_path=args.source_chunks,
        graph_path=args.graph,
        output_root=output_root,
        inherits_from=args.inherits_from,
        title=args.title,
    )
    print(
        json.dumps(
            {
                "bundle_root": str(bundle_root),
                "manifest_path": str(bundle_root / "manifest.yaml"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
