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

from kiu_pipeline.reference_benchmark import (
    benchmark_reference_pack,
    write_reference_benchmark_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark a KiU bundle/run against a local reference skill pack.",
    )
    parser.add_argument("--kiu-bundle", required=True, help="Path to the KiU source or published bundle.")
    parser.add_argument(
        "--reference-pack",
        required=True,
        help="Path to the local benchmark/reference skill pack.",
    )
    parser.add_argument(
        "--run-root",
        default=None,
        help="Optional generated run root to include three-layer review and throughput metrics.",
    )
    parser.add_argument(
        "--alignment-file",
        default=None,
        help="Optional YAML file that aligns KiU skill ids to reference skill ids for deep same-source review.",
    )
    parser.add_argument(
        "--comparison-scope",
        default="structure-only",
        choices=("structure-only", "same-source"),
        help="How to interpret the comparison line.",
    )
    parser.add_argument(
        "--blind-preference-evidence",
        default=None,
        help="Optional anonymous blind preference evidence JSON file.",
    )
    parser.add_argument(
        "--compatibility-regression-report",
        default=None,
        help="Optional v0.6 regression baseline JSON report.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Output JSON path. Defaults to <run-root>/reports/reference-benchmark.json when "
            "--run-root is present, otherwise ./reference-benchmark.json."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = benchmark_reference_pack(
        kiu_bundle_path=args.kiu_bundle,
        reference_pack_path=args.reference_pack,
        run_root=args.run_root,
        alignment_file=args.alignment_file,
        comparison_scope=args.comparison_scope,
        blind_preference_evidence=args.blind_preference_evidence,
        compatibility_regression_report=args.compatibility_regression_report,
    )
    output_path = (
        Path(args.output)
        if args.output
        else (
            Path(args.run_root) / "reports" / "reference-benchmark.json"
            if args.run_root
            else Path("reference-benchmark.json")
        )
    )
    written = write_reference_benchmark_report(report=report, output_path=output_path)
    payload = {
        "json_path": written["json_path"],
        "markdown_path": written["markdown_path"],
        "summary": {
            "kiu_bundle_skill_count": report["kiu_bundle"]["skill_count"],
            "kiu_generated_skill_count": (
                report["generated_run"]["skill_count"] if report["generated_run"] else None
            ),
            "reference_skill_count": report["reference_pack"]["skill_count"],
            "matched_pair_count": report["concept_alignment"]["summary"]["matched_pair_count"],
            "kiu_foundation_retained_100": report["scorecard"]["kiu_foundation_retained_100"],
            "graphify_core_absorbed_100": report["scorecard"]["graphify_core_absorbed_100"],
            "cangjie_core_absorbed_100": report["scorecard"]["cangjie_core_absorbed_100"],
            "cangjie_methodology_internal_100": report["scorecard"].get(
                "cangjie_methodology_internal_100"
            ),
            "cangjie_methodology_external_blind_100": report["scorecard"].get(
                "cangjie_methodology_external_blind_100"
            ),
            "cangjie_methodology_closure_100": report["scorecard"].get(
                "cangjie_methodology_closure_100"
            ),
            "cangjie_methodology_quality_100": report["scorecard"].get(
                "cangjie_methodology_quality_100"
            ),
            "cangjie_methodology_gate_ready": report["scorecard"]
            .get("cangjie_methodology_gate", {})
            .get("ready"),
            "cangjie_methodology_claim": report["scorecard"]
            .get("cangjie_methodology_gate", {})
            .get("claim"),
            "final_artifact_effect_ready": report["scorecard"]
            .get("final_artifact_effect", {})
            .get("ready"),
            "final_artifact_effect_claim": report["scorecard"]
            .get("final_artifact_effect", {})
            .get("claim"),
            "compatibility_regression_risk": report["scorecard"]
            .get("compatibility_regression", {})
            .get("risk"),
            "cangjie_core_baseline_matrix_ready": report["scorecard"]
            .get("cangjie_core_baseline_matrix", {})
            .get("summary", {})
            .get("ready"),
            "cangjie_core_missing_capabilities": report["scorecard"]
            .get("cangjie_core_baseline_matrix", {})
            .get("summary", {})
            .get("missing_capabilities"),
        },
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
