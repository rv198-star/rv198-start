from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from kiu_pipeline.load import load_source_bundle, parse_sections
from kiu_pipeline.profile_resolver import resolve_profile
from kiu_pipeline.review import review_generated_run
from kiu_validator.core import validate_bundle


EXPECTED_CANGJIE_EXTRACTORS = {
    "framework",
    "principle",
    "case",
    "counter-example",
    "term",
}


def benchmark_reference_pack(
    *,
    kiu_bundle_path: str | Path,
    reference_pack_path: str | Path,
    run_root: str | Path | None = None,
    alignment_file: str | Path | None = None,
    comparison_scope: str = "structure-only",
) -> dict[str, Any]:
    bundle_root = Path(kiu_bundle_path)
    reference_root = Path(reference_pack_path)
    run_path = Path(run_root) if run_root is not None else None

    kiu_bundle = _scan_kiu_bundle(bundle_root)
    generated_run = _scan_generated_run(run_path, bundle_root) if run_path is not None else None
    reference_pack = _scan_reference_pack(reference_root)

    comparison = _build_comparison(
        kiu_bundle=kiu_bundle,
        generated_run=generated_run,
        reference_pack=reference_pack,
        comparison_scope=comparison_scope,
    )
    concept_alignment = _build_concept_alignment(
        kiu_bundle=kiu_bundle,
        reference_pack=reference_pack,
        alignment_file=alignment_file,
    )
    scorecard = _build_scorecard(
        kiu_bundle=kiu_bundle,
        generated_run=generated_run,
        reference_pack=reference_pack,
    )

    return {
        "comparison": comparison,
        "concept_alignment": concept_alignment,
        "kiu_bundle": kiu_bundle,
        "generated_run": generated_run,
        "reference_pack": reference_pack,
        "scorecard": scorecard,
    }


def write_reference_benchmark_report(
    *,
    report: dict[str, Any],
    output_path: str | Path,
) -> dict[str, str]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path = output.with_suffix(".md")
    markdown_path.write_text(_render_markdown_report(report), encoding="utf-8")
    return {
        "json_path": str(output),
        "markdown_path": str(markdown_path),
    }


def _scan_kiu_bundle(bundle_root: Path) -> dict[str, Any]:
    report = validate_bundle(bundle_root)
    manifest = report.get("manifest", {})
    graph_meta = report.get("graph", {})
    graph_path = bundle_root / manifest.get("graph", {}).get("path", "graph/graph.json")
    graph_doc = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path.exists() else {}
    graph_report_path = bundle_root / "GRAPH_REPORT.md"
    profile = resolve_profile(bundle_root)

    try:
        source_bundle = load_source_bundle(bundle_root)
    except Exception:
        source_bundle = None

    skill_entries = manifest.get("skills", []) if isinstance(manifest.get("skills"), list) else []
    double_anchor_ratio = None
    contract_ratio = None
    skill_reviews: dict[str, Any] = {}
    if source_bundle is not None and source_bundle.skills:
        double_anchored = 0
        contracts_ready = 0
        for skill in source_bundle.skills.values():
            anchors = skill.anchors or {}
            if anchors.get("graph_anchor_sets") and anchors.get("source_anchor_sets"):
                double_anchored += 1
            contract = skill.contract or {}
            if (
                isinstance(contract.get("trigger"), dict)
                and isinstance(contract.get("intake"), dict)
                and isinstance(contract.get("judgment_schema"), dict)
                and isinstance(contract.get("boundary"), dict)
            ):
                contracts_ready += 1
            skill_reviews[skill.skill_id] = _review_kiu_skill(skill)
        skill_count = len(source_bundle.skills)
        double_anchor_ratio = round(double_anchored / skill_count, 4)
        contract_ratio = round(contracts_ready / skill_count, 4)
    else:
        skill_count = len(skill_entries)
    bundle_kind = _detect_bundle_kind(manifest)

    node_stats = _graph_entity_stats(graph_doc.get("nodes", []), entity_type="node")
    edge_stats = _graph_entity_stats(graph_doc.get("edges", []), entity_type="edge")
    extraction_kind_counts = _count_extraction_kinds(graph_doc)

    return {
        "bundle_id": manifest.get("bundle_id"),
        "bundle_kind": bundle_kind,
        "path": str(bundle_root),
        "skill_count": skill_count,
        "validator_errors": len(report.get("errors", [])),
        "validator_warnings": len(report.get("warnings", [])),
        "graph_version": manifest.get("graph", {}).get("graph_version"),
        "graph_report_present": graph_report_path.exists(),
        "graph": {
            "node_count": graph_meta.get("node_count", 0),
            "edge_count": graph_meta.get("edge_count", 0),
            "community_count": graph_meta.get("community_count", 0),
        },
        "provenance": {
            "nodes": node_stats,
            "edges": edge_stats,
            "extraction_kind_counts": extraction_kind_counts,
        },
        "actionability": {
            "contract_ratio": contract_ratio,
        },
        "evidence_traceability": {
            "double_anchor_ratio": double_anchor_ratio,
        },
        "workflow_boundary": {
            "explicit_boundary": _has_explicit_workflow_boundary(profile),
        },
        "skill_reviews": skill_reviews,
    }


