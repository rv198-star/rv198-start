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

from kiu_pipeline.example_fixture import scaffold_example_bundle
from kiu_pipeline.local_paths import resolve_output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a minimal KiU source bundle from an example fixture.",
    )
    parser.add_argument("--fixture", required=True, help="Path to the fixture YAML.")
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Root directory where the scaffolded bundle will be written. "
            "Defaults to /tmp/kiu-local-artifacts/sources or "
            "$KIU_LOCAL_OUTPUT_ROOT/sources."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_output_root(args.output_root, bucket="sources")
    if args.output_root is None:
        output_root = output_root / Path(args.fixture).stem
    bundle_root = scaffold_example_bundle(
        fixture_path=args.fixture,
        output_root=output_root,
    )
    manifest_path = bundle_root / "manifest.yaml"
    payload = {
        "bundle_root": str(bundle_root),
        "manifest_path": str(manifest_path),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
