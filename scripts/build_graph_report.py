#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_graph.clustering import derive_graph_communities
from kiu_graph.merge import merge_bundle_graphs
from kiu_graph.report import generate_graph_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a navigation-oriented GRAPH_REPORT.md from a KiU graph or bundle.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bundle", help="Path to a KiU source bundle.")
    group.add_argument("--graph", help="Path to a graph JSON document.")
    group.add_argument(
        "--merged",
        nargs="+",
        help="One or more bundle paths to merge before report generation.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output markdown path. Defaults to GRAPH_REPORT.md beside the bundle or in cwd.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.bundle:
        bundle_root = Path(args.bundle)
        manifest_path = bundle_root / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        graph_path = bundle_root / manifest["graph"]["path"]
        graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
        output_path = Path(args.output) if args.output else bundle_root / "GRAPH_REPORT.md"
        report_text = generate_graph_report(graph_doc)
        output_path.write_text(report_text, encoding="utf-8")
        manifest["graph_report"] = {
            "path": _relative_to_bundle(output_path, bundle_root),
            "community_count": len(derive_graph_communities(graph_doc)),
        }
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        payload = {
            "output_path": str(output_path),
            "community_count": manifest["graph_report"]["community_count"],
            "mode": "bundle",
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.graph:
        graph_path = Path(args.graph)
        graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
        output_path = Path(args.output) if args.output else Path.cwd() / "GRAPH_REPORT.md"
        output_path.write_text(generate_graph_report(graph_doc), encoding="utf-8")
        print(
            json.dumps(
                {
                    "output_path": str(output_path),
                    "community_count": len(derive_graph_communities(graph_doc)),
                    "mode": "graph",
                },
                ensure_ascii=False,
            )
        )
        return 0

    merged_graph = merge_bundle_graphs(args.merged)
    output_path = Path(args.output) if args.output else Path.cwd() / "GRAPH_REPORT.md"
    output_path.write_text(generate_graph_report(merged_graph), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_path": str(output_path),
                "community_count": len(derive_graph_communities(merged_graph)),
                "mode": "merged",
            },
            ensure_ascii=False,
        )
    )
    return 0


def _relative_to_bundle(path: Path, bundle_root: Path) -> str:
    try:
        return path.resolve().relative_to(bundle_root.resolve()).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
