from __future__ import annotations

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

    return {
        "skill_id": seed.candidate_id,
        "bundle_version": bundle_version,
        "skill_revision": skill_revision,
        "graph_version": graph_meta["graph_version"],
        "graph_hash": graph_meta["graph_hash"],
        "graph_anchor_sets": graph_anchor_sets,
        "source_anchor_sets": source_anchor_sets,
    }
