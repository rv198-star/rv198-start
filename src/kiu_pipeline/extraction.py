from __future__ import annotations

import re
from typing import Any

import yaml

from kiu_pipeline.refiner.providers import create_provider_from_env, estimate_tokens


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
        entry_source_file = entry.get("source_file", source_file)
        node_id = f"section::{index:04d}"
        nodes.append(
            {
                "id": node_id,
                "type": "source_section",
                "label": title,
                "source_file": entry_source_file,
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
                    "source_file": entry_source_file,
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


def build_heuristic_extraction_result(source_chunks_doc: dict[str, Any]) -> dict[str, Any]:
    result = build_empty_extraction_result(source_chunks_doc)
    section_map = source_chunks_doc.get("section_map", [])
    chunks = source_chunks_doc.get("chunks", [])
    source_file = source_chunks_doc.get("source_file")

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    section_node_by_title: dict[str, str] = {}
    section_nodes_by_id: dict[str, dict[str, Any]] = {}
    narrative_evidence: list[dict[str, Any]] = []
    role_boundary_evidence: list[dict[str, Any]] = []
    strategy_evidence: list[dict[str, Any]] = []

    def add_node(node: dict[str, Any]) -> None:
        node_id = node["id"]
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(node)

    def add_inferred_signal_edge(
        *,
        section_node_id: str | None,
        target_id: str,
        edge_type: str,
        source_file_value: str,
        line_start: int,
        line_end: int,
        chunk_id: str,
    ) -> None:
        if not section_node_id:
            return
        edges.append(
            {
                "id": f"{edge_type}::{section_node_id}->{target_id}",
                "type": edge_type,
                "from": section_node_id,
                "to": target_id,
                "source_file": source_file_value,
                "source_location": {
                    "line_start": line_start,
                    "line_end": line_end,
                },
                "extraction_kind": "INFERRED",
                "confidence": 0.7,
                "inference_basis": "shared_section_chunk_context",
                "chunk_id": chunk_id,
            }
        )

    for index, entry in enumerate(section_map, start=1):
        title = entry.get("title")
        line_start = entry.get("line_start")
        level = entry.get("level")
        if not isinstance(title, str) or not title:
            continue
        if not isinstance(line_start, int) or line_start < 1:
            continue
        entry_source_file = entry.get("source_file", source_file)
        extractor_kind = "framework" if level == 1 else "principle"
        node_id = f"{extractor_kind}::{index:04d}"
        add_node(
            {
                "id": node_id,
                "type": f"{extractor_kind}_signal",
                "label": title,
                "source_file": entry_source_file,
                "source_location": {
                    "line_start": line_start,
                    "line_end": line_start,
                },
                "extraction_kind": "EXTRACTED",
                "extractor_kind": extractor_kind,
            }
        )
        section_node_by_title[title] = node_id
        section_nodes_by_id[node_id] = nodes[-1]
        path = entry.get("path", [])
        if isinstance(path, list) and len(path) > 1:
            parent_title = path[-2]
            parent_id = section_node_by_title.get(parent_title)
            if parent_id:
                edges.append(
                    {
                        "id": f"section-parent::{parent_id}->{node_id}",
                        "type": "section_parent",
                        "from": parent_id,
                        "to": node_id,
                        "source_file": entry_source_file,
                        "source_location": {
                            "line_start": line_start,
                            "line_end": line_start,
                        },
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    }
                )

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        chunk_text = chunk.get("chunk_text")
        line_start = chunk.get("line_start")
        line_end = chunk.get("line_end")
        section_title = chunk.get("section")
        if not isinstance(chunk_id, str) or not chunk_id:
            continue
        if not isinstance(chunk_text, str) or not chunk_text:
            continue
        if not isinstance(line_start, int) or not isinstance(line_end, int):
            continue
        evidence_id = f"evidence::{_safe_id(chunk_id)}"
        add_node(
            {
                "id": evidence_id,
                "type": "chunk_evidence",
                "label": _excerpt(chunk_text),
                "source_file": chunk.get("source_file", source_file),
                "source_location": {
                    "line_start": line_start,
                    "line_end": line_end,
                },
                "extraction_kind": "EXTRACTED",
                "extractor_kind": "evidence",
                "chunk_id": chunk_id,
            }
        )

        section_node_id = None
        if isinstance(section_title, str):
            section_node_id = section_node_by_title.get(section_title)
        if section_node_id:
            if section_node_id in section_nodes_by_id:
                _merge_routing_hints(
                    section_nodes_by_id[section_node_id],
                    chunk_id=chunk_id,
                    hints=_derive_routing_hints(chunk_text),
                )
            edges.append(
                {
                    "id": f"supported-by::{section_node_id}->{evidence_id}",
                    "type": "supported_by_evidence",
                    "from": section_node_id,
                    "to": evidence_id,
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "EXTRACTED",
                    "confidence": 1.0,
                }
            )

        if _has_case_cue(chunk_text):
            case_id = f"case::{_safe_id(chunk_id)}"
            add_node(
                {
                    "id": case_id,
                    "type": "case_signal",
                    "label": _excerpt(chunk_text),
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "EXTRACTED",
                    "extractor_kind": "case",
                }
            )
            edges.append(
                {
                    "id": f"case-from::{evidence_id}->{case_id}",
                    "type": "illustrated_by_case",
                    "from": evidence_id,
                    "to": case_id,
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "EXTRACTED",
                    "confidence": 1.0,
                }
            )
            add_inferred_signal_edge(
                section_node_id=section_node_id,
                target_id=case_id,
                edge_type="derives_case_signal",
                source_file_value=chunk.get("source_file", source_file),
                line_start=line_start,
                line_end=line_end,
                chunk_id=chunk_id,
            )

        if _has_counter_example_cue(chunk_text):
            counter_example_id = f"counter-example::{_safe_id(chunk_id)}"
            add_node(
                {
                    "id": counter_example_id,
                    "type": "counter_example_signal",
                    "label": _excerpt(chunk_text),
                    "section_title": section_title,
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "AMBIGUOUS",
                    "extractor_kind": "counter-example",
                    "inference_basis": "negative_outcome_heuristic",
                }
            )
            edges.append(
                {
                    "id": f"counter-example-from::{evidence_id}->{counter_example_id}",
                    "type": "flags_counter_example",
                    "from": evidence_id,
                    "to": counter_example_id,
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "AMBIGUOUS",
                    "confidence": 0.6,
                    "inference_basis": "negative_outcome_heuristic",
                    "chunk_id": chunk_id,
                }
            )
            add_inferred_signal_edge(
                section_node_id=section_node_id,
                target_id=counter_example_id,
                edge_type="derives_counter_example_signal",
                source_file_value=chunk.get("source_file", source_file),
                line_start=line_start,
                line_end=line_end,
                chunk_id=chunk_id,
            )

        for term in _extract_terms(chunk_text):
            term_id = f"term::{_safe_id(term.lower())}"
            add_node(
                {
                    "id": term_id,
                    "type": "term_signal",
                    "label": term,
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "EXTRACTED",
                    "extractor_kind": "term",
                }
            )
            edges.append(
                {
                    "id": f"term-from::{evidence_id}->{term_id}",
                    "type": "mentions_term",
                    "from": evidence_id,
                    "to": term_id,
                    "source_file": chunk.get("source_file", source_file),
                    "source_location": {
                        "line_start": line_start,
                        "line_end": line_end,
                    },
                    "extraction_kind": "EXTRACTED",
                    "confidence": 1.0,
                }
            )
            add_inferred_signal_edge(
                section_node_id=section_node_id,
                target_id=term_id,
                edge_type="derives_term_signal",
                source_file_value=chunk.get("source_file", source_file),
                line_start=line_start,
                line_end=line_end,
                chunk_id=chunk_id,
            )

        narrative_score, narrative_keywords = _narrative_decision_score(chunk_text)
        if narrative_score >= 3:
            narrative_evidence.append(
                {
                    "chunk_id": chunk_id,
                    "evidence_id": evidence_id,
                    "source_file": chunk.get("source_file", source_file),
                    "line_start": line_start,
                    "line_end": line_end,
                    "section_title": section_title,
                    "score": narrative_score,
                    "keywords": narrative_keywords,
                }
            )
        role_boundary_score, role_boundary_keywords = _role_boundary_decision_score(chunk_text)
        if role_boundary_score >= 3:
            role_boundary_evidence.append(
                {
                    "chunk_id": chunk_id,
                    "evidence_id": evidence_id,
                    "source_file": chunk.get("source_file", source_file),
                    "line_start": line_start,
                    "line_end": line_end,
                    "section_title": section_title,
                    "score": role_boundary_score,
                    "keywords": role_boundary_keywords,
                }
            )
        strategy_score, strategy_keywords = _situation_strategy_score(chunk_text)
        if strategy_score >= 3:
            strategy_evidence.append(
                {
                    "chunk_id": chunk_id,
                    "evidence_id": evidence_id,
                    "source_file": chunk.get("source_file", source_file),
                    "line_start": line_start,
                    "line_end": line_end,
                    "section_title": section_title,
                    "score": strategy_score,
                    "keywords": strategy_keywords,
                }
            )

    _add_case_mechanism_node(
        nodes=nodes,
        edges=edges,
        narrative_evidence=narrative_evidence,
        source_file_count=len(
            {
                chunk.get("source_file", source_file)
                for chunk in chunks
                if isinstance(chunk, dict) and chunk.get("source_file")
            }
        ),
    )
    _add_situation_strategy_nodes(
        nodes=nodes,
        edges=edges,
        strategy_evidence=strategy_evidence,
        source_file_count=len(
            {
                chunk.get("source_file", source_file)
                for chunk in chunks
                if isinstance(chunk, dict) and chunk.get("source_file")
            }
        ),
    )
    _add_narrative_pattern_signal(
        nodes=nodes,
        edges=edges,
        narrative_evidence=narrative_evidence,
        source_file_count=len(
            {
                chunk.get("source_file", source_file)
                for chunk in chunks
                if isinstance(chunk, dict) and chunk.get("source_file")
            }
        ),
    )
    _add_role_boundary_pattern_signal(
        nodes=nodes,
        edges=edges,
        role_boundary_evidence=role_boundary_evidence,
        source_file_count=len(
            {
                chunk.get("source_file", source_file)
                for chunk in chunks
                if isinstance(chunk, dict) and chunk.get("source_file")
            }
        ),
    )

    result["deterministic_pass"] = "heuristic-extractors"
    result["nodes"] = nodes
    result["edges"] = edges
    if not nodes:
        result["warnings"] = ["no_heuristic_signals_extracted"]
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
    extractor_run_log = doc.get("extractor_run_log")
    if extractor_run_log is not None and not isinstance(extractor_run_log, list):
        errors.append("extraction_result: extractor_run_log must be a list")

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

    if isinstance(extractor_run_log, list):
        for index, stage in enumerate(extractor_run_log):
            label = f"extraction_result.extractor_run_log[{index}]"
            if not isinstance(stage, dict):
                errors.append(f"{label}: must be an object")
                continue
            for field in ("stage_id", "extractor_kind", "pass_kind", "prompt_key"):
                if not isinstance(stage.get(field), str) or not stage[field]:
                    errors.append(f"{label}: missing {field}")
            for field in ("input_chunk_ids", "output_node_ids", "output_edge_ids"):
                value = stage.get(field)
                if not isinstance(value, list):
                    errors.append(f"{label}: {field} must be a list")
                    continue
                for item_index, item in enumerate(value):
                    if not isinstance(item, str) or not item:
                        errors.append(f"{label}: {field}[{item_index}] must be a non-empty string")

    return errors


def apply_llm_extraction_patch(
    *,
    source_chunks_doc: dict[str, Any],
    extraction_result: dict[str, Any],
    token_budget: int,
) -> dict[str, Any]:
    prompt = _build_llm_extraction_prompt(source_chunks_doc, extraction_result)
    prompt_tokens = estimate_tokens(prompt)
    if prompt_tokens > token_budget:
        raise ValueError(
            f"llm extraction prompt exceeds budget: {prompt_tokens} > {token_budget}"
        )

    provider = create_provider_from_env()
    response = provider.generate(
        field_name="extraction_result_patch",
        prompt=prompt,
    )
    patch_doc = yaml.safe_load(response.content) or {}
    if not isinstance(patch_doc, dict):
        raise ValueError("llm extraction patch must decode to a mapping")

    merged = {
        **extraction_result,
        "nodes": list(extraction_result.get("nodes", [])),
        "edges": list(extraction_result.get("edges", [])),
        "warnings": list(extraction_result.get("warnings", [])),
        "llm_drafting": {
            "provider": response.provider,
            "model": response.model,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "budget_tokens": token_budget,
        },
    }

    existing_node_ids = {node.get("id") for node in merged["nodes"] if isinstance(node, dict)}
    for node in patch_doc.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if node_id in existing_node_ids:
            continue
        if "source_file" not in node:
            node["source_file"] = extraction_result.get("source_file")
        if "extraction_kind" not in node:
            node["extraction_kind"] = "INFERRED"
        merged["nodes"].append(node)
        existing_node_ids.add(node_id)

    existing_edge_ids = {edge.get("id") for edge in merged["edges"] if isinstance(edge, dict)}
    for edge in patch_doc.get("edges", []) or []:
        if not isinstance(edge, dict):
            continue
        edge_id = edge.get("id")
        if edge_id in existing_edge_ids:
            continue
        if "source_file" not in edge:
            edge["source_file"] = extraction_result.get("source_file")
        if "extraction_kind" not in edge:
            edge["extraction_kind"] = "INFERRED"
        if "confidence" not in edge:
            edge["confidence"] = 0.7
        merged["edges"].append(edge)
        existing_edge_ids.add(edge_id)

    for warning in patch_doc.get("warnings", []) or []:
        if isinstance(warning, str) and warning not in merged["warnings"]:
            merged["warnings"].append(warning)

    return merged


def _add_narrative_pattern_signal(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    narrative_evidence: list[dict[str, Any]],
    source_file_count: int,
) -> None:
    if source_file_count < 3 or len(narrative_evidence) < 3:
        return
    selected = sorted(
        narrative_evidence,
        key=lambda item: (-int(item.get("score", 0) or 0), str(item.get("chunk_id", ""))),
    )[:8]
    primary = selected[0]
    node_id = "narrative-pattern::historical-case-consequence-judgment"
    keywords = sorted(
        {
            keyword
            for item in selected
            for keyword in item.get("keywords", [])
            if isinstance(keyword, str) and keyword
        }
    )
    nodes.append(
        {
            "id": node_id,
            "type": "narrative_pattern_signal",
            "label": "historical-case-consequence-judgment",
            "source_file": primary["source_file"],
            "source_location": {
                "line_start": primary["line_start"],
                "line_end": primary["line_end"],
            },
            "extraction_kind": "INFERRED",
            "extractor_kind": "narrative-pattern",
            "inference_basis": "multi_case_decision_consequence_pattern",
            "routing_hints": {
                "workflow_cues": 0,
                "context_cues": 4,
                "matched_keywords": [
                    "case_pattern",
                    "consequence",
                    "decision_boundary",
                    "tradeoff",
                    *keywords[:6],
                ],
                "evidence_chunk_ids": [item["chunk_id"] for item in selected],
            },
        }
    )
    for index, item in enumerate(selected, start=1):
        edges.append(
            {
                "id": f"narrative-pattern-evidence::{index:04d}",
                "type": "supported_by_evidence",
                "from": node_id,
                "to": item["evidence_id"],
                "source_file": item["source_file"],
                "source_location": {
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                },
                "extraction_kind": "EXTRACTED",
                "confidence": 1.0,
                "inference_basis": "narrative_case_support",
                "chunk_id": item["chunk_id"],
            }
        )


def _add_case_mechanism_node(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    narrative_evidence: list[dict[str, Any]],
    source_file_count: int,
) -> None:
    if source_file_count < 3 or len(narrative_evidence) < 3:
        return
    selected = sorted(
        narrative_evidence,
        key=lambda item: (-int(item.get("score", 0) or 0), str(item.get("chunk_id", ""))),
    )[:6]
    primary = selected[0]
    node_id = "case-mechanism::historical-analogy-transfer-gate"
    nodes.append(
        {
            "id": node_id,
            "type": "case_mechanism",
            "label": "historical-analogy-transfer-gate",
            "source_file": primary["source_file"],
            "source_location": {"line_start": primary["line_start"], "line_end": primary["line_end"]},
            "extraction_kind": "INFERRED",
            "extractor_kind": "case-mechanism",
            "actor": "source_case_actor",
            "role": "role_under_context",
            "objective": "current_or_historical_decision_goal",
            "constraint": "source_context_constraints",
            "action": "case_action",
            "immediate_gain": "short_term_effect_or_gain",
            "delayed_consequence": "long_term_consequence_or_backlash",
            "mechanism": "compare mechanism, not story surface",
            "evidence_pack": _build_evidence_pack(selected),
            "transfer_conditions": [
                "current_decision_is_explicit",
                "case_mechanism_matches_actor_role_constraint_action_outcome",
                "relevant_differences_are_named",
            ],
            "anti_conditions": [
                "single_case_overreach",
                "surface_similarity_only",
                "pure_history_query_or_translation",
            ],
            "routing_hints": {
                "workflow_cues": 0,
                "context_cues": 5,
                "agentic_priority": 80,
                "matched_keywords": ["case_mechanism", "transfer_conditions", "anti_conditions"],
                "evidence_chunk_ids": [item["chunk_id"] for item in selected],
            },
        }
    )
    for index, item in enumerate(selected, start=1):
        edges.append(
            {
                "id": f"case-mechanism-evidence::{index:04d}",
                "type": "supported_by_evidence",
                "from": node_id,
                "to": item["evidence_id"],
                "source_file": item["source_file"],
                "source_location": {"line_start": item["line_start"], "line_end": item["line_end"]},
                "extraction_kind": "EXTRACTED",
                "confidence": 1.0,
                "inference_basis": "case_mechanism_support",
                "chunk_id": item["chunk_id"],
            }
        )


def _narrative_decision_score(text: str) -> tuple[int, list[str]]:
    cue_patterns = (
        ("decision", r"(欲|将|谋|计|策|议|使|令|从之|不从|请|辞|拒|取|弃|攻|救|迁|贾|贷)"),
        ("consequence", r"(于是|遂|乃|卒|果|因|故|是以|以此|由此|终|竟|大破|败|亡|死|富|显|得|失)"),
        ("tradeoff", r"(利|害|权|势|赏|罚|富|贫|强|弱|远|近|虚|实|贵|贱|成败)"),
        ("boundary", r"(不若|不可|不能|非|毋|无|勿|独|唯|必|宜|当)"),
    )
    matched = [label for label, pattern in cue_patterns if re.search(pattern, text)]
    return len(matched), matched


def _add_situation_strategy_nodes(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    strategy_evidence: list[dict[str, Any]],
    source_file_count: int,
) -> None:
    if source_file_count < 2 or len(strategy_evidence) < 2:
        return
    specs = [
        {
            "candidate_id": "no-investigation-no-decision",
            "required": {"investigation", "anti-dogmatism"},
            "label": "no-investigation-no-decision",
            "mechanism": "ground decision in field evidence before applying doctrine or templates",
        },
        {
            "candidate_id": "principal-contradiction-focus",
            "required": {"contradiction", "strategy"},
            "label": "principal-contradiction-focus",
            "mechanism": "identify the principal contradiction before allocating action and attention",
        },
    ]
    for spec in specs:
        selected = [
            item for item in strategy_evidence if spec["required"] & set(item.get("keywords", []))
        ]
        if len(selected) < 1:
            continue
        if len(selected) < 2:
            selected_ids = {item.get("chunk_id") for item in selected}
            selected.extend(
                item
                for item in strategy_evidence
                if item.get("chunk_id") not in selected_ids
            )
        selected = sorted(
            selected,
            key=lambda item: (-int(item.get("score", 0) or 0), str(item.get("chunk_id", ""))),
        )[:6]
        primary = selected[0]
        node_id = f"situation-strategy::{spec['candidate_id']}"
        nodes.append(
            {
                "id": node_id,
                "type": "situation_strategy_pattern",
                "label": spec["label"],
                "source_file": primary["source_file"],
                "source_location": {"line_start": primary["line_start"], "line_end": primary["line_end"]},
                "extraction_kind": "INFERRED",
                "extractor_kind": "situation-strategy",
                "situation": "complex_decision_under_context",
                "principal_contradiction": "main_constraint_or_conflict_to_focus",
                "force_balance": "available_resources_vs_opposing_constraints",
                "policy_boundary": "left_right_or_over_under_reaction_boundary",
                "action_program": "focused_next_action_program",
                "feedback_loop": "field_feedback_to_policy_adjustment",
                "mechanism": spec["mechanism"],
                "evidence_pack": _build_evidence_pack(selected),
                "transfer_conditions": [
                    "current_situation_is_explicit",
                    "field_or_context_evidence_is_available",
                    "strategy_choice_depends_on_context_fit",
                ],
                "anti_conditions": [
                    "context_transfer_abuse",
                    "pure_author_position_query",
                    "stance_commentary_without_user_decision",
                ],
                "routing_hints": {
                    "workflow_cues": 0,
                    "context_cues": 5,
                    "agentic_priority": 90,
                    "matched_keywords": [*sorted(set().union(*(set(item.get("keywords", [])) for item in selected))), "transfer_conditions", "anti_conditions"],
                    "evidence_chunk_ids": [item["chunk_id"] for item in selected],
                },
            }
        )
        for index, item in enumerate(selected, start=1):
            edges.append(
                {
                    "id": f"situation-strategy-evidence::{spec['candidate_id']}::{index:04d}",
                    "type": "supported_by_evidence",
                    "from": node_id,
                    "to": item["evidence_id"],
                    "source_file": item["source_file"],
                    "source_location": {"line_start": item["line_start"], "line_end": item["line_end"]},
                    "extraction_kind": "EXTRACTED",
                    "confidence": 1.0,
                    "inference_basis": "situation_strategy_support",
                    "chunk_id": item["chunk_id"],
                }
            )


def _build_evidence_pack(items: list[dict[str, Any]]) -> dict[str, Any]:
    anchors = [
        {
            "evidence_id": item.get("evidence_id"),
            "chunk_id": item.get("chunk_id"),
            "source_file": item.get("source_file"),
            "source_location": {
                "line_start": item.get("line_start"),
                "line_end": item.get("line_end"),
            },
            "keywords": item.get("keywords", []),
        }
        for item in items
        if item.get("evidence_id") and item.get("chunk_id")
    ]
    return {
        "schema_version": "kiu.mechanism-evidence-pack/v0.1",
        "source_anchor_count": len(anchors),
        "source_file_count": len(
            {anchor["source_file"] for anchor in anchors if anchor.get("source_file")}
        ),
        "chunk_ids": [anchor["chunk_id"] for anchor in anchors],
        "anchors": anchors,
    }


def _situation_strategy_score(text: str) -> tuple[int, list[str]]:
    cue_patterns = (
        ("investigation", r"(调查|研究|事实|现场|群众|经验|材料|发言权)"),
        ("anti-dogmatism", r"(本本|照搬|教条|过去经验|模板|主观主义|空谈)"),
        ("contradiction", r"(矛盾|主要矛盾|形势|阶段|力量|敌我|问题)"),
        ("strategy", r"(战略|策略|方针|政策|路线|任务|办法|原则|集中优势)"),
        ("boundary", r"(必须|不能|不要|防止|纠正|左|右|错误|边界|独立自主)"),
        ("action", r"(组织|动员|开展|实行|执行|领导|工作|行动|纲领)"),
    )
    matched = [label for label, pattern in cue_patterns if re.search(pattern, text)]
    return len(matched), matched


def _add_role_boundary_pattern_signal(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    role_boundary_evidence: list[dict[str, Any]],
    source_file_count: int,
) -> None:
    if source_file_count < 3 or len(role_boundary_evidence) < 2:
        return
    selected = sorted(
        role_boundary_evidence,
        key=lambda item: (-int(item.get("score", 0) or 0), str(item.get("chunk_id", ""))),
    )[:8]
    primary = selected[0]
    node_id = "narrative-pattern::role-boundary-before-action"
    keywords = sorted(
        {
            keyword
            for item in selected
            for keyword in item.get("keywords", [])
            if isinstance(keyword, str) and keyword
        }
    )
    nodes.append(
        {
            "id": node_id,
            "type": "narrative_pattern_signal",
            "label": "role-boundary-before-action",
            "source_file": primary["source_file"],
            "source_location": {
                "line_start": primary["line_start"],
                "line_end": primary["line_end"],
            },
            "extraction_kind": "INFERRED",
            "extractor_kind": "narrative-pattern",
            "inference_basis": "multi_case_role_authority_boundary_pattern",
            "routing_hints": {
                "workflow_cues": 0,
                "context_cues": 4,
                "matched_keywords": [
                    "role_boundary",
                    "authority",
                    "delegation",
                    "overreach_risk",
                    *keywords[:6],
                ],
                "evidence_chunk_ids": [item["chunk_id"] for item in selected],
            },
        }
    )
    for index, item in enumerate(selected, start=1):
        edges.append(
            {
                "id": f"role-boundary-pattern-evidence::{index:04d}",
                "type": "supported_by_evidence",
                "from": node_id,
                "to": item["evidence_id"],
                "source_file": item["source_file"],
                "source_location": {
                    "line_start": item["line_start"],
                    "line_end": item["line_end"],
                },
                "extraction_kind": "EXTRACTED",
                "confidence": 1.0,
                "inference_basis": "role_authority_boundary_support",
                "chunk_id": item["chunk_id"],
            }
        )


def _role_boundary_decision_score(text: str) -> tuple[int, list[str]]:
    cue_patterns = (
        ("role", r"(臣|君|使者|将|主|相|吏|官|职|任|部|团队|老板|授权|职责|身份)"),
        ("authority", r"(命|令|奉命|受节|授权|权|专断|便宜|请|奏|裁|可|不得|未得)"),
        ("boundary", r"(越|擅|界|分|职分|法度|不宜|不可|不审|失其|坏)"),
        ("consequence", r"(疑|惧|乱|败|祸|诛|坏|失|成|功|卒|遂|故|是以)"),
    )
    matched = [label for label, pattern in cue_patterns if re.search(pattern, text)]
    return len(matched), matched


def _safe_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", raw).strip("-").lower() or "signal"


def _excerpt(text: str, max_chars: int = 72) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _has_case_cue(text: str) -> bool:
    cues = ("例如", "比如", "案例", "故事", "trace")
    return any(cue in text for cue in cues)


def _has_counter_example_cue(text: str) -> bool:
    cues = (
        "反例",
        "误区",
        "失败",
        "错误",
        "不能",
        "不要",
        "只剩",
        "遗漏",
        "重叠",
        "漂移",
        "站不住",
        "退化成代码对代码",
        "无法确认边界是否完整",
    )
    if any(cue in text for cue in cues):
        return True
    return bool(
        re.search(r"如果[^。；\n]{0,36}(错误|失败|偏离|带到|无法确认)", text)
        or re.search(r"只是[^。；\n]{0,24}重新命名", text)
        or re.search(r"当[^。；\n]{0,24}站不住时", text)
        or re.search(r"后续[^。；\n]{0,24}退化成", text)
    )


def _extract_terms(text: str) -> list[str]:
    terms: list[str] = []
    for match in re.findall(r"[（(]([A-Za-z][A-Za-z0-9/ +.-]{2,})[）)]", text):
        term = match.strip()
        if term and term not in terms:
            terms.append(term)
    return terms


def _derive_routing_hints(text: str) -> dict[str, Any]:
    workflow_matches: list[str] = []
    for label, pattern in (
        ("第一步", r"第一步"),
        ("第二步", r"第二步"),
        ("下一步", r"下一步"),
        ("步骤", r"步骤"),
        ("清单", r"清单"),
        ("检查", r"检查"),
        ("预检", r"预检"),
        ("checklist", r"checklist"),
        ("preflight", r"preflight"),
        ("先-再", r"先[^。；\n]{0,24}(再|然后|后)"),
        ("如果-则", r"如果[^。；\n]{0,30}(则|就|需要)"),
    ):
        if re.search(pattern, text, flags=re.IGNORECASE):
            workflow_matches.append(label)

    context_matches = [
        keyword
        for keyword in (
            "场景",
            "边界",
            "接口",
            "输入",
            "输出",
            "职责",
            "目标",
            "约束",
            "业务",
            "失败条件",
        )
        if keyword in text
    ]

    matched_keywords = sorted(set([*workflow_matches, *context_matches]))
    if not matched_keywords:
        return {}
    return {
        "workflow_cues": len(workflow_matches),
        "context_cues": len(context_matches),
        "matched_keywords": matched_keywords,
    }


def _merge_routing_hints(
    node: dict[str, Any],
    *,
    chunk_id: str,
    hints: dict[str, Any],
) -> None:
    if not hints:
        return
    existing = node.get("routing_hints")
    if not isinstance(existing, dict):
        existing = {
            "workflow_cues": 0,
            "context_cues": 0,
            "matched_keywords": [],
            "evidence_chunk_ids": [],
        }
    existing["workflow_cues"] = int(existing.get("workflow_cues", 0) or 0) + int(
        hints.get("workflow_cues", 0) or 0
    )
    existing["context_cues"] = int(existing.get("context_cues", 0) or 0) + int(
        hints.get("context_cues", 0) or 0
    )
    keywords = [
        keyword
        for keyword in [*existing.get("matched_keywords", []), *hints.get("matched_keywords", [])]
        if isinstance(keyword, str) and keyword
    ]
    existing["matched_keywords"] = sorted(set(keywords))
    chunk_ids = [
        evidence_chunk_id
        for evidence_chunk_id in [*existing.get("evidence_chunk_ids", []), chunk_id]
        if isinstance(evidence_chunk_id, str) and evidence_chunk_id
    ]
    existing["evidence_chunk_ids"] = sorted(set(chunk_ids))
    node["routing_hints"] = existing


def _build_llm_extraction_prompt(
    source_chunks_doc: dict[str, Any],
    extraction_result: dict[str, Any],
) -> str:
    chunks = source_chunks_doc.get("chunks", [])
    chunk_summaries = []
    for chunk in chunks[:8]:
        if not isinstance(chunk, dict):
            continue
        chunk_summaries.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "section": chunk.get("section"),
                "line_start": chunk.get("line_start"),
                "line_end": chunk.get("line_end"),
                "chunk_text": chunk.get("chunk_text"),
            }
        )

    prompt_doc = {
        "task": (
            "Add inferred extraction signals as YAML with top-level keys nodes, edges, warnings. "
            "Return only YAML."
        ),
        "source_id": source_chunks_doc.get("source_id"),
        "source_file": source_chunks_doc.get("source_file"),
        "deterministic_pass": extraction_result.get("deterministic_pass"),
        "existing_node_count": len(extraction_result.get("nodes", [])),
        "existing_edge_count": len(extraction_result.get("edges", [])),
        "chunks": chunk_summaries,
    }
    return yaml.safe_dump(prompt_doc, sort_keys=False, allow_unicode=True)
