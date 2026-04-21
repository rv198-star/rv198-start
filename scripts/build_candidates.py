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

from kiu_pipeline.load import load_source_bundle
from kiu_pipeline.normalize import normalize_graph
from kiu_pipeline.preflight import validate_generated_bundle
from kiu_pipeline.refiner import refine_bundle_candidates
from kiu_pipeline.render import (
    load_generated_candidates,
    materialize_refined_candidates,
    render_generated_run,
)
from kiu_pipeline.seed import mine_candidate_seeds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build KiU v0.2 candidates with autonomous refinement.",
    )
    parser.add_argument("--source-bundle", required=True, help="Path to the source bundle.")
    parser.add_argument("--output-root", required=True, help="Root directory for generated runs.")
    parser.add_argument("--run-id", required=True, help="Run identifier.")
    parser.add_argument(
        "--drafting-mode",
        default="deterministic",
        choices=("deterministic", "llm-assisted"),
        help="Drafting mode metadata recorded in candidate.yaml.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional automation profile override.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_bundle = load_source_bundle(args.source_bundle, profile_override=args.profile)
    graph = normalize_graph(source_bundle.graph_doc)
    seeds = mine_candidate_seeds(
        source_bundle,
        graph,
        drafting_mode=args.drafting_mode,
    )
    run_root = render_generated_run(
        source_bundle=source_bundle,
        seeds=seeds,
        output_root=args.output_root,
        run_id=args.run_id,
    )
    bundle_root = run_root / "bundle"
    candidates = load_generated_candidates(bundle_root)
    refined = refine_bundle_candidates(
        candidates=candidates,
        source_bundle=source_bundle,
        run_root=run_root,
    )
    materialize_refined_candidates(bundle_root, refined)

    report = validate_generated_bundle(bundle_root)
    if report["errors"]:
        print(json.dumps(report["errors"], ensure_ascii=False, indent=2))
        return 1

    print(
        json.dumps(
            {
                "run_root": str(run_root),
                "bundle_root": str(bundle_root),
                "summary": report["summary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
