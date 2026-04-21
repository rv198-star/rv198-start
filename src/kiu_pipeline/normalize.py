from __future__ import annotations

from .models import NormalizedGraph


def normalize_graph(graph_doc: dict) -> NormalizedGraph:
    nodes = {node["id"]: node for node in graph_doc.get("nodes", [])}
    edges = {edge["id"]: edge for edge in graph_doc.get("edges", [])}
    adjacency: dict[str, list[dict]] = {node_id: [] for node_id in nodes}
    for edge in graph_doc.get("edges", []):
        adjacency.setdefault(edge["from"], []).append(edge)
        adjacency.setdefault(edge["to"], []).append(edge)
    communities = {community["id"]: community for community in graph_doc.get("communities", [])}
    return NormalizedGraph(
        doc=graph_doc,
        nodes=nodes,
        edges=edges,
        adjacency=adjacency,
        communities=communities,
    )
