from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_ria_tv_stage_report(
    *,
    book_overview_doc: dict[str, Any],
    extraction_result: dict[str, Any],
    verification_summary: dict[str, Any],
    generated_skill_count: int,
) -> dict[str, Any]:
    extractor_responsibilities = _build_extractor_responsibilities(extraction_result)
    accepted = [item for item in verification_summary.get("accepted", []) if isinstance(item, dict)]
    rejected = [item for item in verification_summary.get("rejected", []) if isinstance(item, dict)]
    return {
        "schema_version": "kiu.ria-tv-stage-report/v0.1",
        "stage0_book_overview": {
            "present": bool(book_overview_doc),
            "chapter_count": book_overview_doc.get("chapter_count", 0),
            "domain_tags": list(book_overview_doc.get("domain_tags", [])),
        },
        "stage1_parallel_extractors": {
            "present": bool(extractor_responsibilities),
            "extractor_responsibilities": extractor_responsibilities,
        },
        "stage1_5_triple_verification": {
            "present": bool(accepted or rejected),
            "accepted_candidate_count": len(accepted),
            "rejected_candidate_count": len(rejected),
        },
        "stage2_skill_distillation": {
            "present": True,
            "generated_skill_count": generated_skill_count,
        },
        "stage3_linking": {
            "present": True,
            "evidence": "relations and graph anchors are rendered into candidate metadata",
        },
        "stage4_pressure_test": {
            "present": True,
            "evidence": "smoke usage and boundary/refusal scenario families are generated when candidates exist",
        },
    }


def write_ria_tv_stage_report(
    *,
    run_root: str | Path,
    report: dict[str, Any],
) -> Path:
    path = Path(run_root) / "reports" / "ria-tv-stage-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _build_extractor_responsibilities(extraction_result: dict[str, Any]) -> dict[str, Any]:
    responsibilities: dict[str, Any] = {}
    for stage in extraction_result.get("extractor_run_log", []):
        if not isinstance(stage, dict):
            continue
        kind = str(stage.get("extractor_kind") or "")
        if not kind:
            continue
        responsibilities[kind] = {
            "owner": kind,
            "pass_kind": stage.get("pass_kind"),
            "input_chunk_ids": list(stage.get("input_chunk_ids", [])),
            "output_node_ids": list(stage.get("output_node_ids", [])),
            "output_edge_ids": list(stage.get("output_edge_ids", [])),
            "evidence_count": len(stage.get("output_node_ids", [])) + len(stage.get("output_edge_ids", [])),
            "rejection_count": 0,
        }
    return responsibilities


def build_skill_ria_tv_provenance(
    *,
    graph_doc: dict[str, Any],
    primary_node_id: str,
    supporting_node_ids: list[str],
    supporting_edge_ids: list[str],
) -> dict[str, Any]:
    node_ids = _unique([primary_node_id, *supporting_node_ids])
    edge_ids = _unique(supporting_edge_ids)
    nodes = {str(node.get("id")): node for node in graph_doc.get("nodes", []) if isinstance(node, dict)}
    edges = {str(edge.get("id")): edge for edge in graph_doc.get("edges", []) if isinstance(edge, dict)}
    extractor_kinds = sorted(
        {
            _normalize_extractor_kind(str(value))
            for value in [
                *(nodes.get(node_id, {}).get("extractor_kind") for node_id in node_ids),
                *(nodes.get(node_id, {}).get("type") for node_id in node_ids),
                *(edges.get(edge_id, {}).get("extractor_kind") for edge_id in edge_ids),
            ]
            if value
        }
    )
    return {
        "schema_version": "kiu.ria-tv-provenance/v0.1",
        "available_extractors": extractor_kinds,
        "source_node_ids": node_ids,
        "source_edge_ids": edge_ids,
        "source_locations": _source_locations(nodes, edges, node_ids, edge_ids),
    }


def build_workflow_gateway_provenance(*, routed_ids: list[str], source_node_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "kiu.workflow-gateway-provenance/v0.1",
        "routes_to": sorted(_unique(routed_ids)),
        "source_node_ids": _unique(source_node_ids),
        "boundary": "thin_gateway_only_not_cangjie_thick_skill",
    }


def _source_locations(
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
    node_ids: list[str],
    edge_ids: list[str],
) -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []
    for item in [*(nodes.get(node_id, {}) for node_id in node_ids), *(edges.get(edge_id, {}) for edge_id in edge_ids)]:
        source_file = item.get("source_file")
        source_location = item.get("source_location")
        if source_file or source_location:
            locations.append({"source_file": source_file, "source_location": source_location})
    return locations


def _normalize_extractor_kind(value: str) -> str:
    normalized = value.strip().replace("_", "-").lower()
    if normalized in {"counterexample", "counter-example", "counter example"}:
        return "counter-example"
    if "framework" in normalized:
        return "framework"
    if "principle" in normalized:
        return "principle"
    if "case" in normalized and "counter" not in normalized:
        return "case"
    if "term" in normalized:
        return "term"
    if "evidence" in normalized:
        return "evidence"
    return normalized


def _unique(values: list[str | None]) -> list[str]:
    result: list[str] = []
    for value in values:
        if not value:
            continue
        value = str(value)
        if value not in result:
            result.append(value)
    return result
