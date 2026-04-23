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

from kiu_pipeline.extraction import validate_source_chunks_doc
from kiu_pipeline.source_chunks import build_source_chunks_from_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize a markdown source into KiU source-chunks artifacts.",
    )
    parser.add_argument("--input", required=True, help="Markdown source file.")
    parser.add_argument("--bundle-id", required=True, help="Owning bundle id for the chunk artifact.")
    parser.add_argument("--source-id", required=True, help="Stable source identifier.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    parser.add_argument("--language", default="zh-CN", help="Language tag recorded in chunks.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Maximum characters per chunk before splitting within the same section.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    doc = build_source_chunks_from_markdown(
        input_path=args.input,
        bundle_id=args.bundle_id,
        source_id=args.source_id,
        language=args.language,
        max_chars=args.max_chars,
    )
    errors = validate_source_chunks_doc(doc)
    if errors:
        print(json.dumps({"errors": errors}, ensure_ascii=False, indent=2))
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "chunk_count": len(doc["chunks"]),
                "section_count": len(doc.get("section_map", [])),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
