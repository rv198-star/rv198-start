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

from kiu_pipeline.extraction import (
    validate_extraction_result_doc,
    validate_source_chunks_doc,
)
from kiu_pipeline.extractor_runtime import build_extraction_result_with_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read source chunks and emit an empty extraction-result shell for W2 wiring.",
    )
    parser.add_argument("--source-chunks", required=True, help="Path to source-chunks JSON.")
    parser.add_argument("--output", required=True, help="Where to write extraction-result JSON.")
    parser.add_argument(
        "--drafting-mode",
        default="deterministic",
        choices=("deterministic", "llm-assisted"),
        help="Whether to emit deterministic-only output or apply an LLM patch on top.",
    )
    parser.add_argument(
        "--deterministic-pass",
        default="empty-shell",
        choices=("empty-shell", "section-headings", "heuristic-extractors"),
        help="Deterministic extraction pass to run before any future LLM stage.",
    )
    parser.add_argument(
        "--llm-budget-tokens",
        type=int,
        default=6000,
        help="Token budget ceiling for llm-assisted extraction drafting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_chunks = json.loads(Path(args.source_chunks).read_text(encoding="utf-8"))
    source_errors = validate_source_chunks_doc(source_chunks)
    if source_errors:
        print(json.dumps({"errors": source_errors}, ensure_ascii=False, indent=2))
        return 1

    try:
        extraction_result = build_extraction_result_with_audit(
            source_chunks_doc=source_chunks,
            deterministic_pass=args.deterministic_pass,
            drafting_mode=args.drafting_mode,
            llm_budget_tokens=args.llm_budget_tokens,
        )
    except Exception as exc:
        print(json.dumps({"errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 1

    result_errors = validate_extraction_result_doc(extraction_result)
    if result_errors:
        print(json.dumps({"errors": result_errors}, ensure_ascii=False, indent=2))
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(extraction_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "input_chunk_count": extraction_result["input_chunk_count"],
                "node_count": len(extraction_result["nodes"]),
                "edge_count": len(extraction_result["edges"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
