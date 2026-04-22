from __future__ import annotations

from typing import Any


SOURCE_CHUNKS_SCHEMA_VERSION = "kiu.source-chunks/v0.1"
EXTRACTION_RESULTS_SCHEMA_VERSION = "kiu.extraction-results/v0.1"
ALLOWED_EXTRACTION_KINDS = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}


def validate_source_chunks_doc(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema_version") != SOURCE_CHUNKS_SCHEMA_VERSION:
        errors.append("source_chunks: invalid schema_version")
    for field in ("bundle_id", "source_id", "source_file", "language"):
        if not isinstance(doc.get(field), str) or not doc[field]:
            errors.append(f"source_chunks: missing {field}")

    chunks = doc.get("chunks")
    if not isinstance(chunks, list):
        errors.append("source_chunks: chunks must be a list")
        return errors

    for index, chunk in enumerate(chunks):
        label = f"source_chunks[{index}]"
        if not isinstance(chunk, dict):
            errors.append(f"{label}: must be an object")
            continue
        for field in (
            "chunk_id",
            "source_id",
            "source_file",
            "chapter",
            "section",
            "chunk_text",
            "language",
        ):
            if not isinstance(chunk.get(field), str) or not chunk[field]:
                errors.append(f"{label}: missing {field}")
        line_start = chunk.get("line_start")
        line_end = chunk.get("line_end")
        token_estimate = chunk.get("token_estimate")
        if not isinstance(line_start, int) or line_start < 1:
            errors.append(f"{label}: invalid line_start")
        if not isinstance(line_end, int) or line_end < 1:
            errors.append(f"{label}: invalid line_end")
        if isinstance(line_start, int) and isinstance(line_end, int) and line_end < line_start:
            errors.append(f"{label}: line_end must be >= line_start")
        if not isinstance(token_estimate, int) or token_estimate < 0:
            errors.append(f"{label}: invalid token_estimate")
    return errors


def build_empty_extraction_result(source_chunks_doc: dict[str, Any]) -> dict[str, Any]:
    chunks = source_chunks_doc.get("chunks", [])
    return {
        "schema_version": EXTRACTION_RESULTS_SCHEMA_VERSION,
        "bundle_id": source_chunks_doc.get("bundle_id"),
        "source_id": source_chunks_doc.get("source_id"),
        "source_file": source_chunks_doc.get("source_file"),
        "input_chunk_count": len(chunks),
        "chunk_ids": [chunk.get("chunk_id") for chunk in chunks],
        "nodes": [],
        "edges": [],
        "warnings": [],
    }


def build_section_heading_extraction_result(source_chunks_doc: dict[str, Any]) -> dict[str, Any]:
    result = build_empty_extraction_result(source_chunks_doc)
    section_map = source_chunks_doc.get("section_map", [])
    source_file = source_chunks_doc.get("source_file")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    previous_node_id: str | None = None
    for index, entry in enumerate(section_map, start=1):
        title = entry.get("title")
        line_start = entry.get("line_start")
        if not isinstance(title, str) or not title:
            continue
        if not isinstance(line_start, int) or line_start < 1:
            continue
        node_id = f"section::{index:04d}"
        nodes.append(
            {
                "id": node_id,
                "type": "source_section",
                "label": title,
                "source_file": source_file,
                "source_location": {
                    "line_start": line_start,
                    "line_end": line_start,
                },
                "extraction_kind": "EXTRACTED",
            }
        )
        if previous_node_id is not None:
            edges.append(
                {
                    "id": f"section-edge::{index - 1:04d}-{index:04d}",
                    "type": "next_section",
                    "from": previous_node_id,
                    "to": node_id,
                    "source_file": source_file,
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_start,
                    },
                    "extraction_kind": "EXTRACTED",
                    "confidence": 1.0,
                }
            )
        previous_node_id = node_id

    result["deterministic_pass"] = "section-headings"
    result["nodes"] = nodes
    result["edges"] = edges
    if not nodes:
        result["warnings"] = ["no_section_headings_extracted"]
    return result


def validate_extraction_result_doc(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema_version") != EXTRACTION_RESULTS_SCHEMA_VERSION:
        errors.append("extraction_result: invalid schema_version")
    for field in ("bundle_id", "source_id", "source_file"):
        if not isinstance(doc.get(field), str) or not doc[field]:
            errors.append(f"extraction_result: missing {field}")

    input_chunk_count = doc.get("input_chunk_count")
    if not isinstance(input_chunk_count, int) or input_chunk_count < 0:
        errors.append("extraction_result: invalid input_chunk_count")

    chunk_ids = doc.get("chunk_ids")
    if not isinstance(chunk_ids, list):
        errors.append("extraction_result: chunk_ids must be a list")
    nodes = doc.get("nodes")
    edges = doc.get("edges")
    warnings = doc.get("warnings")
    if not isinstance(nodes, list):
        errors.append("extraction_result: nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        errors.append("extraction_result: edges must be a list")
        edges = []
    if not isinstance(warnings, list):
        errors.append("extraction_result: warnings must be a list")

    for index, node in enumerate(nodes):
        label = f"extraction_result.nodes[{index}]"
        if not isinstance(node, dict):
            errors.append(f"{label}: must be an object")
            continue
        for field in ("id", "type", "label", "source_file", "extraction_kind"):
            if not isinstance(node.get(field), str) or not node[field]:
                errors.append(f"{label}: missing {field}")
        if node.get("extraction_kind") not in ALLOWED_EXTRACTION_KINDS:
            errors.append(f"{label}: invalid extraction_kind")

    for index, edge in enumerate(edges):
        label = f"extraction_result.edges[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{label}: must be an object")
            continue
        for field in ("id", "type", "from", "to", "extraction_kind"):
            if not isinstance(edge.get(field), str) or not edge[field]:
                errors.append(f"{label}: missing {field}")
        if edge.get("extraction_kind") not in ALLOWED_EXTRACTION_KINDS:
            errors.append(f"{label}: invalid extraction_kind")
        confidence = edge.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            errors.append(f"{label}: invalid confidence")

    return errors
