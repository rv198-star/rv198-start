from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import CandidateSeed, SourceBundle


def build_candidate_anchors(
    *,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
    bundle_version: str,
    skill_revision: int,
) -> dict[str, Any]:
    source_skill = seed.source_skill
    graph_meta = source_bundle.manifest["graph"]

    graph_anchor_sets = [
        {
            "anchor_id": f"{seed.candidate_id}-seed-support",
            "node_ids": [seed.primary_node_id, *seed.supporting_node_ids],
            "edge_ids": seed.supporting_edge_ids,
            "community_ids": seed.community_ids,
        }
    ]

    source_anchor_sets: list[dict[str, Any]] = []
    if source_skill:
        source_anchor_sets = list(source_skill.anchors.get("source_anchor_sets", []))
    else:
        source_anchor_sets = _build_seed_source_anchors(
            source_bundle=source_bundle,
            seed=seed,
        )

    return {
        "skill_id": seed.candidate_id,
        "bundle_version": bundle_version,
        "skill_revision": skill_revision,
        "graph_version": graph_meta["graph_version"],
        "graph_hash": graph_meta["graph_hash"],
        "graph_anchor_sets": graph_anchor_sets,
        "source_anchor_sets": source_anchor_sets,
    }


def _build_seed_source_anchors(
    *,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
) -> list[dict[str, Any]]:
    node_docs = {
        node["id"]: node
        for node in source_bundle.graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    source_anchor_sets: list[dict[str, Any]] = []
    for node_id in [seed.primary_node_id, *seed.supporting_node_ids]:
        node_doc = node_docs.get(node_id, {})
        source_anchor = node_doc.get("source_anchor", {})
        relative_path = source_anchor.get("path")
        if not relative_path:
            continue
        line_start = int(source_anchor.get("line_start", 1))
        line_end = int(source_anchor.get("line_end", line_start))
        source_anchor_sets.append(
            {
                "anchor_id": f"{seed.candidate_id}-{node_id}",
                "kind": source_anchor.get("kind", "source_excerpt"),
                "path": _candidate_relative_path(relative_path),
                "line_start": line_start,
                "line_end": line_end,
                "snippet": _read_snippet(
                    source_bundle.root / relative_path,
                    line_start=line_start,
                    line_end=line_end,
                ),
            }
        )
    return source_anchor_sets


def _candidate_relative_path(relative_path: str) -> str:
    return (Path("..") / ".." / relative_path).as_posix()


def _read_snippet(path: Path, *, line_start: int, line_end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = " ".join(
        line.strip()
        for line in lines[line_start - 1 : line_end]
        if line.strip()
    )
    return excerpt[:220] if len(excerpt) > 220 else excerpt
