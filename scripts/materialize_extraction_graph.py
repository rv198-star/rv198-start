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

from kiu_graph.materialize import materialize_graph_from_extraction_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize a KiU graph v0.2 document from extraction results.",
    )
    parser.add_argument("--extraction-result", required=True, help="Input extraction-result JSON.")
    parser.add_argument("--output", required=True, help="Output graph JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    extraction_result = json.loads(Path(args.extraction_result).read_text(encoding="utf-8"))
    graph_doc = materialize_graph_from_extraction_result(extraction_result)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "node_count": len(graph_doc["nodes"]),
                "edge_count": len(graph_doc["edges"]),
                "graph_hash": graph_doc["graph_hash"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
