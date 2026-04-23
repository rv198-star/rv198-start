from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .preflight import validate_generated_bundle
from kiu_validator.core import validate_bundle

GENERIC_NEXT_ACTIONS = {
    "collect_more_info",
    "gather_more_info",
    "review_more",
    "review_source_evidence",
}


def review_generated_run(
    *,
    run_root: str | Path,
    source_bundle_path: str | Path,
    usage_review_dir: str | Path | None = None,
) -> dict[str, Any]:
    run_root = Path(run_root)
    bundle_root = run_root / "bundle"
    usage_root = Path(usage_review_dir) if usage_review_dir is not None else run_root / "usage-review"

    source_report = validate_bundle(source_bundle_path)
    generated_report = validate_generated_bundle(bundle_root)
    metrics = _load_json(run_root / "reports" / "metrics.json")
    production_quality = _load_json(run_root / "reports" / "production-quality.json")
    usage_docs = _load_usage_reviews(usage_root)
    usage_docs = [
        doc
        for doc in usage_docs
        if _belongs_to_run(doc, run_root)
    ]

    source_bundle = _score_source_bundle(
        report=source_report,
        source_bundle_path=source_bundle_path,
        run_root=run_root,
    )
    generated_bundle = _score_generated_bundle(
        generated_report=generated_report,
        production_quality=production_quality,
        metrics=metrics,
        run_root=run_root,
    )
    usage_outputs = _score_usage_outputs(usage_docs)

    overall_score = round(
        0.30 * source_bundle["score_100"]
        + 0.40 * generated_bundle["score_100"]
        + 0.30 * usage_outputs["score_100"],
        1,
    )
    release_gate = _derive_release_gate(
        source_bundle=source_bundle,
        generated_bundle=generated_bundle,
        usage_outputs=usage_outputs,
    )

    return {
        "run_root": str(run_root),
        "source_bundle_path": str(Path(source_bundle_path)),
        "usage_review_dir": str(usage_root),
        "source_bundle": source_bundle,
        "generated_bundle": generated_bundle,
        "usage_outputs": usage_outputs,
        "release_gate": release_gate,
        "overall_score_100": overall_score,
    }