def _scan_generated_run(run_root: Path, source_bundle_path: Path) -> dict[str, Any]:
    reports_root = run_root / "reports"
    review_path = reports_root / "three-layer-review.json"
    if review_path.exists():
        review_doc = json.loads(review_path.read_text(encoding="utf-8"))
    else:
        review_doc = review_generated_run(
            run_root=run_root,
            source_bundle_path=source_bundle_path,
        )

    production_quality_path = reports_root / "production-quality.json"
    production_quality = (
        json.loads(production_quality_path.read_text(encoding="utf-8"))
        if production_quality_path.exists()
        else {}
    )
    metrics_path = reports_root / "metrics.json"
    metrics = (
        json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics_path.exists()
        else {}
    )
    workflow_count = int(metrics.get("summary", {}).get("workflow_script_candidates", 0) or 0)
    workflow_dirs = (
        len([path for path in (run_root / "workflow_candidates").glob("*") if path.is_dir()])
        if (run_root / "workflow_candidates").exists()
        else 0
    )
    return {
        "path": str(run_root),
        "skill_count": int(review_doc.get("generated_bundle", {}).get("skill_count", 0) or 0),
        "workflow_candidate_count": workflow_count,
        "workflow_boundary_preserved": workflow_count == 0 or workflow_count == workflow_dirs,
        "overall_score_100": review_doc.get("overall_score_100"),
        "usage_score_100": review_doc.get("usage_outputs", {}).get("score_100"),
        "minimum_production_quality": production_quality.get("minimum_production_quality"),
        "average_production_quality": production_quality.get("average_production_quality"),
        "bundle_quality_grade": production_quality.get("bundle_quality_grade"),
        "usage_sample_count": review_doc.get("usage_outputs", {}).get("sample_count"),
        "review_notes": review_doc.get("generated_bundle", {}).get("notes", []),
        "source_tri_state_effectiveness": review_doc.get("source_bundle", {}).get(
            "tri_state_effectiveness",
            {},
        ),
        "pipeline_artifacts": _discover_pipeline_artifacts(
            source_bundle_path=source_bundle_path,
            run_root=run_root,
        ),
    }


def _scan_reference_pack(reference_root: Path) -> dict[str, Any]:
    skill_paths = sorted(reference_root.glob("*/SKILL.md"))
    skill_ids = [path.parent.name for path in skill_paths]
    frontmatters = []
    quote_count = 0
    execution_count = 0
    boundary_count = 0
    skill_reviews: dict[str, Any] = {}
    for skill_path in skill_paths:
        content = skill_path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)
        sections = parse_sections(content)
        skill_id = skill_path.parent.name
        frontmatters.append(frontmatter)
        if ">" in content or any("原文" in name for name in sections):
            quote_count += 1
        if _has_named_section(sections, prefixes=("E",), keywords=("执行", "Execution")):
            execution_count += 1
        if _has_named_section(sections, prefixes=("B",), keywords=("边界", "Boundary")):
            boundary_count += 1
        skill_reviews[skill_id] = _review_reference_skill(
            skill_id=skill_id,
            frontmatter=frontmatter,
            sections=sections,
            markdown=content,
        )

    skill_count = len(skill_paths)
    source_book_ratio = _safe_ratio(
        sum(1 for doc in frontmatters if doc.get("source_book")),
        skill_count,
    )
    source_chapter_ratio = _safe_ratio(
        sum(1 for doc in frontmatters if doc.get("source_chapter")),
        skill_count,
    )

    return {
        "path": str(reference_root),
        "skill_count": skill_count,
        "skill_ids": skill_ids,
        "has_book_overview": (reference_root / "BOOK_OVERVIEW.md").exists(),
        "has_index": (reference_root / "INDEX.md").exists(),
        "has_candidates_dir": (reference_root / "candidates").exists(),
        "has_rejected_dir": (reference_root / "rejected").exists(),
        "actionability": {
            "execution_section_ratio": _safe_ratio(execution_count, skill_count),
            "boundary_section_ratio": _safe_ratio(boundary_count, skill_count),
        },
        "evidence_traceability": {
            "source_book_ratio": source_book_ratio,
            "source_chapter_ratio": source_chapter_ratio,
            "quote_section_ratio": _safe_ratio(quote_count, skill_count),
        },
        "workflow_boundary": {
            "explicit_boundary": (reference_root / "workflow_candidates").exists(),
        },
        "skill_reviews": skill_reviews,
    }


