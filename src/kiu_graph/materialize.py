from __future__ import annotations

from typing import Any

from .migrate import canonical_graph_hash


def materialize_graph_from_extraction_result(
    extraction_result: dict[str, Any],
) -> dict[str, Any]:
    graph_doc = {
        "graph_version": "kiu.graph/v0.2",
        "source_snapshot": extraction_result.get("source_id"),
        "nodes": [],
        "edges": [],
        "communities": [],
    }

    for node in extraction_result.get("nodes", []):
        if not isinstance(node, dict):
            continue
        graph_doc["nodes"].append(_materialize_node(node, extraction_result))

    for edge in extraction_result.get("edges", []):
        if not isinstance(edge, dict):
            continue
        graph_doc["edges"].append(_materialize_edge(edge, extraction_result))

    graph_doc["graph_hash"] = canonical_graph_hash(graph_doc)
    return graph_doc


def _materialize_node(node: dict[str, Any], extraction_result: dict[str, Any]) -> dict[str, Any]:
    materialized = dict(node)
    materialized.setdefault("source_file", extraction_result.get("source_file"))
    materialized.setdefault("source_location", None)
    materialized.setdefault("extraction_kind", "INFERRED")
    materialized.pop("chunk_id", None)
    materialized.pop("extractor_kind", None)
    return materialized


def _materialize_edge(edge: dict[str, Any], extraction_result: dict[str, Any]) -> dict[str, Any]:
    materialized = dict(edge)
    materialized.setdefault("source_file", extraction_result.get("source_file"))
    materialized.setdefault("source_location", None)
    materialized.setdefault("extraction_kind", "INFERRED")
    materialized.setdefault("confidence", 0.7)
    return materialized
