from __future__ import annotations

from typing import Any

from .clustering import derive_graph_communities


def generate_graph_report(graph_doc: dict[str, Any]) -> str:
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
    communities = derive_graph_communities(graph_doc)
    adjacency = _build_adjacency(edges)
    node_to_communities = _build_node_to_communities(communities)

    god_nodes = sorted(
        nodes.values(),
        key=lambda node: (
            -len(adjacency.get(node["id"], [])),
            str(node.get("label", node["id"])),
            node["id"],
        ),
    )[:5]
    surprising_edges = _find_surprising_connections(
        edges=edges,
        nodes=nodes,
        node_to_communities=node_to_communities,
    )
    suggested_questions = _build_suggested_questions(
        god_nodes=god_nodes,
        communities=communities,
    )

    lines = [
        "# GRAPH_REPORT",
        "",
        "## Snapshot",
        f"- source_snapshot: `{graph_doc.get('source_snapshot', '<unknown>')}`",
        f"- graph_version: `{graph_doc.get('graph_version', '<unknown>')}`",
        f"- nodes: `{len(nodes)}`",
        f"- edges: `{len(edges)}`",
        f"- communities: `{len(communities)}`",
    ]
    bundle_count = graph_doc.get("bundle_count")
    if bundle_count is not None:
        lines.append(f"- bundle_count: `{bundle_count}`")
    source_bundles = graph_doc.get("source_bundles", [])
    if source_bundles:
        rendered_bundles = ", ".join(
            f"`{bundle_id}`" for bundle_id in source_bundles if bundle_id
        )
        if rendered_bundles:
            lines.append(f"- source_bundles: {rendered_bundles}")
    lines.extend(["", "## God Nodes"])
    if god_nodes:
        for index, node in enumerate(god_nodes, start=1):
            lines.append(
                (
                    f"{index}. **{node.get('label', node['id'])}** "
                    f"(`{node['id']}`) | type=`{node.get('type', 'unknown')}` | "
                    f"degree=`{len(adjacency.get(node['id'], []))}`"
                )
            )
    else:
        lines.append("No nodes available.")

    lines.extend(["", "## Communities"])
    if communities:
        for community in communities:
            top_node = nodes.get(community["top_node_id"], {"label": community["top_node_id"]})
            member_labels = [
                nodes[node_id].get("label", node_id)
                for node_id in community.get("node_ids", [])
                if node_id in nodes
            ]
            lines.extend(
                [
                    f"### {community.get('label', community['id'])}",
                    f"- top_node: **{top_node.get('label', community['top_node_id'])}** (`{community['top_node_id']}`)",
                    f"- node_count: `{len(community.get('node_ids', []))}`",
                    f"- modularity_score: `{community.get('modularity_score', 0.0)}`",
                    f"- nodes: {', '.join(member_labels)}",
                ]
            )
    else:
        lines.append("No communities available.")

    lines.extend(["", "## Surprising Connections"])
    if surprising_edges:
        for edge in surprising_edges:
            from_node = nodes[edge["from"]]
            to_node = nodes[edge["to"]]
            extras = []
            if edge.get("cross_bundle"):
                extras.append("cross_bundle=`true`")
            shared_concepts = [
                concept
                for concept in edge.get("shared_concepts", [])
                if isinstance(concept, str) and concept
            ]
            if shared_concepts:
                extras.append(f"concepts=`{', '.join(shared_concepts)}`")
            support_refs = [
                ref
                for ref in edge.get("support_refs", [])
                if isinstance(ref, str) and ref
            ]
            if support_refs:
                extras.append(f"support_refs=`{len(support_refs)}`")
            lines.append(
                (
                    f"- **{from_node.get('label', edge['from'])}** -> "
                    f"**{to_node.get('label', edge['to'])}** | "
                    f"type=`{edge.get('type', 'unknown')}` | "
                    f"kind=`{edge.get('extraction_kind', 'unknown')}` | "
                    f"confidence=`{edge.get('confidence', 0.0)}`"
                    + (f" | {' | '.join(extras)}" if extras else "")
                )
            )
    else:
        lines.append("- No cross-community inferred or ambiguous connections yet.")

    lines.extend(["", "## Suggested Questions"])
    for index, question in enumerate(suggested_questions, start=1):
        lines.append(f"{index}. {question}")
    return "\n".join(lines) + "\n"


def _find_surprising_connections(
    *,
    edges: list[dict[str, Any]],
    nodes: dict[str, dict[str, Any]],
    node_to_communities: dict[str, list[str]],
) -> list[dict[str, Any]]:
    interesting = []
    for edge in edges:
        if edge.get("extraction_kind") not in {"INFERRED", "AMBIGUOUS"}:
            continue
        source_communities = set(node_to_communities.get(edge["from"], []))
        target_communities = set(node_to_communities.get(edge["to"], []))
        if source_communities and target_communities and source_communities == target_communities:
            continue
        interesting.append(edge)
    interesting.sort(
        key=lambda edge: (
            -int(bool(edge.get("cross_bundle"))),
            -float(edge.get("confidence", 0.0) or 0.0),
            str(nodes[edge["from"]].get("label", edge["from"])),
            str(nodes[edge["to"]].get("label", edge["to"])),
            edge["id"],
        )
    )
    return interesting[:3]


def _build_suggested_questions(
    *,
    god_nodes: list[dict[str, Any]],
    communities: list[dict[str, Any]],
) -> list[str]:
    questions: list[str] = []
    for node in god_nodes[:2]:
        questions.append(
            f"Why does `{node.get('label', node['id'])}` sit at the center of this graph, and what evidence would most change its routing?"
        )
    for community in communities[:2]:
        questions.append(
            f"What is the operational boundary of `{community.get('label', community['id'])}`, and should it stay agentic or downgrade to workflow?"
        )
    if communities:
        questions.append(
            f"Which missing evidence would most improve confidence for `{communities[0].get('label', communities[0]['id'])}`?"
        )
    if not questions:
        questions.append("What additional extraction evidence is needed before this graph can support stable skill generation?")
    return questions[:5]


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
