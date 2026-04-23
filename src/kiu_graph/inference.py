from __future__ import annotations

import re
from typing import Any


INFERENCE_NODE_TYPES = {
    "skill_principle",
    "control_principle",
    "principle_signal",
    "control_signal",
}

CONCEPT_KEYWORDS = {
    "boundary_control": (
        "boundary",
        "boundary discipline",
        "circle of competence",
        "competence",
        "blast radius",
        "radius",
        "scope",
    ),
    "risk_safety": (
        "margin of safety",
        "safety",
        "risk control",
        "risk",
        "blast radius",
        "holdback",
        "exposure cap",
        "reversibility",
        "irreversible",
    ),
    "error_avoidance": (
        "invert",
        "error avoidance",
        "anti-ruin",
        "checklist",
        "precheck",
        "guard",
        "gate",
        "regret",
    ),
    "learning_audit": (
        "bias",
        "audit",
        "postmortem",
        "blameless",
        "timeline gap",
        "runbook",
        "learning loop",
    ),
}

SUPPORT_REF_LIMIT_PER_SIDE = 2
MAX_INFERRED_EDGE_COUNT = 8


def derive_cross_bundle_inferred_edges(graph_doc: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {
        node["id"]: node
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    edges = [
        edge
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict) and edge.get("from") in nodes and edge.get("to") in nodes
    ]
    communities = [
        community
        for community in graph_doc.get("communities", [])
        if isinstance(community, dict) and community.get("id")
    ]
    adjacency = _build_adjacency(edges)
    community_labels = {community["id"]: str(community.get("label", "")) for community in communities}
    node_to_communities = _build_node_to_communities(communities)

    candidate_docs = []
    for node in nodes.values():
        if node.get("type") not in INFERENCE_NODE_TYPES:
            continue
        bundle_id = node.get("bundle_id")
        if not isinstance(bundle_id, str) or not bundle_id:
            continue
        support_refs = _collect_support_refs(node["id"], adjacency)
        if not support_refs:
            continue
        concept_doc = _derive_concepts(
            node=node,
            node_to_communities=node_to_communities,
            community_labels=community_labels,
        )
        if not concept_doc["all_concepts"]:
            continue
        candidate_docs.append(
            {
                "node": node,
                "bundle_id": bundle_id,
                "degree": len(adjacency.get(node["id"], [])),
                "support_refs": support_refs,
                "concepts": concept_doc,
            }
        )

    candidate_docs.sort(key=lambda item: item["node"]["id"])
    inferred_edges = []
    for index, left in enumerate(candidate_docs):
        for right in candidate_docs[index + 1 :]:
            if left["bundle_id"] == right["bundle_id"]:
                continue
            inferred_edge = _build_inferred_edge(left=left, right=right)
            if inferred_edge is not None:
                inferred_edges.append(inferred_edge)

    inferred_edges.sort(
        key=lambda edge: (
            -float(edge.get("confidence", 0.0) or 0.0),
            str(edge.get("from", "")),
            str(edge.get("to", "")),
            str(edge.get("id", "")),
        )
    )
    return inferred_edges[:MAX_INFERRED_EDGE_COUNT]


def _build_inferred_edge(
    *,
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any] | None:
    left_concepts = set(left["concepts"]["all_concepts"])
    right_concepts = set(right["concepts"]["all_concepts"])
    shared_concepts = sorted(left_concepts & right_concepts)
    if not shared_concepts:
        return None

    support_refs = sorted(set([*left["support_refs"], *right["support_refs"]]))
    if len(support_refs) < 3:
        return None

    shared_community_concepts = sorted(
        set(left["concepts"]["community_concepts"]) & set(right["concepts"]["community_concepts"])
    )
    confidence = _infer_confidence(
        shared_concepts=shared_concepts,
        shared_community_concepts=shared_community_concepts,
        support_ref_count=len(support_refs),
    )
    if confidence < 0.47:
        return None

    extraction_kind = "INFERRED" if confidence >= 0.58 else "AMBIGUOUS"
    from_doc, to_doc = _orient_pair(left, right)
    edge_id = _edge_id(
        from_id=from_doc["node"]["id"],
        to_id=to_doc["node"]["id"],
        shared_concepts=shared_concepts,
    )
    return {
        "id": edge_id,
        "from": from_doc["node"]["id"],
        "to": to_doc["node"]["id"],
        "type": "complements",
        "source_file": None,
        "source_location": None,
        "extraction_kind": extraction_kind,
        "confidence": confidence,
        "cross_bundle": True,
        "inference_basis": "shared_concept_support_heuristic",
        "shared_concepts": shared_concepts,
        "support_refs": support_refs,
        "support_ref_count": len(support_refs),
        "bundle_ids": sorted({left["bundle_id"], right["bundle_id"]}),
        "source_support_refs": {
            from_doc["node"]["id"]: list(from_doc["support_refs"]),
            to_doc["node"]["id"]: list(to_doc["support_refs"]),
        },
    }


def _derive_concepts(
    *,
    node: dict[str, Any],
    node_to_communities: dict[str, list[str]],
    community_labels: dict[str, str],
) -> dict[str, list[str]]:
    node_text = " ".join(
        part
        for part in [
            str(node.get("label", "")),
            str(node.get("type", "")),
        ]
        if part
    )
    normalized_node_text = _normalize_text(node_text)
    community_texts = [
        community_labels[community_id]
        for community_id in node_to_communities.get(node["id"], [])
        if community_id in community_labels and community_labels[community_id]
    ]
    normalized_community_text = _normalize_text(" ".join(community_texts))

    all_concepts: list[str] = []
    community_concepts: list[str] = []
    for concept, keywords in CONCEPT_KEYWORDS.items():
        if any(_normalize_text(keyword) in normalized_node_text for keyword in keywords):
            all_concepts.append(concept)
            continue
        if any(_normalize_text(keyword) in normalized_community_text for keyword in keywords):
            all_concepts.append(concept)
            community_concepts.append(concept)

    return {
        "all_concepts": sorted(set(all_concepts)),
        "community_concepts": sorted(set(community_concepts)),
    }


def _collect_support_refs(
    node_id: str,
    adjacency: dict[str, list[dict[str, Any]]],
) -> list[str]:
    support_edges = [
        edge
        for edge in adjacency.get(node_id, [])
        if edge.get("extraction_kind") == "EXTRACTED" and edge.get("id")
    ]
    support_edges.sort(
        key=lambda edge: (
            0 if edge.get("type") == "supports" else 1,
            str(edge.get("id", "")),
        )
    )
    return [edge["id"] for edge in support_edges[:SUPPORT_REF_LIMIT_PER_SIDE]]


def _infer_confidence(
    *,
    shared_concepts: list[str],
    shared_community_concepts: list[str],
    support_ref_count: int,
) -> float:
    confidence = 0.34
    confidence += 0.10 * min(len(shared_concepts), 3)
    confidence += 0.05 * min(len(shared_community_concepts), 2)
    confidence += 0.03 * min(support_ref_count, 4)
    return round(min(confidence, 0.79), 2)


def _orient_pair(
    left: dict[str, Any],
    right: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ordered = sorted(
        [left, right],
        key=lambda item: (
            item["degree"],
            str(item["node"].get("label", item["node"]["id"])),
            item["node"]["id"],
        ),
    )
    return ordered[0], ordered[1]


def _edge_id(
    *,
    from_id: str,
    to_id: str,
    shared_concepts: list[str],
) -> str:
    concept_suffix = "+".join(shared_concepts)
    return f"merge::inferred::{from_id}::{to_id}::{concept_suffix}"


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def _build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        adjacency.setdefault(edge["from"], []).append(edge)
        adjacency.setdefault(edge["to"], []).append(edge)
    return adjacency


def _build_node_to_communities(communities: list[dict[str, Any]]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for community in communities:
        community_id = community["id"]
        for node_id in community.get("node_ids", []):
            mapping.setdefault(node_id, []).append(community_id)
    return mapping