def _build_comparison(
    *,
    kiu_bundle: dict[str, Any],
    generated_run: dict[str, Any] | None,
    reference_pack: dict[str, Any],
    comparison_scope: str,
) -> dict[str, Any]:
    reference_skill_count = int(reference_pack.get("skill_count", 0) or 0)
    bundle_skill_count = int(kiu_bundle.get("skill_count", 0) or 0)
    generated_skill_count = (
        int(generated_run.get("skill_count", 0) or 0) if generated_run is not None else None
    )
    generated_usage_score = (
        generated_run.get("usage_score_100") if generated_run is not None else None
    )
    generated_usage_samples = (
        int(generated_run.get("usage_sample_count", 0) or 0) if generated_run is not None else None
    )

    return {
        "scope": comparison_scope,
        "notes": (
            ["kiu_bundle_is_source_bundle; use generated_run.skill_count for throughput."]
            if kiu_bundle.get("bundle_kind") == "source_bundle"
            else []
        ),
        "output_count": {
            "kiu_bundle_skill_count": bundle_skill_count,
            "kiu_generated_skill_count": generated_skill_count,
            "reference_skill_count": reference_skill_count,
            "bundle_throughput_vs_reference": _safe_ratio(bundle_skill_count, reference_skill_count),
            "generated_throughput_vs_reference": _safe_ratio(
                generated_skill_count,
                reference_skill_count,
            )
            if generated_skill_count is not None
            else None,
        },
        "coverage": {
            "bundle_coverage_vs_reference": min(
                _safe_ratio(bundle_skill_count, reference_skill_count),
                1.0,
            ),
            "generated_coverage_vs_reference": min(
                _safe_ratio(generated_skill_count, reference_skill_count),
                1.0,
            )
            if generated_skill_count is not None
            else None,
        },
        "actionability": {
            "kiu_bundle_contract_ratio": kiu_bundle.get("actionability", {}).get("contract_ratio"),
            "kiu_generated_usage_coverage_ratio": min(
                _safe_ratio(generated_usage_samples, generated_skill_count),
                1.0,
            )
            if generated_skill_count
            else None,
            "reference_execution_section_ratio": reference_pack.get("actionability", {}).get(
                "execution_section_ratio"
            ),
            "reference_boundary_section_ratio": reference_pack.get("actionability", {}).get(
                "boundary_section_ratio"
            ),
        },
        "evidence_traceability": {
            "kiu_double_anchor_ratio": kiu_bundle.get("evidence_traceability", {}).get(
                "double_anchor_ratio"
            ),
            "reference_source_context_ratio": round(
                (
                    float(
                        reference_pack.get("evidence_traceability", {}).get("source_book_ratio", 0.0)
                    )
                    + float(
                        reference_pack.get("evidence_traceability", {}).get("source_chapter_ratio", 0.0)
                    )
                    + float(
                        reference_pack.get("evidence_traceability", {}).get("quote_section_ratio", 0.0)
                    )
                )
                / 3.0,
                4,
            )
            if reference_pack.get("skill_count")
            else 0.0,
        },
        "workflow_vs_agentic_boundary": {
            "kiu_explicit_boundary": kiu_bundle.get("workflow_boundary", {}).get(
                "explicit_boundary",
                False,
            ),
            "kiu_boundary_preserved": generated_run.get("workflow_boundary_preserved")
            if generated_run is not None
            else None,
            "kiu_workflow_candidate_count": generated_run.get("workflow_candidate_count")
            if generated_run is not None
            else None,
            "reference_explicit_boundary": reference_pack.get("workflow_boundary", {}).get(
                "explicit_boundary",
                False,
            ),
        },
        "real_usage_quality": {
            "kiu_usage_score_100": generated_usage_score,
            "reference_usage_score_100": None,
            "notes": ["reference_pack_has_no_usage_review_artifacts"],
        },
    }