def _score_source_bundle(
    *,
    report: dict[str, Any],
    source_bundle_path: str | Path,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    errors = report.get("errors", [])
    warnings = report.get("warnings", [])
    graph = report.get("graph", {})
    shared = report.get("shared_assets", {})
    manifest = report.get("manifest", {})
    skills = report.get("skills", [])
    artifact_doc = _inspect_source_bundle_artifacts(
        source_bundle_path=source_bundle_path,
        manifest=manifest,
    )
    source_bundle_kind = _detect_source_bundle_kind(
        manifest=manifest,
        skills=skills,
        artifact_doc=artifact_doc,
    )
    tri_state_effectiveness = _inspect_tri_state_effectiveness(
        source_bundle_path=source_bundle_path,
        run_root=run_root,
    )

    structural_cleanliness = max(0.0, 1.0 - 0.25 * len(errors))
    warning_cleanliness = max(0.0, 1.0 - 0.10 * len(warnings))
    notes: list[str] = []

    if source_bundle_kind == "raw_book_source_bundle":
        node_prov = _ratio(
            [
                artifact_doc["provenance"]["nodes"]["source_file_ratio"],
                artifact_doc["provenance"]["nodes"]["source_location_ratio"],
                artifact_doc["provenance"]["nodes"]["extraction_kind_ratio"],
            ]
        )
        edge_prov = _ratio(
            [
                artifact_doc["provenance"]["edges"]["source_file_ratio"],
                artifact_doc["provenance"]["edges"]["source_location_ratio"],
                artifact_doc["provenance"]["edges"]["extraction_kind_ratio"],
                artifact_doc["provenance"]["edges"]["confidence_ratio"],
            ]
        )
        provenance_factor = _ratio([node_prov, edge_prov])
        extraction_kind_counts = artifact_doc["provenance"]["extraction_kind_counts"]
        tri_state_density_ratio = _score_tri_state_density(extraction_kind_counts)
        graph_navigation_factor = _ratio(
            [
                1.0 if graph.get("community_count", 0) > 0 else 0.0,
                1.0 if artifact_doc["graph_report_present"] else 0.0,
            ]
        )
        ingestion_factor = _ratio(
            [
                1.0 if artifact_doc["source_snapshot_present"] else 0.0,
                1.0 if artifact_doc["source_chunks_present"] else 0.0,
            ]
        )
        evidence_pool_factor = _ratio(
            [
                1.0 if shared.get("trace_count", 0) > 0 else 0.0,
                1.0 if shared.get("evaluation_count", 0) > 0 else 0.0,
            ]
        )
        score = round(
            100.0
            * (
                0.20 * structural_cleanliness
                + 0.05 * warning_cleanliness
                + 0.25 * provenance_factor
                + 0.10 * tri_state_density_ratio
                + 0.10 * tri_state_effectiveness["overall_ratio"]
                + 0.10 * graph_navigation_factor
                + 0.10 * ingestion_factor
                + 0.10 * evidence_pool_factor
            ),
            1,
        )
        if not errors and not warnings:
            notes.append("validator_clean")
        if artifact_doc["graph_report_present"]:
            notes.append("graph_report_present")
        if provenance_factor == 1.0:
            notes.append("provenance_graph_complete")
        if ingestion_factor == 1.0:
            notes.append("source_ingestion_trace_present")
        if tri_state_effectiveness["overall_ratio"] > 0.0:
            notes.append("tri_state_effective")
        if tri_state_density_ratio < 1.0:
            notes.append("tri_state_density_partial")
        if evidence_pool_factor == 1.0:
            notes.append("shared_evidence_pool_present")
        return {
            "score_100": score,
            "errors": len(errors),
            "warnings": len(warnings),
            "skill_count": len(manifest.get("skills", [])),
            "graph": graph,
            "shared_assets": shared,
            "source_bundle_kind": source_bundle_kind,
            "provenance": artifact_doc["provenance"],
            "tri_state_density_ratio": round(tri_state_density_ratio, 4),
            "tri_state_effectiveness": tri_state_effectiveness,
            "graph_report_present": artifact_doc["graph_report_present"],
            "source_chunks_present": artifact_doc["source_chunks_present"],
            "source_snapshot_present": artifact_doc["source_snapshot_present"],
            "notes": notes,
        }

    graph_factor = _ratio(
        [
            1.0 if graph.get("node_count", 0) > 0 else 0.0,
            1.0 if graph.get("edge_count", 0) > 0 else 0.0,
            1.0 if graph.get("community_count", 0) > 0 else 0.0,
        ]
    )
    asset_factor = _ratio(
        [
            1.0 if len(manifest.get("skills", [])) > 0 else 0.0,
            1.0 if shared.get("trace_count", 0) > 0 else 0.0,
            1.0 if shared.get("evaluation_count", 0) > 0 else 0.0,
        ]
    )
    maturity_factor = _score_source_skill_maturity(skills)
    score = round(
        100.0
        * (
            0.40 * structural_cleanliness
            + 0.10 * warning_cleanliness
            + 0.10 * graph_factor
            + 0.15 * asset_factor
            + 0.25 * maturity_factor
        ),
        1,
    )
    if not errors and not warnings:
        notes.append("validator_clean")
    if shared.get("trace_count", 0) > 0 and shared.get("evaluation_count", 0) > 0:
        notes.append("shared_evidence_pool_present")
    if artifact_doc["graph_report_present"]:
        notes.append("graph_report_present")
    if _ratio(
        [
            artifact_doc["provenance"]["nodes"]["source_file_ratio"],
            artifact_doc["provenance"]["nodes"]["source_location_ratio"],
            artifact_doc["provenance"]["nodes"]["extraction_kind_ratio"],
            artifact_doc["provenance"]["edges"]["source_file_ratio"],
            artifact_doc["provenance"]["edges"]["source_location_ratio"],
            artifact_doc["provenance"]["edges"]["extraction_kind_ratio"],
            artifact_doc["provenance"]["edges"]["confidence_ratio"],
        ]
    ) == 1.0:
        notes.append("provenance_graph_complete")

    return {
        "score_100": score,
        "errors": len(errors),
        "warnings": len(warnings),
        "skill_count": len(manifest.get("skills", [])),
        "graph": graph,
        "shared_assets": shared,
        "source_bundle_kind": source_bundle_kind,
        "provenance": artifact_doc["provenance"],
        "tri_state_effectiveness": tri_state_effectiveness,
        "graph_report_present": artifact_doc["graph_report_present"],
        "source_chunks_present": artifact_doc["source_chunks_present"],
        "source_snapshot_present": artifact_doc["source_snapshot_present"],
        "maturity_factor": round(maturity_factor, 4),
        "notes": notes,
    }


def _score_generated_bundle(
    *,
    generated_report: dict[str, Any],
    production_quality: dict[str, Any],
    metrics: dict[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    errors = generated_report.get("errors", [])
    warnings = generated_report.get("warnings", [])
    workflow_count = int(metrics.get("summary", {}).get("workflow_script_candidates", 0) or 0)
    workflow_dirs = len(
        [path for path in (run_root / "workflow_candidates").glob("*") if path.is_dir()]
    ) if (run_root / "workflow_candidates").exists() else 0
    boundary_preserved = workflow_count == 0 or workflow_dirs == workflow_count
    verification_doc = _load_json(run_root / "reports" / "verification-summary.json")
    verification_gate_present = bool(verification_doc)
    workflow_ready_ratio = _workflow_verification_ready_ratio(
        verification_doc=verification_doc,
        workflow_count=workflow_count,
    )

    structural_cleanliness = max(0.0, 1.0 - 0.25 * len(errors) - 0.05 * len(warnings))
    minimum_production = float(production_quality.get("minimum_production_quality", 0.0) or 0.0)
    average_production = float(production_quality.get("average_production_quality", 0.0) or 0.0)
    workflow_boundary_factor = 1.0 if boundary_preserved else 0.0
    score = round(
        100.0
        * (
            0.55 * minimum_production
            + 0.10 * average_production
            + 0.10 * structural_cleanliness
            + 0.10 * workflow_boundary_factor
            + 0.05 * (1.0 if verification_gate_present else 0.0)
            + 0.10 * workflow_ready_ratio
        ),
        1,
    )

    notes: list[str] = []
    if production_quality.get("bundle_quality_grade") == "excellent":
        notes.append("production_quality_excellent")
    if workflow_count > 0 and boundary_preserved:
        notes.append("workflow_boundary_preserved")
    if workflow_count > 0 and not boundary_preserved:
        notes.append("workflow_boundary_drift")
    if verification_gate_present:
        notes.append("verification_gate_present")
    if workflow_count > 0 and workflow_ready_ratio < 1.0:
        notes.append("workflow_verification_partial")

    return {
        "score_100": score,
        "errors": len(errors),
        "warnings": len(warnings),
        "skill_count": int(production_quality.get("candidate_count", 0) or 0),
        "workflow_candidate_count": workflow_count,
        "bundle_quality_grade": production_quality.get("bundle_quality_grade"),
        "minimum_production_quality": minimum_production,
        "average_production_quality": average_production,
        "verification_gate_present": verification_gate_present,
        "workflow_verification_ready_ratio": workflow_ready_ratio,
        "notes": notes,
    }


def _score_usage_outputs(docs: list[dict[str, Any]]) -> dict[str, Any]:
    scored_docs = [_score_usage_doc(doc) for doc in docs if _is_skill_usage_doc(doc)]
    if not scored_docs:
        return {
            "score_100": 0.0,
            "sample_count": 0,
            "notes": ["no_skill_usage_reviews_found"],
            "failure_tag_counts": {},
            "top_failure_modes": [],
            "severity_counts": {},
            "critical_failure_count": 0,
            "usage_gate_ready": False,
            "usage_gate_reasons": ["no_usage_reviews"],
            "samples": [],
        }

    average_doc_score = sum(item["score_100"] for item in scored_docs) / len(scored_docs)
    coverage_factor = min(len(scored_docs) / 3.0, 1.0)
    score = round(0.85 * average_doc_score + 15.0 * coverage_factor, 1)
    failure_tag_counts = _aggregate_counts(
        item.get("failure_analysis", {}).get("tag_counts", {})
        if isinstance(item.get("failure_analysis"), dict)
        else {}
        for item in scored_docs
    )
    severity_counts = _aggregate_counts(
        (
            {str(item.get("failure_analysis", {}).get("severity", "none")): 1}
            if isinstance(item.get("failure_analysis"), dict)
            else {}
        )
        for item in scored_docs
    )
    usage_gate_reasons: list[str] = []
    if score < 75.0:
        usage_gate_reasons.append("usage_score_below_bar")
    if failure_tag_counts.get("boundary_leak", 0) > 0:
        usage_gate_reasons.append("boundary_leak_detected")
    if failure_tag_counts.get("next_step_blunt", 0) > 0:
        usage_gate_reasons.append("next_step_quality_weak")
    if int(severity_counts.get("critical", 0) or 0) > 0:
        usage_gate_reasons.append("critical_usage_failure_present")
    usage_gate_ready = not usage_gate_reasons
    return {
        "score_100": score,
        "sample_count": len(scored_docs),
        "notes": ["usage_reviews_scored"] + (["usage_gate_blocked"] if not usage_gate_ready else []),
        "failure_tag_counts": failure_tag_counts,
        "top_failure_modes": _top_items(failure_tag_counts),
        "severity_counts": severity_counts,
        "critical_failure_count": int(severity_counts.get("critical", 0) or 0),
        "usage_gate_ready": usage_gate_ready,
        "usage_gate_reasons": usage_gate_reasons,
        "samples": scored_docs,
    }


def _score_usage_doc(doc: dict[str, Any]) -> dict[str, Any]:
    quality = doc.get("quality_assessment", {})
    structured_output = doc.get("structured_output", {})
    contract_fit_map = {
        "strong": 1.0,
        "medium": 0.75,
        "weak": 0.45,
    }
    contract_fit = contract_fit_map.get(str(quality.get("contract_fit", "")).lower(), 0.4)

    boundary_status = str(doc.get("boundary_check", {}).get("status", "")).lower()
    boundary_score = {
        "pass": 1.0,
        "warning": 0.6,
        "fail": 0.2,
    }.get(boundary_status, 0.4)

    structured_score = min(len(structured_output) / 3.0, 1.0) if structured_output else 0.0
    evidence_score = min(len(quality.get("evidence_alignment", []) or []) / 3.0, 1.0)

    scenario_score = 0.0
    if isinstance(doc.get("input_scenario"), dict) and doc["input_scenario"]:
        scenario_score += 0.5
    if doc.get("analysis_summary"):
        scenario_score += 0.25
    firing = doc.get("firing_assessment", {})
    if isinstance(firing, dict) and "should_fire" in firing:
        scenario_score += 0.25

    score = round(
        100.0
        * (
            0.30 * contract_fit
            + 0.20 * boundary_score
            + 0.20 * structured_score
            + 0.15 * evidence_score
            + 0.15 * min(scenario_score, 1.0)
        ),
        1,
    )
    failure_analysis = _score_usage_failure_analysis(
        doc=doc,
        score_100=score,
        contract_fit=contract_fit,
        boundary_status=boundary_status,
        evidence_score=evidence_score,
    )
    return {
        "review_case_id": doc.get("review_case_id", "<missing-review-case-id>"),
        "score_100": score,
        "skill_path": doc.get("skill_path"),
        "failure_analysis": failure_analysis,
    }


def _is_skill_usage_doc(doc: dict[str, Any]) -> bool:
    return bool(doc.get("skill_path")) and isinstance(doc.get("structured_output"), dict)


def _load_usage_reviews(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    docs: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yaml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            loaded["_path"] = str(path)
            docs.append(loaded)
    return docs


def _belongs_to_run(doc: dict[str, Any], run_root: Path) -> bool:
    generated_run_root = doc.get("generated_run_root")
    if not generated_run_root:
        return True
    try:
        return Path(generated_run_root).resolve() == run_root.resolve()
    except OSError:
        return False


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _workflow_verification_ready_ratio(
    *,
    verification_doc: dict[str, Any],
    workflow_count: int,
) -> float:
    if workflow_count <= 0:
        return 1.0
    accepted = verification_doc.get("accepted", [])
    if not isinstance(accepted, list) or not accepted:
        return 0.0
    ready = 0
    workflow_total = 0
    for item in accepted:
        if not isinstance(item, dict):
            continue
        if item.get("disposition") != "workflow_script_candidate":
            continue
        workflow_total += 1
        verification = item.get("verification", {})
        if isinstance(verification, dict) and verification.get("workflow_ready"):
            ready += 1
    denominator = workflow_total if workflow_total > 0 else workflow_count
    return _safe_ratio(ready, denominator)


def _score_usage_failure_analysis(
    *,
    doc: dict[str, Any],
    score_100: float,
    contract_fit: float,
    boundary_status: str,
    evidence_score: float,
) -> dict[str, Any]:
    structured_output = doc.get("structured_output", {})
    next_action = str(structured_output.get("next_action", "") or "").strip().lower()
    analysis_summary = str(doc.get("analysis_summary", "") or "").strip()

    tags: list[str] = []
    if contract_fit <= 0.45:
        tags.append("trigger_miss")
    if boundary_status in {"warning", "fail"}:
        tags.append("boundary_leak")
    if not next_action or next_action in GENERIC_NEXT_ACTIONS:
        tags.append("next_step_blunt")
    if len(analysis_summary) < 12 or evidence_score <= 0.0:
        tags.append("generic_reasoning")

    severity = "none"
    if boundary_status == "fail":
        severity = "critical"
    elif boundary_status == "warning" or len(tags) >= 2 or score_100 < 60.0:
        severity = "major"
    elif tags:
        severity = "minor"
    return {
        "tags": tags,
        "tag_counts": {tag: 1 for tag in tags},
        "severity": severity,
    }


def _derive_release_gate(
    *,
    source_bundle: dict[str, Any],
    generated_bundle: dict[str, Any],
    usage_outputs: dict[str, Any],
) -> dict[str, Any]:
    source_bundle_ready = int(source_bundle.get("errors", 0) or 0) == 0
    generated_bundle_ready = (
        int(generated_bundle.get("errors", 0) or 0) == 0
        and float(generated_bundle.get("minimum_production_quality", 0.0) or 0.0) >= 0.78
        and (
            generated_bundle.get("workflow_candidate_count", 0) == 0
            or "workflow_boundary_preserved" in generated_bundle.get("notes", [])
        )
    )
    usage_gate_ready = bool(usage_outputs.get("usage_gate_ready"))
    reasons: list[str] = []
    if not source_bundle_ready:
        reasons.append("source_bundle_not_ready")
    if not generated_bundle_ready:
        reasons.append("generated_bundle_not_ready")
    if not usage_gate_ready:
        reasons.append("usage_gate_not_ready")
        reasons.extend(
            reason
            for reason in usage_outputs.get("usage_gate_reasons", [])
            if isinstance(reason, str)
        )
    return {
        "source_bundle_ready": source_bundle_ready,
        "generated_bundle_ready": generated_bundle_ready,
        "usage_gate_ready": usage_gate_ready,
        "overall_ready": source_bundle_ready and generated_bundle_ready and usage_gate_ready,
        "reasons": reasons,
    }


def _aggregate_counts(count_docs: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for count_doc in count_docs:
        if not isinstance(count_doc, dict):
            continue
        for key, value in count_doc.items():
            if not isinstance(key, str) or not key:
                continue
            counts[key] = counts.get(key, 0) + int(value or 0)
    return {
        key: counts[key]
        for key in sorted(counts, key=lambda item: (-counts[item], item))
        if counts[key] > 0
    }


def _top_items(counts: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"name": key, "count": value}
        for key, value in counts.items()
    ][:5]


def _inspect_source_bundle_artifacts(
    *,
    source_bundle_path: str | Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    root = Path(source_bundle_path)
    graph_meta = manifest.get("graph", {}) if isinstance(manifest.get("graph"), dict) else {}
    graph_path = root / graph_meta.get("path", "graph/graph.json")
    graph_doc = _load_json(graph_path)
    nodes = [node for node in graph_doc.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph_doc.get("edges", []) if isinstance(edge, dict)]
    graph_report_meta = (
        manifest.get("graph_report", {})
        if isinstance(manifest.get("graph_report"), dict)
        else {}
    )
    graph_report_path = root / graph_report_meta.get("path", "GRAPH_REPORT.md")
    source_chunks_path = root / "ingestion" / "source-chunks-v0.1.json"
    sources_root = root / "sources"
    return {
        "graph_report_present": graph_report_path.exists(),
        "source_chunks_present": source_chunks_path.exists(),
        "source_snapshot_present": sources_root.exists() and any(sources_root.glob("*")),
        "provenance": {
            "nodes": _graph_entity_stats(nodes, entity_type="node"),
            "edges": _graph_entity_stats(edges, entity_type="edge"),
            "extraction_kind_counts": _count_extraction_kinds(graph_doc),
        },
    }


def _inspect_tri_state_effectiveness(
    *,
    source_bundle_path: str | Path,
    run_root: str | Path | None,
) -> dict[str, Any]:
    if run_root is None:
        return {
            "candidate_count": 0,
            "candidates_using_tri_state": 0,
            "candidate_coverage_ratio": 0.0,
            "inferred_edge_reference_ratio": 0.0,
            "ambiguous_node_reference_ratio": 0.0,
            "ambiguous_edge_reference_ratio": 0.0,
            "overall_ratio": 0.0,
        }

    root = Path(source_bundle_path)
    manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8")) or {}
    graph_path = root / manifest.get("graph", {}).get("path", "graph/graph.json")
    graph_doc = _load_json(graph_path)

    inferred_edge_ids = {
        edge["id"]
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict) and edge.get("extraction_kind") == "INFERRED" and edge.get("id")
    }
    ambiguous_edge_ids = {
        edge["id"]
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict) and edge.get("extraction_kind") == "AMBIGUOUS" and edge.get("id")
    }
    ambiguous_node_ids = {
        node["id"]
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("extraction_kind") == "AMBIGUOUS" and node.get("id")
    }

    run_path = Path(run_root)
    candidate_paths = sorted((run_path / "bundle" / "skills").glob("*/candidate.yaml"))
    candidate_paths.extend(sorted((run_path / "workflow_candidates").glob("*/candidate.yaml")))

    referenced_inferred_edge_ids: set[str] = set()
    referenced_ambiguous_edge_ids: set[str] = set()
    referenced_ambiguous_node_ids: set[str] = set()
    candidates_using_tri_state = 0

    for candidate_path in candidate_paths:
        loaded = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
        seed = loaded.get("seed", {}) if isinstance(loaded, dict) else {}
        primary_node_id = seed.get("primary_node_id")
        supporting_node_ids = [
            node_id
            for node_id in seed.get("supporting_node_ids", [])
            if isinstance(node_id, str) and node_id
        ]
        supporting_edge_ids = [
            edge_id
            for edge_id in seed.get("supporting_edge_ids", [])
            if isinstance(edge_id, str) and edge_id
        ]
        candidate_node_ids = {
            node_id
            for node_id in [primary_node_id, *supporting_node_ids]
            if isinstance(node_id, str) and node_id
        }

        matched_inferred_edge_ids = set(supporting_edge_ids) & inferred_edge_ids
        matched_ambiguous_edge_ids = set(supporting_edge_ids) & ambiguous_edge_ids
        matched_ambiguous_node_ids = candidate_node_ids & ambiguous_node_ids

        referenced_inferred_edge_ids.update(matched_inferred_edge_ids)
        referenced_ambiguous_edge_ids.update(matched_ambiguous_edge_ids)
        referenced_ambiguous_node_ids.update(matched_ambiguous_node_ids)

        if matched_inferred_edge_ids or matched_ambiguous_edge_ids or matched_ambiguous_node_ids:
            candidates_using_tri_state += 1

    candidate_count = len(candidate_paths)
    candidate_coverage_ratio = _safe_ratio(candidates_using_tri_state, candidate_count)
    inferred_edge_reference_ratio = _safe_ratio(
        len(referenced_inferred_edge_ids),
        len(inferred_edge_ids),
    )
    ambiguous_node_reference_ratio = _safe_ratio(
        len(referenced_ambiguous_node_ids),
        len(ambiguous_node_ids),
    )
    ambiguous_edge_reference_ratio = _safe_ratio(
        len(referenced_ambiguous_edge_ids),
        len(ambiguous_edge_ids),
    )
    overall_ratio = _ratio(
        [
            candidate_coverage_ratio,
            inferred_edge_reference_ratio,
            ambiguous_node_reference_ratio,
            ambiguous_edge_reference_ratio,
        ]
    )
    return {
        "candidate_count": candidate_count,
        "candidates_using_tri_state": candidates_using_tri_state,
        "candidate_coverage_ratio": round(candidate_coverage_ratio, 4),
        "inferred_edge_reference_ratio": round(inferred_edge_reference_ratio, 4),
        "ambiguous_node_reference_ratio": round(ambiguous_node_reference_ratio, 4),
        "ambiguous_edge_reference_ratio": round(ambiguous_edge_reference_ratio, 4),
        "overall_ratio": round(overall_ratio, 4),
    }


def _detect_source_bundle_kind(
    *,
    manifest: dict[str, Any],
    skills: list[dict[str, Any]],
    artifact_doc: dict[str, Any],
) -> str:
    bundle_id = str(manifest.get("bundle_id", ""))
    if (
        not skills
        and (
            bundle_id.endswith("-source-v0.6")
            or artifact_doc.get("source_chunks_present")
            or artifact_doc.get("source_snapshot_present")
        )
    ):
        return "raw_book_source_bundle"
    return "published_source_bundle"


def _score_tri_state_density(extraction_kind_counts: dict[str, int]) -> float:
    total = sum(int(value or 0) for value in extraction_kind_counts.values())
    if total <= 0:
        return 0.0
    inferred_ratio = min(_safe_ratio(extraction_kind_counts.get("INFERRED"), total) / 0.08, 1.0)
    ambiguous_ratio = min(_safe_ratio(extraction_kind_counts.get("AMBIGUOUS"), total) / 0.10, 1.0)
    extracted_ratio = 1.0 if int(extraction_kind_counts.get("EXTRACTED", 0) or 0) > 0 else 0.0
    return _ratio([extracted_ratio, inferred_ratio, ambiguous_ratio])


def _graph_entity_stats(entities: list[dict[str, Any]], *, entity_type: str) -> dict[str, Any]:
    count = len(entities)
    if count == 0:
        return {
            "count": 0,
            "source_file_ratio": 0.0,
            "source_location_ratio": 0.0,
            "extraction_kind_ratio": 0.0,
            "confidence_ratio": 0.0 if entity_type == "edge" else None,
        }
    stats = {
        "count": count,
        "source_file_ratio": _safe_ratio(
            sum(1 for entity in entities if entity.get("source_file")),
            count,
        ),
        "source_location_ratio": _safe_ratio(
            sum(1 for entity in entities if entity.get("source_location")),
            count,
        ),
        "extraction_kind_ratio": _safe_ratio(
            sum(1 for entity in entities if entity.get("extraction_kind")),
            count,
        ),
    }
    if entity_type == "edge":
        stats["confidence_ratio"] = _safe_ratio(
            sum(1 for entity in entities if entity.get("confidence") is not None),
            count,
        )
    return stats


def _count_extraction_kinds(graph_doc: dict[str, Any]) -> dict[str, int]:
    counts = {
        "EXTRACTED": 0,
        "INFERRED": 0,
        "AMBIGUOUS": 0,
    }
    for entity in [*graph_doc.get("nodes", []), *graph_doc.get("edges", [])]:
        kind = entity.get("extraction_kind")
        if kind in counts:
            counts[kind] += 1
    return counts


def _safe_ratio(numerator: int | float | None, denominator: int | float | None) -> float:
    if numerator is None or denominator in (None, 0):
        return 0.0
    return float(numerator) / float(denominator)


def _ratio(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _score_source_skill_maturity(skills: list[dict[str, Any]]) -> float:
    if not skills:
        return 0.0

    status_weights = {
        "published": 1.0,
        "under_evaluation": 0.7,
        "candidate": 0.55,
        "archived": 0.8,
    }
    maturity_scores: list[float] = []
    for skill in skills:
        status_score = status_weights.get(str(skill.get("status", "")).lower(), 0.4)
        eval_counts = skill.get("eval_case_counts", {})
        total_eval_cases = sum(int(value or 0) for value in eval_counts.values())
        eval_score = min(total_eval_cases / 20.0, 1.0)
        revision_score = 1.0 if skill.get("has_revision_loop") else 0.5
        maturity_scores.append(
            0.60 * status_score + 0.25 * eval_score + 0.15 * revision_score
        )
    return _ratio(maturity_scores)
