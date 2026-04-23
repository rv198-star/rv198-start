from __future__ import annotations

from typing import Any

from .extraction import (
    apply_llm_extraction_patch,
    build_empty_extraction_result,
    build_heuristic_extraction_result,
    build_section_heading_extraction_result,
)
from .extractor_prompts import (
    EXTRACTOR_PROMPT_REGISTRY_VERSION,
    get_deterministic_stage_catalog,
    get_llm_patch_stage_metadata,
)


def build_extraction_result_with_audit(
    *,
    source_chunks_doc: dict[str, Any],
    deterministic_pass: str,
    drafting_mode: str = "deterministic",
    llm_budget_tokens: int = 6000,
) -> dict[str, Any]:
    extraction_result = _run_deterministic_pass(
        source_chunks_doc=source_chunks_doc,
        deterministic_pass=deterministic_pass,
    )
    _attach_deterministic_stage_log(
        source_chunks_doc=source_chunks_doc,
        extraction_result=extraction_result,
        deterministic_pass=deterministic_pass,
    )

    if drafting_mode == "llm-assisted":
        before_node_ids = {
            node.get("id")
            for node in extraction_result.get("nodes", [])
            if isinstance(node, dict) and node.get("id")
        }
        before_edge_ids = {
            edge.get("id")
            for edge in extraction_result.get("edges", [])
            if isinstance(edge, dict) and edge.get("id")
        }
        extraction_result = apply_llm_extraction_patch(
            source_chunks_doc=source_chunks_doc,
            extraction_result=extraction_result,
            token_budget=llm_budget_tokens,
        )
        _append_llm_patch_stage_log(
            source_chunks_doc=source_chunks_doc,
            extraction_result=extraction_result,
            before_node_ids=before_node_ids,
            before_edge_ids=before_edge_ids,
        )

    return extraction_result


def _run_deterministic_pass(
    *,
    source_chunks_doc: dict[str, Any],
    deterministic_pass: str,
) -> dict[str, Any]:
    if deterministic_pass == "empty-shell":
        return build_empty_extraction_result(source_chunks_doc)
    if deterministic_pass == "section-headings":
        return build_section_heading_extraction_result(source_chunks_doc)
    if deterministic_pass == "heuristic-extractors":
        return build_heuristic_extraction_result(source_chunks_doc)
    raise ValueError(f"unsupported deterministic_pass: {deterministic_pass}")


def _attach_deterministic_stage_log(
    *,
    source_chunks_doc: dict[str, Any],
    extraction_result: dict[str, Any],
    deterministic_pass: str,
) -> None:
    stage_catalog = get_deterministic_stage_catalog(deterministic_pass)
    chunk_ids = [
        chunk.get("chunk_id")
        for chunk in source_chunks_doc.get("chunks", [])
        if isinstance(chunk, dict) and isinstance(chunk.get("chunk_id"), str) and chunk.get("chunk_id")
    ]
    extraction_result["extractor_prompt_registry_version"] = EXTRACTOR_PROMPT_REGISTRY_VERSION
    extraction_result["extractor_run_log"] = [
        {
            **stage,
            "stage_id": f"{stage['pass_kind']}::{stage['extractor_kind']}",
            "input_chunk_ids": _derive_stage_input_chunk_ids(
                stage=stage,
                chunk_ids=chunk_ids,
                extraction_result=extraction_result,
            ),
            "output_node_ids": _derive_stage_output_node_ids(
                stage=stage,
                extraction_result=extraction_result,
            ),
            "output_edge_ids": _derive_stage_output_edge_ids(
                stage=stage,
                extraction_result=extraction_result,
            ),
        }
        for stage in stage_catalog
    ]


