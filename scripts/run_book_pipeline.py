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

from kiu_pipeline.book_pipeline import run_book_pipeline
from kiu_pipeline.local_paths import resolve_output_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the KiU v0.6 raw-book pipeline from markdown to BOOK_OVERVIEW, graph, and review artifacts.",
    )
    parser.add_argument("--input", required=True, help="Path to the source markdown file.")
    parser.add_argument("--bundle-id", required=True, help="Logical bundle id for source-chunks.")
    parser.add_argument("--source-id", required=True, help="Stable source id for the book.")
    parser.add_argument("--run-id", required=True, help="Generated-run identifier.")
    parser.add_argument(
        "--output-root",
        default=None,
        help=(
            "Root directory for all pipeline artifacts. Defaults to "
            "/tmp/kiu-local-artifacts/book-pipeline or "
            "$KIU_LOCAL_OUTPUT_ROOT/book-pipeline."
        ),
    )
    parser.add_argument("--max-chars", type=int, default=1200, help="Chunk max char length.")
    parser.add_argument("--language", default="zh-CN", help="Source language code.")
    parser.add_argument(
        "--deterministic-pass",
        default="heuristic-extractors",
        choices=("empty-shell", "section-headings", "heuristic-extractors"),
        help="Deterministic extraction pass to run.",
    )
    parser.add_argument(
        "--drafting-mode",
        default="deterministic",
        choices=("deterministic", "llm-assisted"),
        help="Candidate drafting mode for the downstream builder.",
    )
    parser.add_argument(
        "--inherits-from",
        default="default",
        help="Shared profile inheritance target for the scaffolded source bundle.",
    )
    parser.add_argument("--title", default=None, help="Optional manifest title override.")
    parser.add_argument(
        "--llm-budget-tokens",
        type=int,
        default=100000,
        help="Token budget ceiling for candidate refinement drafting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = (
        Path(args.output_root).expanduser()
        if args.output_root
        else resolve_output_root(None, bucket="book-pipeline")
    )
    payload = run_book_pipeline(
        input_path=args.input,
        bundle_id=args.bundle_id,
        source_id=args.source_id,
        run_id=args.run_id,
        output_root=output_root,
        max_chars=args.max_chars,
        language=args.language,
        deterministic_pass=args.deterministic_pass,
        drafting_mode=args.drafting_mode,
        inherits_from=args.inherits_from,
        title=args.title,
        llm_budget_tokens=args.llm_budget_tokens,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