def _build_concept_alignment(
    *,
    kiu_bundle: dict[str, Any],
    reference_pack: dict[str, Any],
    alignment_file: str | Path | None,
) -> dict[str, Any]:
    kiu_reviews = dict(kiu_bundle.get("skill_reviews", {}))
    reference_reviews = dict(reference_pack.get("skill_reviews", {}))
    alignment_pairs = _resolve_alignment_pairs(
        kiu_reviews=kiu_reviews,
        reference_reviews=reference_reviews,
        alignment_file=alignment_file,
    )

    matched_pairs = []
    matched_kiu_ids: set[str] = set()
    matched_reference_ids: set[str] = set()
    for pair in alignment_pairs:
        kiu_skill_id = pair["kiu_skill_id"]
        reference_skill_id = pair["reference_skill_id"]
        kiu_review = kiu_reviews.get(kiu_skill_id)
        reference_review = reference_reviews.get(reference_skill_id)
        if not kiu_review or not reference_review:
            continue
        matched_kiu_ids.add(kiu_skill_id)
        matched_reference_ids.add(reference_skill_id)
        delta = round(
            float(kiu_review.get("overall_artifact_score_100", 0.0))
            - float(reference_review.get("overall_artifact_score_100", 0.0)),
            1,
        )
        matched_pairs.append(
            {
                "kiu_skill_id": kiu_skill_id,
                "reference_skill_id": reference_skill_id,
                "relationship": pair.get("relationship", "aligned"),
                "notes": pair.get("notes", []),
                "kiu_review": kiu_review,
                "reference_review": reference_review,
                "artifact_score_delta_100": delta,
            }
        )

    kiu_scores = [
        float(item["kiu_review"]["overall_artifact_score_100"])
        for item in matched_pairs
    ]
    reference_scores = [
        float(item["reference_review"]["overall_artifact_score_100"])
        for item in matched_pairs
    ]
    return {
        "alignment_source": (
            f"file:{Path(alignment_file)}" if alignment_file else "auto_exact_slug_match"
        ),
        "matched_pairs": matched_pairs,
        "unmatched_kiu_skills": sorted(set(kiu_reviews) - matched_kiu_ids),
        "unmatched_reference_skills": sorted(set(reference_reviews) - matched_reference_ids),
        "summary": {
            "matched_pair_count": len(matched_pairs),
            "kiu_average_artifact_score_100": round(_average(kiu_scores), 1),
            "reference_average_artifact_score_100": round(_average(reference_scores), 1),
            "average_artifact_score_delta_100": round(
                _average(kiu_scores) - _average(reference_scores),
                1,
            )
            if matched_pairs
            else 0.0,
        },
    }


