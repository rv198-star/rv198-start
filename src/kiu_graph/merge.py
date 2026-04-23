from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .inference import derive_cross_bundle_inferred_edges
from .migrate import canonical_graph_hash


def merge_bundle_graphs(bundle_paths: list[str | Path]) -> dict[str, Any]:
    bundle_docs = [_load_bundle_graph(bundle_path) for bundle_path in bundle_paths]
    return _merge_graph_docs(bundle_docs)


def _load_bundle_graph(bundle_path: str | Path) -> dict[str, Any]:
    root = Path(bundle_path)
    manifest = _load_yaml(root / "manifest.yaml")
    bundle_id = manifest.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise ValueError(f"{root}: manifest missing bundle_id")

    graph_meta = manifest.get("graph", {})
    graph_path_value = graph_meta.get("path")
    if not isinstance(graph_path_value, str) or not graph_path_value:
        raise ValueError(f"{root}: manifest missing graph.path")

    graph_path = root / graph_path_value
    graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
    return {
        "bundle_id": bundle_id,
        "bundle_path": str(root),
        "graph_doc": graph_doc,
    }


def _merge_graph_docs(bundle_docs: list[dict[str, Any]]) -> dict[str, Any]:
    if not bundle_docs:
        raise ValueError("at least one bundle is required for graph merge")

    seen_bundle_ids: set[str] = set()
    for bundle_doc in bundle_docs:
        bundle_id = bundle_doc["bundle_id"]
        if bundle_id in seen_bundle_ids:
            raise ValueError(f"duplicate bundle_id in merge set: {bundle_id}")
        seen_bundle_ids.add(bundle_id)

    ordered_bundles = sorted(bundle_docs, key=lambda item: item["bundle_id"])
    merged_nodes: list[dict[str, Any]] = []
    merged_edges: list[dict[str, Any]] = []
    merged_communities: list[dict[str, Any]] = []
    merged_graph_version = "kiu.graph.merge/v0.1"

    for bundle_doc in ordered_bundles:
        bundle_id = bundle_doc["bundle_id"]
        graph_doc = bundle_doc["graph_doc"]
        if graph_doc.get("graph_version") == "kiu.graph/v0.2":
            merged_graph_version = "kiu.graph.merge/v0.2"

        for node in sorted(graph_doc.get("nodes", []), key=lambda item: item["id"]):
            merged_nodes.append(_namespace_node(bundle_id, node))

        for edge in sorted(graph_doc.get("edges", []), key=lambda item: item["id"]):
            merged_edges.append(_namespace_edge(bundle_id, edge))

        for community in sorted(
            graph_doc.get("communities", []),
            key=lambda item: item["id"],
        ):
            merged_communities.append(_namespace_community(bundle_id, community))

    merged_doc = {
        "graph_version": merged_graph_version,
        "source_bundles": [bundle_doc["bundle_id"] for bundle_doc in ordered_bundles],
        "bundle_count": len(ordered_bundles),
        "nodes": merged_nodes,
        "edges": merged_edges,
        "communities": merged_communities,
    }
    merged_doc["edges"].extend(derive_cross_bundle_inferred_edges(merged_doc))
    merged_doc["graph_hash"] = canonical_graph_hash(merged_doc)
    return merged_doc


def _namespace_node(bundle_id: str, node: dict[str, Any]) -> dict[str, Any]:
    namespaced = dict(node)
    namespaced["id"] = _namespace_id(bundle_id, node["id"])
    namespaced["bundle_id"] = bundle_id
    namespaced["source_id"] = node["id"]
    return namespaced


def _namespace_edge(bundle_id: str, edge: dict[str, Any]) -> dict[str, Any]:
    namespaced = dict(edge)
    namespaced["id"] = _namespace_id(bundle_id, edge["id"])
    namespaced["from"] = _namespace_id(bundle_id, edge["from"])
    namespaced["to"] = _namespace_id(bundle_id, edge["to"])
    namespaced["bundle_id"] = bundle_id
    namespaced["source_id"] = edge["id"]
    return namespaced


def _namespace_community(bundle_id: str, community: dict[str, Any]) -> dict[str, Any]:
    namespaced = dict(community)
    namespaced["id"] = _namespace_id(bundle_id, community["id"])
    namespaced["node_ids"] = sorted(
        _namespace_id(bundle_id, node_id)
        for node_id in community.get("node_ids", [])
    )
    namespaced["bundle_id"] = bundle_id
    namespaced["source_id"] = community["id"]
    return namespaced


def _namespace_id(bundle_id: str, source_id: str) -> str:
    return f"{bundle_id}::{source_id}"
def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}
