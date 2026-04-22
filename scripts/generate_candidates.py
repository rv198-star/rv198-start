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
from kiu_pipeline.local_paths import resolve_output_root
from kiu_pipeline.normalize import normalize_graph
from kiu_pipeline.preflight import validate_generated_bundle
from kiu_pipeline.quality import assess_run_quality
from kiu_pipeline.render import load_generated_candidates, render_generated_run
from kiu_pipeline.reports import write_production_quality
from kiu_pipeline.seed import mine_candidate_seeds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate KiU v0.2 candidate bundles.")
    parser.add_argument("--source-bundle", required=True, help="Path to the source bundle.")
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Root directory for generated runs. Defaults to "
            "/tmp/kiu-local-artifacts/generated or "
            "$KIU_LOCAL_OUTPUT_ROOT/generated."
        ),
    )
    parser.add_argument("--run-id", required=True, help="Deterministic run identifier.")
    parser.add_argument(
        "--drafting-mode",
        default="deterministic",
        choices=("deterministic", "llm-assisted"),
        help="Drafting mode metadata recorded in candidate.yaml.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional automation profile override. Defaults to <source-bundle>/automation.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = resolve_output_root(args.output_root, bucket="generated")
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
        output_root=output_root,
        run_id=args.run_id,
    )
    report = validate_generated_bundle(run_root / "bundle")
    if report["errors"]:
        print(json.dumps(report["errors"], ensure_ascii=False, indent=2))
        return 1

    quality_report = assess_run_quality(
        candidates=load_generated_candidates(run_root / "bundle"),
        profile=source_bundle.profile,
    )
    write_production_quality(run_root, quality_report)

    print(
        json.dumps(
            {
                "run_root": str(run_root),
                "bundle_root": str(run_root / "bundle"),
                "summary": report["summary"],
                "quality": {
                    "release_ready": quality_report["release_ready"],
                    "bundle_quality_grade": quality_report["bundle_quality_grade"],
                    "minimum_production_quality": quality_report["minimum_production_quality"],
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