def _build_scorecard(
    *,
    kiu_bundle: dict[str, Any],
    generated_run: dict[str, Any] | None,
    reference_pack: dict[str, Any],
) -> dict[str, Any]:
    bundle_errors = int(kiu_bundle.get("validator_errors", 0) or 0)
    bundle_warnings = int(kiu_bundle.get("validator_warnings", 0) or 0)
    structural_cleanliness = max(0.0, 1.0 - 0.25 * bundle_errors - 0.05 * bundle_warnings)
    boundary_explicit = 1.0 if kiu_bundle.get("workflow_boundary", {}).get("explicit_boundary") else 0.0
    boundary_preserved = (
        1.0 if generated_run and generated_run.get("workflow_boundary_preserved") else 0.0
    )
    quality_gate = 0.0
    review_score = 0.0
    if generated_run is not None:
        minimum_production = float(generated_run.get("minimum_production_quality", 0.0) or 0.0)
        quality_gate = min(minimum_production / 0.82, 1.0)
        review_score = min(float(generated_run.get("overall_score_100", 0.0) or 0.0) / 100.0, 1.0)
    foundation_score = round(
        100.0
        * (
            0.35 * structural_cleanliness
            + 0.20 * boundary_explicit
            + 0.20 * boundary_preserved
            + 0.15 * quality_gate
            + 0.10 * review_score
        ),
        1,
    )

    node_prov = _average(
        [
            kiu_bundle.get("provenance", {}).get("nodes", {}).get("source_file_ratio"),
            kiu_bundle.get("provenance", {}).get("nodes", {}).get("source_location_ratio"),
            kiu_bundle.get("provenance", {}).get("nodes", {}).get("extraction_kind_ratio"),
        ]
    )
    edge_prov = _average(
        [
            kiu_bundle.get("provenance", {}).get("edges", {}).get("source_file_ratio"),
            kiu_bundle.get("provenance", {}).get("edges", {}).get("source_location_ratio"),
            kiu_bundle.get("provenance", {}).get("edges", {}).get("extraction_kind_ratio"),
            kiu_bundle.get("provenance", {}).get("edges", {}).get("confidence_ratio"),
        ]
    )
    extraction_kind_counts = kiu_bundle.get("provenance", {}).get("extraction_kind_counts", {})
    tri_state_density_ratio = _tri_state_density_ratio(extraction_kind_counts)
    communities_ratio = 1.0 if kiu_bundle.get("graph", {}).get("community_count", 0) > 0 else 0.0
    graph_report_ratio = 1.0 if kiu_bundle.get("graph_report_present") else 0.0
    tri_state_effectiveness_ratio = 0.0
    if generated_run is not None:
        tri_state_effectiveness_ratio = min(
            float(
                generated_run.get("source_tri_state_effectiveness", {}).get("overall_ratio", 0.0)
                or 0.0
            ),
            1.0,
        )
        graphify_score = round(
            100.0
            * (
                0.25 * node_prov
                + 0.25 * edge_prov
                + 0.15 * tri_state_density_ratio
                + 0.15 * tri_state_effectiveness_ratio
                + 0.10 * communities_ratio
                + 0.10 * graph_report_ratio
            ),
            1,
        )
    else:
        graphify_score = round(
            100.0
            * (
                0.30 * node_prov
                + 0.30 * edge_prov
                + 0.20 * tri_state_density_ratio
                + 0.10 * communities_ratio
                + 0.10 * graph_report_ratio
            ),
            1,
        )

    pipeline_artifacts = generated_run.get("pipeline_artifacts", {}) if generated_run is not None else {}
    stage_presence_ratio = _average(
        [
            1.0 if pipeline_artifacts.get("raw_source_present") else 0.0,
            1.0 if pipeline_artifacts.get("source_chunks_present") else 0.0,
            1.0 if pipeline_artifacts.get("extraction_result_present") else 0.0,
            1.0 if pipeline_artifacts.get("graph_present") else 0.0,
            1.0 if generated_run is not None else 0.0,
        ]
    )
    extraction_kinds = set(pipeline_artifacts.get("extractor_kinds", []))
    extractor_coverage_ratio = min(
        len(extraction_kinds & EXPECTED_CANGJIE_EXTRACTORS) / len(EXPECTED_CANGJIE_EXTRACTORS),
        1.0,
    )
    reference_skill_count = int(reference_pack.get("skill_count", 0) or 0)
    throughput_ratio = min(
        _safe_ratio(
            generated_run.get("skill_count") if generated_run is not None else kiu_bundle.get("skill_count"),
            reference_skill_count,
        ),
        1.0,
    )
    usage_quality_ratio = min(
        float(generated_run.get("usage_score_100", 0.0) or 0.0) / 100.0,
        1.0,
    ) if generated_run is not None else 0.0
    cangjie_score = round(
        100.0
        * (
            0.30 * stage_presence_ratio
            + 0.25 * extractor_coverage_ratio
            + 0.25 * throughput_ratio
            + 0.20 * usage_quality_ratio
        ),
        1,
    )

    return {
        "kiu_foundation_retained_100": foundation_score,
        "graphify_core_absorbed_100": graphify_score,
        "cangjie_core_absorbed_100": cangjie_score,
        "details": {
            "kiu_foundation_retained": {
                "structural_cleanliness": round(structural_cleanliness, 4),
                "boundary_explicit_ratio": boundary_explicit,
                "boundary_preserved_ratio": boundary_preserved,
                "quality_gate_ratio": round(quality_gate, 4),
                "review_score_ratio": round(review_score, 4),
            },
            "graphify_core_absorbed": {
                "node_provenance_ratio": round(node_prov, 4),
                "edge_provenance_ratio": round(edge_prov, 4),
                "tri_state_density_ratio": round(tri_state_density_ratio, 4),
                "tri_state_effectiveness_ratio": round(tri_state_effectiveness_ratio, 4),
                "communities_ratio": communities_ratio,
                "graph_report_ratio": graph_report_ratio,
            },
            "cangjie_core_absorbed": {
                "pipeline_stage_presence_ratio": round(stage_presence_ratio, 4),
                "extractor_coverage_ratio": round(extractor_coverage_ratio, 4),
                "throughput_vs_reference_ratio": round(throughput_ratio, 4),
                "usage_quality_ratio": round(usage_quality_ratio, 4),
                "extractor_kinds": sorted(extraction_kinds),
            },
        },
    }


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