def _append_llm_patch_stage_log(
    *,
    source_chunks_doc: dict[str, Any],
    extraction_result: dict[str, Any],
    before_node_ids: set[str],
    before_edge_ids: set[str],
) -> None:
    stage = get_llm_patch_stage_metadata()
    chunk_ids = [
        chunk.get("chunk_id")
        for chunk in source_chunks_doc.get("chunks", [])
        if isinstance(chunk, dict) and isinstance(chunk.get("chunk_id"), str) and chunk.get("chunk_id")
    ]
    stage["stage_id"] = f"{stage['pass_kind']}::{stage['extractor_kind']}"
    stage["input_chunk_ids"] = chunk_ids
    stage["output_node_ids"] = sorted(
        node.get("id")
        for node in extraction_result.get("nodes", [])
        if isinstance(node, dict) and node.get("id") and node.get("id") not in before_node_ids
    )
    stage["output_edge_ids"] = sorted(
        edge.get("id")
        for edge in extraction_result.get("edges", [])
        if isinstance(edge, dict) and edge.get("id") and edge.get("id") not in before_edge_ids
    )
    extraction_result.setdefault("extractor_run_log", []).append(stage)


def _derive_stage_input_chunk_ids(
    *,
    stage: dict[str, Any],
    chunk_ids: list[str],
    extraction_result: dict[str, Any],
) -> list[str]:
    extractor_kind = stage.get("extractor_kind")
    if extractor_kind in {"framework", "principle", "section-headings", "empty-shell", "llm-patch"}:
        return chunk_ids
    matched_chunk_ids = {
        node.get("chunk_id")
        for node in extraction_result.get("nodes", [])
        if isinstance(node, dict)
        and node.get("extractor_kind") == extractor_kind
        and isinstance(node.get("chunk_id"), str)
        and node.get("chunk_id")
    }
    matched_chunk_ids.update(
        edge.get("chunk_id")
        for edge in extraction_result.get("edges", [])
        if isinstance(edge, dict)
        and isinstance(edge.get("chunk_id"), str)
        and edge.get("chunk_id")
        and _edge_matches_extractor_kind(edge=edge, extractor_kind=str(extractor_kind), extraction_result=extraction_result)
    )
    if matched_chunk_ids:
        return sorted(matched_chunk_ids)
    return chunk_ids


def _derive_stage_output_node_ids(
    *,
    stage: dict[str, Any],
    extraction_result: dict[str, Any],
) -> list[str]:
    extractor_kind = stage.get("extractor_kind")
    if extractor_kind == "section-headings":
        return sorted(
            node.get("id")
            for node in extraction_result.get("nodes", [])
            if isinstance(node, dict) and node.get("type") == "source_section" and node.get("id")
        )
    if extractor_kind == "empty-shell":
        return []
    return sorted(
        node.get("id")
        for node in extraction_result.get("nodes", [])
        if isinstance(node, dict)
        and node.get("extractor_kind") == extractor_kind
        and node.get("id")
    )


def _derive_stage_output_edge_ids(
    *,
    stage: dict[str, Any],
    extraction_result: dict[str, Any],
) -> list[str]:
    extractor_kind = str(stage.get("extractor_kind"))
    if extractor_kind == "section-headings":
        return sorted(
            edge.get("id")
            for edge in extraction_result.get("edges", [])
            if isinstance(edge, dict) and edge.get("type") == "next_section" and edge.get("id")
        )
    if extractor_kind == "empty-shell":
        return []
    return sorted(
        edge.get("id")
        for edge in extraction_result.get("edges", [])
        if isinstance(edge, dict)
        and edge.get("id")
        and _edge_matches_extractor_kind(
            edge=edge,
            extractor_kind=extractor_kind,
            extraction_result=extraction_result,
        )
    )


def _edge_matches_extractor_kind(
    *,
    edge: dict[str, Any],
    extractor_kind: str,
    extraction_result: dict[str, Any],
) -> bool:
    node_by_id = {
        node.get("id"): node
        for node in extraction_result.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    source_kind = node_by_id.get(edge.get("from"), {}).get("extractor_kind")
    target_kind = node_by_id.get(edge.get("to"), {}).get("extractor_kind")
    if source_kind == extractor_kind or target_kind == extractor_kind:
        return True
    edge_type = str(edge.get("type", ""))
    if extractor_kind == "evidence":
        return edge_type == "supported_by_evidence"
    if extractor_kind == "case":
        return edge_type in {"illustrated_by_case", "derives_case_signal"}
    if extractor_kind == "counter-example":
        return edge_type in {"flags_counter_example", "derives_counter_example_signal"}
    if extractor_kind == "term":
        return edge_type in {"mentions_term", "derives_term_signal"}
    if extractor_kind == "framework":
        return edge_type == "section_parent" and target_kind == "principle"
    return False
