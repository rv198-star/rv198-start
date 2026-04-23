from __future__ import annotations

from typing import Any


COMMUNITY_SEED_TYPES = {
    "skill_principle",
    "control_principle",
    "principle_signal",
    "control_signal",
}


def derive_graph_communities(graph_doc: dict[str, Any]) -> list[dict[str, Any]]:
    existing = [
        community
        for community in graph_doc.get("communities", [])
        if isinstance(community, dict) and community.get("id")
    ]
    if existing:
        return _enrich_existing_communities(graph_doc, existing)

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
    adjacency = _build_adjacency(edges)

    seed_nodes = [
        node
        for node in nodes.values()
        if node.get("type") in COMMUNITY_SEED_TYPES
    ]
    seed_nodes.sort(
        key=lambda node: (
            -len(adjacency.get(node["id"], [])),
            str(node.get("label", node["id"])),
            node["id"],
        )
    )
    if seed_nodes:
        communities = _build_seed_communities(
            seed_nodes=seed_nodes,
            adjacency=adjacency,
            edges=edges,
            nodes=nodes,
        )
        if communities:
            return communities

    return _build_component_communities(
        nodes=nodes,
        adjacency=adjacency,
        edges=edges,
    )


def _enrich_existing_communities(
    graph_doc: dict[str, Any],
    communities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
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
    adjacency = _build_adjacency(edges)
    enriched: list[dict[str, Any]] = []
    for community in communities:
        node_ids = [
            node_id
            for node_id in community.get("node_ids", [])
            if node_id in nodes
        ]
        if not node_ids:
            continue
        top_node_id = community.get("top_node_id") or _pick_top_node(
            node_ids=node_ids,
            adjacency=adjacency,
            nodes=nodes,
        )
        enriched.append(
            {
                "id": community["id"],
                "label": community.get("label") or _community_label(nodes[top_node_id]),
                "node_ids": sorted(set(node_ids)),
                "top_node_id": top_node_id,
                "modularity_score": round(
                    _community_density(node_ids=node_ids, edges=edges),
                    4,
                ),
            }
        )
    return enriched


def _build_seed_communities(
    *,
    seed_nodes: list[dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    edges: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    communities: list[dict[str, Any]] = []
    seen_memberships: set[tuple[str, ...]] = set()
    for seed in seed_nodes:
        member_ids = {seed["id"]}
        for edge in adjacency.get(seed["id"], []):
            other = edge["to"] if edge["from"] == seed["id"] else edge["from"]
            member_ids.add(other)
        membership_key = tuple(sorted(member_ids))
        if membership_key in seen_memberships:
            continue
        seen_memberships.add(membership_key)
        communities.append(
            {
                "id": f"community::{seed['id']}",
                "label": _community_label(seed),
                "node_ids": list(membership_key),
                "top_node_id": seed["id"],
                "modularity_score": round(
                    _community_density(node_ids=list(member_ids), edges=edges),
                    4,
                ),
            }
        )
    return communities


def _build_component_communities(
    *,
    nodes: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pending = set(nodes)
    communities: list[dict[str, Any]] = []
    index = 0
    while pending:
        start = min(pending)
        stack = [start]
        component: set[str] = set()
        while stack:
            node_id = stack.pop()
            if node_id in component:
                continue
            component.add(node_id)
            pending.discard(node_id)
            for edge in adjacency.get(node_id, []):
                other = edge["to"] if edge["from"] == node_id else edge["from"]
                if other not in component:
                    stack.append(other)
        node_ids = sorted(component)
        top_node_id = _pick_top_node(
            node_ids=node_ids,
            adjacency=adjacency,
            nodes=nodes,
        )
        index += 1
        communities.append(
            {
                "id": f"community::component::{index:02d}",
                "label": _community_label(nodes[top_node_id]),
                "node_ids": node_ids,
                "top_node_id": top_node_id,
                "modularity_score": round(
                    _community_density(node_ids=node_ids, edges=edges),
                    4,
                ),
            }
        )
    return communities


def _pick_top_node(
    *,
    node_ids: list[str],
    adjacency: dict[str, list[dict[str, Any]]],
    nodes: dict[str, dict[str, Any]],
) -> str:
    return sorted(
        node_ids,
        key=lambda node_id: (
            -len(adjacency.get(node_id, [])),
            str(nodes[node_id].get("label", node_id)),
            node_id,
        ),
    )[0]


def _community_density(
    *,
    node_ids: list[str],
    edges: list[dict[str, Any]],
) -> float:
    if len(node_ids) <= 1:
        return 1.0
    member_set = set(node_ids)
    internal_edges = sum(
        1
        for edge in edges
        if edge["from"] in member_set and edge["to"] in member_set
    )
    possible_edges = len(node_ids) * (len(node_ids) - 1) / 2
    if possible_edges <= 0:
        return 1.0
    return min(internal_edges / possible_edges, 1.0)


def _community_label(node: dict[str, Any]) -> str:
    label = str(node.get("label", node.get("id", "community"))).strip()
    return f"{label} Cluster"


def _build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        adjacency.setdefault(edge["from"], []).append(edge)
        adjacency.setdefault(edge["to"], []).append(edge)
    return adjacency