def _tri_state_density_ratio(extraction_kind_counts: dict[str, int]) -> float:
    total = sum(int(value or 0) for value in extraction_kind_counts.values())
    if total <= 0:
        return 0.0
    inferred_ratio = min(_safe_ratio(extraction_kind_counts.get("INFERRED"), total) / 0.08, 1.0)
    ambiguous_ratio = min(_safe_ratio(extraction_kind_counts.get("AMBIGUOUS"), total) / 0.10, 1.0)
    extracted_ratio = 1.0 if int(extraction_kind_counts.get("EXTRACTED", 0) or 0) > 0 else 0.0
    return _average([extracted_ratio, inferred_ratio, ambiguous_ratio])


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


def _review_kiu_skill(skill: Any) -> dict[str, Any]:
    contract = skill.contract or {}
    trigger = contract.get("trigger", {}) if isinstance(contract.get("trigger"), dict) else {}
    intake = contract.get("intake", {}) if isinstance(contract.get("intake"), dict) else {}
    boundary = contract.get("boundary", {}) if isinstance(contract.get("boundary"), dict) else {}
    judgment_schema = (
        contract.get("judgment_schema", {})
        if isinstance(contract.get("judgment_schema"), dict)
        else {}
    )
    anchors = skill.anchors or {}
    graph_anchor_sets = anchors.get("graph_anchor_sets", [])
    source_anchor_sets = anchors.get("source_anchor_sets", [])

    trigger_clarity = 100.0 * _average(
        [
            1.0 if trigger.get("patterns") else 0.0,
            1.0 if trigger.get("exclusions") else 0.0,
            1.0 if intake.get("required") else 0.0,
        ]
    )
    boundary_clarity = 100.0 * _average(
        [
            1.0 if boundary.get("fails_when") else 0.0,
            1.0 if boundary.get("do_not_fire_when") else 0.0,
            1.0 if len(str(skill.sections.get("Rationale", ""))) >= 120 else 0.0,
        ]
    )
    actionability = 100.0 * _average(
        [
            1.0 if judgment_schema.get("output") else 0.0,
            1.0 if skill.trace_refs else 0.0,
            1.0 if skill.sections.get("Usage Summary") else 0.0,
        ]
    )
    evidence_traceability = 100.0 * _average(
        [
            1.0 if graph_anchor_sets else 0.0,
            1.0 if source_anchor_sets else 0.0,
            1.0 if anchors.get("graph_hash") and anchors.get("graph_version") else 0.0,
        ]
    )
    auditability = 100.0 * _average(
        [
            1.0 if anchors else 0.0,
            1.0 if getattr(skill, "eval_summary", None) else 0.0,
            1.0 if getattr(skill, "revisions", None) else 0.0,
        ]
    )
    overall = round(
        _average(
            [
                trigger_clarity,
                boundary_clarity,
                actionability,
                evidence_traceability,
                auditability,
            ]
        ),
        1,
    )
    return {
        "title": getattr(skill, "title", skill.skill_id),
        "trigger_clarity_100": round(trigger_clarity, 1),
        "boundary_clarity_100": round(boundary_clarity, 1),
        "actionability_100": round(actionability, 1),
        "evidence_traceability_100": round(evidence_traceability, 1),
        "auditability_100": round(auditability, 1),
        "overall_artifact_score_100": overall,
        "notes": [
            "structured_contract_present",
            "double_anchor_backed" if graph_anchor_sets and source_anchor_sets else "partial_anchor_backing",
        ],
    }


def _review_reference_skill(
    *,
    skill_id: str,
    frontmatter: dict[str, Any],
    sections: dict[str, str],
    markdown: str,
) -> dict[str, Any]:
    description = str(frontmatter.get("description", "") or "")
    trigger_section = _find_section(
        sections,
        prefixes=("A2",),
        keywords=("触发", "Trigger"),
    )
    boundary_section = _find_section(
        sections,
        prefixes=("B",),
        keywords=("边界", "Boundary"),
    )
    execution_section = _find_section(
        sections,
        prefixes=("E",),
        keywords=("执行", "Execution"),
    )
    reading_section = _find_section(
        sections,
        prefixes=("R",),
        keywords=("原文", "Reading"),
    )
    execution_steps = len(
        re.findall(r"^\s*\d+\.\s+", execution_section, flags=re.MULTILINE)
    ) if execution_section else 0

    trigger_clarity = 100.0 * _average(
        [
            1.0 if description else 0.0,
            1.0 if trigger_section else 0.0,
            1.0 if len(description) >= 40 or len(trigger_section) >= 120 else 0.0,
        ]
    )
    boundary_clarity = 100.0 * _average(
        [
            1.0 if boundary_section else 0.0,
            1.0 if len(boundary_section) >= 60 else 0.0,
            1.0 if "不要" in boundary_section or "不适用" in boundary_section else 0.0,
        ]
    )
    actionability = 100.0 * _average(
        [
            1.0 if execution_section else 0.0,
            min(execution_steps / 3.0, 1.0),
            1.0 if "step" in execution_section.lower() or execution_steps > 0 else 0.0,
        ]
    )
    evidence_traceability = 100.0 * _average(
        [
            1.0 if frontmatter.get("source_book") else 0.0,
            1.0 if frontmatter.get("source_chapter") else 0.0,
            1.0 if reading_section or ">" in markdown else 0.0,
        ]
    )
    auditability = 100.0 * _average(
        [
            1.0 if frontmatter else 0.0,
            0.0,
            0.0,
        ]
    )
    overall = round(
        _average(
            [
                trigger_clarity,
                boundary_clarity,
                actionability,
                evidence_traceability,
                auditability,
            ]
        ),
        1,
    )
    return {
        "title": skill_id,
        "trigger_clarity_100": round(trigger_clarity, 1),
        "boundary_clarity_100": round(boundary_clarity, 1),
        "actionability_100": round(actionability, 1),
        "evidence_traceability_100": round(evidence_traceability, 1),
        "auditability_100": round(auditability, 1),
        "overall_artifact_score_100": overall,
        "notes": [
            "frontmatter_present" if frontmatter else "no_frontmatter",
            "reading_excerpt_present" if reading_section or ">" in markdown else "no_reading_excerpt",
            "no_structured_truth_docs",
        ],
    }


def _resolve_alignment_pairs(
    *,
    kiu_reviews: dict[str, Any],
    reference_reviews: dict[str, Any],
    alignment_file: str | Path | None,
) -> list[dict[str, Any]]:
    if alignment_file is not None:
        alignment_doc = yaml.safe_load(Path(alignment_file).read_text(encoding="utf-8")) or {}
        pairs = alignment_doc.get("pairs", [])
        return [pair for pair in pairs if isinstance(pair, dict)]
    exact_matches = sorted(set(kiu_reviews) & set(reference_reviews))
    return [
        {
            "kiu_skill_id": skill_id,
            "reference_skill_id": skill_id,
            "relationship": "exact_slug_match",
            "notes": [],
        }
        for skill_id in exact_matches
    ]


def _has_explicit_workflow_boundary(profile: dict[str, Any]) -> bool:
    rules = profile.get("routing_rules", [])
    candidate_kinds = profile.get("candidate_kinds", {})
    if "general_agentic" not in candidate_kinds or "workflow_script" not in candidate_kinds:
        return False
    for rule in rules:
        when = rule.get("when", {})
        if (
            when.get("workflow_certainty") == "high"
            and when.get("context_certainty") == "high"
            and rule.get("recommended_execution_mode") == "workflow_script"
            and rule.get("disposition") == "workflow_script_candidate"
        ):
            return True
    return False


def _detect_bundle_kind(manifest: dict[str, Any]) -> str:
    bundle_id = str(manifest.get("bundle_id", ""))
    if bundle_id.endswith("-source-v0.6"):
        return "source_bundle"
    return "published_bundle"


def _discover_pipeline_artifacts(
    *,
    source_bundle_path: Path,
    run_root: Path,
) -> dict[str, Any]:
    manifest = yaml.safe_load((source_bundle_path / "manifest.yaml").read_text(encoding="utf-8")) or {}
    graph_path = source_bundle_path / manifest.get("graph", {}).get("path", "graph/graph.json")
    source_snapshot_present = any((source_bundle_path / "sources").glob("*"))
    source_chunks_path = source_bundle_path / "ingestion" / "source-chunks-v0.1.json"
    bundle_id = str(manifest.get("bundle_id", ""))
    extraction_result_path = None
    intermediate_graph_path = None
    extractor_kinds: set[str] = set()
    if bundle_id.endswith("-source-v0.6"):
        source_id = bundle_id.removesuffix("-source-v0.6")
        try:
            output_root = run_root.parents[2]
        except IndexError:
            output_root = None
        if output_root is not None:
            intermediate_root = output_root / "intermediate" / source_id / run_root.name
            extraction_result_path = intermediate_root / "extraction-result.json"
            intermediate_graph_path = intermediate_root / "graph.json"
            if extraction_result_path.exists():
                extraction_doc = json.loads(extraction_result_path.read_text(encoding="utf-8"))
                for node in extraction_doc.get("nodes", []):
                    extractor_kind = node.get("extractor_kind")
                    if isinstance(extractor_kind, str) and extractor_kind:
                        extractor_kinds.add(_normalize_extractor_kind(extractor_kind))
    return {
        "raw_source_present": source_snapshot_present,
        "source_chunks_present": source_chunks_path.exists(),
        "extraction_result_present": extraction_result_path.exists() if extraction_result_path else False,
        "graph_present": graph_path.exists() or (intermediate_graph_path.exists() if intermediate_graph_path else False),
        "extractor_kinds": sorted(extractor_kinds),
    }


def _normalize_extractor_kind(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if normalized == "counterexample":
        return "counter-example"
    return normalized


def _parse_frontmatter(markdown: str) -> dict[str, Any]:
    match = re.match(r"^---\n(.*?)\n---\n", markdown, flags=re.DOTALL)
    if not match:
        return {}
    loaded = yaml.safe_load(match.group(1))
    return loaded or {}


def _has_named_section(
    sections: dict[str, str],
    *,
    prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
) -> bool:
    for name in sections:
        stripped = name.strip()
        if any(stripped.startswith(prefix) for prefix in prefixes):
            return True
        if any(keyword.lower() in stripped.lower() for keyword in keywords):
            return True
    return False


def _find_section(
    sections: dict[str, str],
    *,
    prefixes: tuple[str, ...],
    keywords: tuple[str, ...],
) -> str:
    for name, value in sections.items():
        stripped = name.strip()
        if any(stripped.startswith(prefix) for prefix in prefixes):
            return value
        if any(keyword.lower() in stripped.lower() for keyword in keywords):
            return value
    return ""


def _average(values: list[float | int | None]) -> float:
    usable = [float(value) for value in values if value is not None]
    if not usable:
        return 0.0
    return sum(usable) / len(usable)


def _safe_ratio(numerator: int | float | None, denominator: int | float | None) -> float:
    if numerator is None or denominator in (None, 0):
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _render_markdown_report(report: dict[str, Any]) -> str:
    comparison = report["comparison"]
    concept_alignment = report["concept_alignment"]
    scorecard = report["scorecard"]
    generated_run = report.get("generated_run") or {}
    return "\n".join(
        [
            "# Reference Benchmark Report",
            "",
            "## Summary",
            "",
            f"- Scope: `{comparison['scope']}`",
            f"- KiU bundle skills: `{report['kiu_bundle']['skill_count']}`",
            f"- KiU generated skills: `{generated_run.get('skill_count', 'n/a')}`",
            f"- Reference pack skills: `{report['reference_pack']['skill_count']}`",
            "",
            "## Comparison",
            "",
            f"- Bundle throughput vs reference: `{comparison['output_count']['bundle_throughput_vs_reference']}`",
            f"- Generated throughput vs reference: `{comparison['output_count']['generated_throughput_vs_reference']}`",
            f"- KiU double-anchor ratio: `{comparison['evidence_traceability']['kiu_double_anchor_ratio']}`",
            f"- Reference source-context ratio: `{comparison['evidence_traceability']['reference_source_context_ratio']}`",
            f"- KiU usage score: `{comparison['real_usage_quality']['kiu_usage_score_100']}`",
            "",
            "## Concept Alignment",
            "",
            f"- Alignment source: `{concept_alignment['alignment_source']}`",
            f"- Matched pairs: `{concept_alignment['summary']['matched_pair_count']}`",
            f"- KiU aligned artifact score: `{concept_alignment['summary']['kiu_average_artifact_score_100']}`",
            f"- Reference aligned artifact score: `{concept_alignment['summary']['reference_average_artifact_score_100']}`",
            "",
            "## Scorecard",
            "",
            f"- KiU foundation retained: `{scorecard['kiu_foundation_retained_100']}`",
            f"- Graphify core absorbed: `{scorecard['graphify_core_absorbed_100']}`",
            f"- cangjie core absorbed: `{scorecard['cangjie_core_absorbed_100']}`",
            "",
        ]
    )
