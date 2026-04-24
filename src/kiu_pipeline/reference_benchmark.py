from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from kiu_pipeline.load import load_source_bundle, parse_sections
from kiu_pipeline.pipeline_provenance import load_pipeline_provenance
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
    blind_preference_evidence: str | Path | None = None,
    compatibility_regression_report: str | Path | None = None,
) -> dict[str, Any]:
    bundle_root = Path(kiu_bundle_path)
    reference_root = Path(reference_pack_path)
    run_path = Path(run_root) if run_root is not None else None

    kiu_bundle = _scan_kiu_bundle(bundle_root)
    generated_run = _scan_generated_run(run_path, bundle_root) if run_path is not None else None
    reference_pack = _scan_reference_pack(reference_root)
    if generated_run is not None and blind_preference_evidence is not None:
        generated_run.setdefault("pipeline_artifacts", {})["blind_preference_summary"] = (
            _load_blind_preference_summary(blind_preference_evidence)
        )
    if generated_run is not None and compatibility_regression_report is not None:
        generated_run.setdefault("pipeline_artifacts", {})["compatibility_regression_summary"] = (
            _load_compatibility_regression_summary(compatibility_regression_report)
        )

    concept_alignment = _build_concept_alignment(
        kiu_bundle=kiu_bundle,
        generated_run=generated_run,
        reference_pack=reference_pack,
        alignment_file=alignment_file,
    )
    same_scenario_usage = _build_same_scenario_usage(
        bundle_root=bundle_root,
        generated_run=generated_run,
        reference_root=reference_root,
        concept_alignment=concept_alignment,
    )
    comparison = _build_comparison(
        kiu_bundle=kiu_bundle,
        generated_run=generated_run,
        reference_pack=reference_pack,
        concept_alignment=concept_alignment,
        same_scenario_usage=same_scenario_usage,
        comparison_scope=comparison_scope,
    )
    scorecard = _build_scorecard(
        kiu_bundle=kiu_bundle,
        generated_run=generated_run,
        reference_pack=reference_pack,
        same_scenario_usage=same_scenario_usage,
    )

    return {
        "comparison": comparison,
        "concept_alignment": concept_alignment,
        "kiu_bundle": kiu_bundle,
        "generated_run": generated_run,
        "reference_pack": reference_pack,
        "same_scenario_usage": same_scenario_usage,
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


def _load_compatibility_regression_summary(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    try:
        doc = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"executed": 0, "passed": 0, "failed": 1, "report_path": str(report_path)}
    summary = doc.get("summary", {}) if isinstance(doc.get("summary"), dict) else {}
    return {
        "baseline": str(doc.get("version", "v0.6.4")),
        "executed": int(summary.get("executed", 0) or 0),
        "passed": int(summary.get("passed", 0) or 0),
        "failed": int(summary.get("failed", 0) or 0),
        "report_path": str(report_path),
    }


def _load_blind_preference_summary(path: str | Path) -> dict[str, Any]:
    evidence_path = Path(path)
    try:
        doc = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"valid": False, "pass_ratio": 0.0, "pair_count": 0, "errors": ["blind_evidence_unreadable"]}
    errors: list[str] = []
    if doc.get("schema_version") != "kiu.blind-preference-review/v0.1":
        errors.append("invalid_schema_version")
    pairs = doc.get("pairs", [])
    if not isinstance(pairs, list):
        errors.append("pairs_not_list")
        pairs = []
    passed = 0
    usable = 0
    for pair in pairs:
        if not isinstance(pair, dict):
            errors.append("pair_not_object")
            continue
        preferred = str(pair.get("preferred", "")).lower()
        if preferred in {"kiu", "cangjie", "reference"}:
            errors.append("non_anonymous_preference_label")
            continue
        if preferred not in {"a", "b", "tie", "inconclusive"}:
            errors.append("invalid_preferred_option")
            continue
        roles = pair.get("option_roles", {}) if isinstance(pair.get("option_roles"), dict) else {}
        scores = pair.get("dimension_scores", {}) if isinstance(pair.get("dimension_scores"), dict) else {}
        required_dimensions = {"usage", "depth", "transferability", "anti_misuse"}
        if not required_dimensions.issubset(scores):
            errors.append("dimension_scores_incomplete")
            continue
        usable += 1
        if preferred == "tie":
            passed += 1
        elif roles.get(preferred) == "kiu":
            passed += 1
    valid = not errors
    return {
        "schema_version": "kiu.blind-preference-summary/v0.1",
        "valid": valid,
        "pair_count": usable,
        "pass_ratio": round(_safe_ratio(passed, usable), 4),
        "errors": sorted(set(errors)),
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

    pipeline_provenance = load_pipeline_provenance(run_root)
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
    verification_summary_path = reports_root / "verification-summary.json"
    verification_summary = (
        json.loads(verification_summary_path.read_text(encoding="utf-8"))
        if verification_summary_path.exists()
        else {}
    )
    generated_bundle_root = run_root / "bundle"
    generated_bundle_skill_reviews: dict[str, Any] = {}
    graph_to_skill_distillation: dict[str, Any] = {}
    if generated_bundle_root.exists():
        try:
            generated_bundle = load_source_bundle(generated_bundle_root)
        except Exception:
            generated_bundle = None
        if generated_bundle is not None:
            graph_to_skill_distillation = _review_graph_to_skill_distillation(generated_bundle)
            for skill in generated_bundle.skills.values():
                generated_bundle_skill_reviews[skill.skill_id] = _review_kiu_skill(skill)
    return {
        "path": str(run_root),
        "generated_bundle_path": str(generated_bundle_root),
        "skill_count": int(review_doc.get("generated_bundle", {}).get("skill_count", 0) or 0),
        "workflow_candidate_count": workflow_count,
        "workflow_boundary_preserved": workflow_count == 0 or workflow_count == workflow_dirs,
        "verification_gate_present": bool(verification_summary),
        "workflow_verification_ready_ratio": _workflow_verification_ready_ratio(
            verification_summary=verification_summary,
            workflow_candidate_count=workflow_count,
        ),
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
        "graph_to_skill_distillation": graph_to_skill_distillation,
        "generated_bundle_skill_reviews": generated_bundle_skill_reviews,
        "pipeline_provenance": pipeline_provenance,
        "raw_book_no_seed_cold_start": bool(
            pipeline_provenance.get("raw_book_no_seed_cold_start")
        ),
        "pipeline_mode": pipeline_provenance.get("pipeline_mode", "unknown"),
        "pipeline_artifacts": _discover_pipeline_artifacts(
            source_bundle_path=source_bundle_path,
            run_root=run_root,
            pipeline_provenance=pipeline_provenance,
        ),
    }


def _scan_reference_pack(reference_root: Path) -> dict[str, Any]:
    skill_paths = sorted(reference_root.glob("*/SKILL.md"))
    skill_ids = [path.parent.name for path in skill_paths]
    metadata_path = reference_root / "metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata = {"metadata_parse_error": True}
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
        "reference_protocol": metadata.get("reference_protocol"),
        "official_cangjie_run": metadata.get("official_cangjie_run"),
        "benchmark_only": metadata.get("benchmark_only"),
        "external_reference_boundary": metadata.get("external_reference_boundary", {}),
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
    concept_alignment: dict[str, Any],
    same_scenario_usage: dict[str, Any],
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
    same_scenario_summary = same_scenario_usage.get("summary", {})

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
            "kiu_workflow_verification_ready_ratio": generated_run.get(
                "workflow_verification_ready_ratio"
            )
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
            "kiu_same_scenario_usage_score_100": same_scenario_summary.get(
                "kiu_average_usage_score_100"
            ),
            "reference_same_scenario_usage_score_100": same_scenario_summary.get(
                "reference_average_usage_score_100"
            ),
            "same_scenario_average_delta_100": same_scenario_summary.get(
                "average_usage_score_delta_100"
            ),
            "kiu_same_scenario_weighted_pass_rate": same_scenario_summary.get(
                "kiu_weighted_pass_rate"
            ),
            "reference_same_scenario_weighted_pass_rate": same_scenario_summary.get(
                "reference_weighted_pass_rate"
            ),
            "same_scenario_weighted_pass_rate_delta": same_scenario_summary.get(
                "weighted_pass_rate_delta"
            ),
            "same_scenario_usage_winner": same_scenario_summary.get("usage_winner"),
            "graph_to_skill_distillation_100": (
                generated_run.get("graph_to_skill_distillation", {}).get("overall_score_100")
                if generated_run is not None
                else None
            ),
            "same_scenario_matched_pair_count": same_scenario_summary.get("matched_pair_count"),
            "same_scenario_case_count": same_scenario_summary.get("scenario_count"),
            "concept_aligned_pair_count": concept_alignment.get("summary", {}).get("matched_pair_count"),
            "notes": (
                ["same_scenario_usage_heuristic_review"]
                if same_scenario_summary.get("scenario_count", 0)
                else ["reference_pack_has_no_usage_review_artifacts"]
            ),
        },
    }


def _build_concept_alignment(
    *,
    kiu_bundle: dict[str, Any],
    generated_run: dict[str, Any] | None,
    reference_pack: dict[str, Any],
    alignment_file: str | Path | None,
) -> dict[str, Any]:
    generated_kiu_reviews = (
        dict(generated_run.get("generated_bundle_skill_reviews", {}))
        if generated_run is not None
        else {}
    )
    if generated_kiu_reviews:
        kiu_reviews = generated_kiu_reviews
    else:
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
            "unmatched_kiu_skill_count": len(set(kiu_reviews) - matched_kiu_ids),
            "unmatched_reference_skill_count": len(
                set(reference_reviews) - matched_reference_ids
            ),
        },
    }


def _build_same_scenario_usage(
    *,
    bundle_root: Path,
    generated_run: dict[str, Any] | None,
    reference_root: Path,
    concept_alignment: dict[str, Any],
) -> dict[str, Any]:
    effective_bundle_root = bundle_root
    if generated_run is not None:
        generated_bundle_path = generated_run.get("generated_bundle_path")
        if isinstance(generated_bundle_path, str) and generated_bundle_path:
            generated_bundle_root = Path(generated_bundle_path)
            if generated_bundle_root.exists():
                effective_bundle_root = generated_bundle_root
    try:
        source_bundle = load_source_bundle(effective_bundle_root)
    except Exception as exc:
        return {
            "matched_pairs": [],
            "summary": {
                "matched_pair_count": 0,
                "scenario_count": 0,
                "kiu_average_usage_score_100": 0.0,
                "reference_average_usage_score_100": 0.0,
                "average_usage_score_delta_100": 0.0,
                "kiu_weighted_pass_rate": 0.0,
                "reference_weighted_pass_rate": 0.0,
                "failure_tag_counts": {},
                "top_failure_modes": [],
                "repair_target_counts": {},
                "dominant_repair_targets": [],
                "critical_case_count": 0,
                "major_case_count": 0,
            },
            "notes": [f"failed_to_load_kiu_bundle:{exc.__class__.__name__}"],
        }

    matched_pairs = []
    notes: list[str] = []
    kiu_case_scores: list[float] = []
    reference_case_scores: list[float] = []
    kiu_credit_total = 0.0
    reference_credit_total = 0.0
    scenario_total = 0

    for pair in concept_alignment.get("matched_pairs", []):
        kiu_skill = source_bundle.skills.get(pair["kiu_skill_id"])
        if kiu_skill is None:
            notes.append(f"missing_kiu_skill:{pair['kiu_skill_id']}")
            continue

        reference_skill_dir = reference_root / pair["reference_skill_id"]
        reference_skill_path = reference_skill_dir / "SKILL.md"
        prompt_path = reference_skill_dir / "test-prompts.json"
        if not reference_skill_path.exists():
            notes.append(f"missing_reference_skill:{pair['reference_skill_id']}")
            continue
        if not prompt_path.exists():
            notes.append(f"missing_test_prompts:{pair['reference_skill_id']}")
            continue

        prompt_doc = json.loads(prompt_path.read_text(encoding="utf-8"))
        raw_cases = prompt_doc.get("test_cases", [])
        test_cases = [case for case in raw_cases if isinstance(case, dict)]
        if not test_cases:
            notes.append(f"empty_test_cases:{pair['reference_skill_id']}")
            continue

        reference_markdown = reference_skill_path.read_text(encoding="utf-8")
        reference_frontmatter = _parse_frontmatter(reference_markdown)
        reference_sections = parse_sections(reference_markdown)
        kiu_case_reviews = []
        reference_case_reviews = []
        case_reviews = []
        alignment_strength = _relationship_alignment_strength(pair.get("relationship"))
        minimum_pass_rate = float(prompt_doc.get("minimum_pass_rate", 0.0) or 0.0)

        for case in test_cases:
            kiu_review = _evaluate_kiu_usage_case(
                skill=kiu_skill,
                case=case,
                alignment_strength=alignment_strength,
            )
            reference_review = _evaluate_reference_usage_case(
                skill_id=pair["reference_skill_id"],
                markdown=reference_markdown,
                frontmatter=reference_frontmatter,
                sections=reference_sections,
                case=case,
            )
            case_reviews.append(
                {
                    "case_id": str(case.get("id", "")),
                    "type": str(case.get("type", "")),
                    "prompt": str(case.get("prompt", "")),
                    "expected_behavior": str(case.get("expected_behavior", "")),
                    "notes": str(case.get("notes", "")),
                    "kiu_review": kiu_review,
                    "reference_review": reference_review,
                    "score_delta_100": round(
                        float(kiu_review["overall_score_100"])
                        - float(reference_review["overall_score_100"]),
                        1,
                    ),
                }
            )
            kiu_case_reviews.append({"type": str(case.get("type", "")), **kiu_review})
            reference_case_reviews.append({"type": str(case.get("type", "")), **reference_review})

        kiu_usage_review = _summarize_usage_case_reviews(
            case_reviews=kiu_case_reviews,
            minimum_pass_rate=minimum_pass_rate,
        )
        reference_usage_review = _summarize_usage_case_reviews(
            case_reviews=reference_case_reviews,
            minimum_pass_rate=minimum_pass_rate,
        )
        matched_pairs.append(
            {
                "kiu_skill_id": pair["kiu_skill_id"],
                "reference_skill_id": pair["reference_skill_id"],
                "relationship": pair.get("relationship", "aligned"),
                "scenario_count": len(case_reviews),
                "minimum_pass_rate": minimum_pass_rate,
                "kiu_usage_review": kiu_usage_review,
                "reference_usage_review": reference_usage_review,
                "usage_score_delta_100": round(
                    float(kiu_usage_review["overall_score_100"])
                    - float(reference_usage_review["overall_score_100"]),
                    1,
                ),
                "cases": case_reviews,
            }
        )
        kiu_case_scores.extend(
            float(item["overall_score_100"]) for item in kiu_case_reviews
        )
        reference_case_scores.extend(
            float(item["overall_score_100"]) for item in reference_case_reviews
        )
        kiu_credit_total += float(kiu_usage_review["credit_total"])
        reference_credit_total += float(reference_usage_review["credit_total"])
        scenario_total += len(case_reviews)

    return {
        "matched_pairs": matched_pairs,
        "summary": {
            "matched_pair_count": len(matched_pairs),
            "scenario_count": scenario_total,
            "kiu_average_usage_score_100": round(_average(kiu_case_scores), 1),
            "reference_average_usage_score_100": round(_average(reference_case_scores), 1),
            "average_usage_score_delta_100": round(
                _average(kiu_case_scores) - _average(reference_case_scores),
                1,
            )
            if scenario_total
            else 0.0,
            "kiu_weighted_pass_rate": round(_safe_ratio(kiu_credit_total, scenario_total), 4),
            "reference_weighted_pass_rate": round(
                _safe_ratio(reference_credit_total, scenario_total),
                4,
            ),
            "weighted_pass_rate_delta": round(
                _safe_ratio(kiu_credit_total, scenario_total)
                - _safe_ratio(reference_credit_total, scenario_total),
                4,
            )
            if scenario_total
            else 0.0,
            "usage_winner": _usage_winner(
                kiu_score=_average(kiu_case_scores),
                reference_score=_average(reference_case_scores),
                kiu_pass_rate=_safe_ratio(kiu_credit_total, scenario_total),
                reference_pass_rate=_safe_ratio(reference_credit_total, scenario_total),
            ),
            "failure_tag_counts": _aggregate_failure_counts(
                pair.get("kiu_usage_review", {}).get("failure_tag_counts", {})
                for pair in matched_pairs
            ),
            "top_failure_modes": _aggregate_top_items(
                pair.get("kiu_usage_review", {}).get("failure_tag_counts", {})
                for pair in matched_pairs
            ),
            "repair_target_counts": _aggregate_failure_counts(
                pair.get("kiu_usage_review", {}).get("repair_target_counts", {})
                for pair in matched_pairs
            ),
            "dominant_repair_targets": _aggregate_top_items(
                pair.get("kiu_usage_review", {}).get("repair_target_counts", {})
                for pair in matched_pairs
            ),
            "repair_owner_counts": _aggregate_failure_counts(
                pair.get("kiu_usage_review", {}).get("repair_owner_counts", {})
                for pair in matched_pairs
            ),
            "dominant_repair_owners": _aggregate_top_items(
                pair.get("kiu_usage_review", {}).get("repair_owner_counts", {})
                for pair in matched_pairs
            ),
            "critical_case_count": sum(
                int(pair.get("kiu_usage_review", {}).get("critical_case_count", 0) or 0)
                for pair in matched_pairs
            ),
            "major_case_count": sum(
                int(pair.get("kiu_usage_review", {}).get("major_case_count", 0) or 0)
                for pair in matched_pairs
            ),
        },
        "notes": notes,
    }


def _build_scorecard(
    *,
    kiu_bundle: dict[str, Any],
    generated_run: dict[str, Any] | None,
    reference_pack: dict[str, Any],
    same_scenario_usage: dict[str, Any],
) -> dict[str, Any]:
    bundle_errors = int(kiu_bundle.get("validator_errors", 0) or 0)
    bundle_warnings = int(kiu_bundle.get("validator_warnings", 0) or 0)
    structural_cleanliness = max(0.0, 1.0 - 0.25 * bundle_errors - 0.05 * bundle_warnings)
    boundary_explicit = 1.0 if kiu_bundle.get("workflow_boundary", {}).get("explicit_boundary") else 0.0
    boundary_preserved = (
        1.0 if generated_run and generated_run.get("workflow_boundary_preserved") else 0.0
    )
    verification_gate = (
        1.0 if generated_run and generated_run.get("verification_gate_present") else 0.0
    )
    workflow_verification_ready = (
        min(float(generated_run.get("workflow_verification_ready_ratio", 0.0) or 0.0), 1.0)
        if generated_run is not None
        else 0.0
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
            0.30 * structural_cleanliness
            + 0.20 * boundary_explicit
            + 0.15 * boundary_preserved
            + 0.10 * verification_gate
            + 0.10 * workflow_verification_ready
            + 0.10 * quality_gate
            + 0.05 * review_score
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
    cold_start_proof_ratio = 1.0 if pipeline_artifacts.get("raw_book_no_seed_cold_start") else 0.0
    stage_presence_ratio = _average(
        [
            cold_start_proof_ratio,
            1.0 if pipeline_artifacts.get("book_overview_present") else 0.0,
            1.0 if pipeline_artifacts.get("source_chunks_present") else 0.0,
            1.0 if pipeline_artifacts.get("extraction_result_present") else 0.0,
            1.0 if pipeline_artifacts.get("graph_present") else 0.0,
            1.0 if pipeline_artifacts.get("verification_summary_present") else 0.0,
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
    cangjie_methodology_quality = _build_cangjie_methodology_quality(
        pipeline_artifacts=pipeline_artifacts,
        same_scenario_usage=same_scenario_usage,
    )
    final_artifact_effect = _build_final_artifact_effect_gate(
        generated_run=generated_run,
        same_scenario_usage=same_scenario_usage,
        cangjie_methodology_quality=cangjie_methodology_quality,
    )

    distillation_review = (
        generated_run.get("graph_to_skill_distillation", {})
        if generated_run is not None
        else {}
    )
    graph_to_skill_distillation_score = round(
        float(distillation_review.get("overall_score_100", 0.0) or 0.0),
        1,
    )
    v061_gate = _build_v061_distillation_gate(
        generated_run=generated_run,
        same_scenario_usage=same_scenario_usage,
        distillation_score_100=graph_to_skill_distillation_score,
    )
    cangjie_core_baseline_matrix = _build_cangjie_core_baseline_matrix(
        pipeline_artifacts=pipeline_artifacts,
        generated_run=generated_run,
        same_scenario_usage=same_scenario_usage,
        methodology_details=cangjie_methodology_quality["details"],
        stage_presence_ratio=stage_presence_ratio,
        extractor_coverage_ratio=extractor_coverage_ratio,
    )

    compatibility_regression = _build_compatibility_regression(pipeline_artifacts)

    return {
        "kiu_foundation_retained_100": foundation_score,
        "graphify_core_absorbed_100": graphify_score,
        "cangjie_core_absorbed_100": cangjie_score,
        "cangjie_methodology_internal_100": cangjie_methodology_quality["internal_score_100"],
        "cangjie_methodology_external_blind_100": cangjie_methodology_quality["external_blind_preference_score_100"],
        "cangjie_methodology_closure_100": cangjie_methodology_quality["closure_score_100"],
        "cangjie_methodology_quality_100": cangjie_methodology_quality["closure_score_100"],
        "cangjie_methodology_gate": cangjie_methodology_quality["gate"],
        "cangjie_core_baseline_matrix": cangjie_core_baseline_matrix,
        "final_artifact_effect": final_artifact_effect,
        "compatibility_regression": compatibility_regression,
        "book_to_skill_cold_start_proven": bool(cold_start_proof_ratio),
        "book_to_skill_cold_start_proven_100": round(100.0 * cold_start_proof_ratio, 1),
        "graph_to_skill_distillation_100": graph_to_skill_distillation_score,
        "v061_distillation_gate": v061_gate,
        "details": {
            "kiu_foundation_retained": {
                "structural_cleanliness": round(structural_cleanliness, 4),
                "boundary_explicit_ratio": boundary_explicit,
                "boundary_preserved_ratio": boundary_preserved,
                "verification_gate_ratio": verification_gate,
                "workflow_verification_ready_ratio": workflow_verification_ready,
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
                "cold_start_proof_ratio": round(cold_start_proof_ratio, 4),
                "pipeline_stage_presence_ratio": round(stage_presence_ratio, 4),
                "pipeline_mode": pipeline_artifacts.get("pipeline_mode"),
                "source_bundle_skill_count": pipeline_artifacts.get("source_bundle_skill_count"),
                "extractor_coverage_ratio": round(extractor_coverage_ratio, 4),
                "throughput_vs_reference_ratio": round(throughput_ratio, 4),
                "usage_quality_ratio": round(usage_quality_ratio, 4),
                "extractor_kinds": sorted(extraction_kinds),
            },
            "cangjie_methodology_quality": cangjie_methodology_quality["details"],
            "graph_to_skill_distillation": distillation_review,
        },
    }


def _build_compatibility_regression(pipeline_artifacts: dict[str, Any]) -> dict[str, Any]:
    summary = pipeline_artifacts.get("compatibility_regression_summary")
    if not isinstance(summary, dict):
        return {
            "schema_version": "kiu.compatibility-regression/v0.1",
            "risk": "unknown_until_baseline_rerun",
            "baseline": "v0.6.4",
        }
    executed = int(summary.get("executed", 0) or 0)
    failed = int(summary.get("failed", 0) or 0)
    passed = int(summary.get("passed", 0) or 0)
    if executed <= 0:
        risk = "unknown_until_baseline_rerun"
    elif failed > 0:
        risk = "fail"
    elif passed < executed:
        risk = "warn"
    else:
        risk = "pass"
    return {
        "schema_version": "kiu.compatibility-regression/v0.1",
        "risk": risk,
        "baseline": str(summary.get("baseline", "v0.6.4")),
        "executed": executed,
        "passed": passed,
        "failed": failed,
        "report_path": summary.get("report_path"),
    }


def _build_cangjie_core_baseline_matrix(
    *,
    pipeline_artifacts: dict[str, Any],
    generated_run: dict[str, Any] | None,
    same_scenario_usage: dict[str, Any],
    methodology_details: dict[str, float],
    stage_presence_ratio: float,
    extractor_coverage_ratio: float,
) -> dict[str, Any]:
    summary = same_scenario_usage.get("summary", {}) if isinstance(same_scenario_usage, dict) else {}
    scenario_count = int(summary.get("scenario_count", 0) or 0)
    same_source_ratio = 1.0 if summary.get("usage_winner") == "kiu" and scenario_count >= 20 else 0.0
    workflow_boundary_ratio = 1.0 if generated_run and generated_run.get("workflow_boundary_preserved") else 0.0
    rows = [
        _cangjie_matrix_row(
            capability_id="ria_tv_stages",
            score_ratio=stage_presence_ratio,
            evidence="raw-book stage artifacts: book overview, chunks, extraction, graph, verification, generated run",
            missing_reason="ria_tv_stage_evidence_missing_or_weak",
        ),
        _cangjie_matrix_row(
            capability_id="five_extractors",
            score_ratio=extractor_coverage_ratio,
            evidence=f"extractor_kinds={','.join(pipeline_artifacts.get('extractor_kinds', []))}",
            missing_reason="five_extractor_evidence_missing_or_weak",
        ),
        _cangjie_matrix_row(
            capability_id="triple_verification",
            score_ratio=float(methodology_details.get("triple_verification_ratio", 0.0) or 0.0),
            evidence="triple verification summary: cross evidence, predictive action, uniqueness",
            missing_reason="triple_verification_missing_or_weak",
        ),
        _cangjie_matrix_row(
            capability_id="decoy_pressure",
            score_ratio=float(methodology_details.get("decoy_pressure_test_ratio", 0.0) or 0.0),
            evidence="pressure_test_summary.pass_ratio",
            missing_reason="decoy_pressure_missing_or_weak",
        ),
        _cangjie_matrix_row(
            capability_id="blind_preference",
            score_ratio=float(methodology_details.get("blind_preference_review_ratio", 0.0) or 0.0),
            evidence="blind_preference_summary.pass_ratio",
            missing_reason="blind_preference_missing_or_weak",
        ),
        _cangjie_matrix_row(
            capability_id="same_source_benchmark",
            score_ratio=same_source_ratio,
            evidence=f"usage_winner={summary.get('usage_winner')}; scenario_count={scenario_count}",
            missing_reason="same_source_benchmark_missing_or_not_won",
        ),
        _cangjie_matrix_row(
            capability_id="workflow_boundary_preservation",
            score_ratio=workflow_boundary_ratio,
            evidence="generated_run.workflow_boundary_preserved",
            missing_reason="workflow_boundary_preservation_missing_or_weak",
        ),
    ]
    missing = [row["capability_id"] for row in rows if row["status"] != "pass"]
    return {
        "schema_version": "kiu.cangjie-core-baseline-matrix/v0.1",
        "summary": {
            "ready": not missing,
            "missing_p0_count": len(missing),
            "missing_capabilities": missing,
        },
        "rows": rows,
    }


def _cangjie_matrix_row(
    *,
    capability_id: str,
    score_ratio: float,
    evidence: str,
    missing_reason: str,
    threshold: float = 0.8,
) -> dict[str, Any]:
    score = _bounded_ratio(score_ratio)
    if score >= threshold:
        status = "pass"
        reason = ""
    elif score <= 0.0:
        status = "missing"
        reason = missing_reason
    else:
        status = "weak"
        reason = missing_reason
    return {
        "capability_id": capability_id,
        "status": status,
        "score_ratio": round(score, 4),
        "threshold": threshold,
        "evidence": evidence,
        "missing_reason": reason,
    }


def _build_final_artifact_effect_gate(
    *,
    generated_run: dict[str, Any] | None,
    same_scenario_usage: dict[str, Any],
    cangjie_methodology_quality: dict[str, Any],
) -> dict[str, Any]:
    summary = same_scenario_usage.get("summary", {}) if isinstance(same_scenario_usage, dict) else {}
    same_scenario_score = float(summary.get("kiu_average_usage_score_100", 0.0) or 0.0)
    generated_usage_score = (
        float(generated_run.get("usage_score_100", 0.0) or 0.0)
        if generated_run is not None
        else 0.0
    )
    layer1_score = round(max(same_scenario_score, generated_usage_score), 1)
    layer2_score = round(
        float(cangjie_methodology_quality.get("internal_score_100", 0.0) or 0.0),
        1,
    )
    external_blind_score = round(
        float(
            cangjie_methodology_quality.get(
                "external_blind_preference_score_100",
                0.0,
            )
            or 0.0
        ),
        1,
    )
    reasons: list[str] = []
    if layer1_score < 80.0:
        reasons.append("immediate_usage_effect_below_80")
    if summary.get("usage_winner") not in (None, "kiu"):
        reasons.append("same_scenario_usage_not_won_by_kiu")
    if layer2_score < 80.0:
        reasons.append("knowledge_depth_effect_below_80")
    if external_blind_score < 80.0:
        reasons.append("external_blind_preference_below_80")
    methodology_gate = cangjie_methodology_quality.get("gate", {})
    if not methodology_gate.get("ready"):
        reasons.append("knowledge_depth_gate_not_ready")

    ready = not reasons
    if ready:
        claim = "two_layer_effect_proven"
    elif layer1_score >= 80.0 and layer2_score < 80.0:
        claim = "usage_effect_only"
    elif layer1_score >= 80.0 and layer2_score >= 80.0 and external_blind_score < 80.0:
        claim = "internal_depth_proven_external_blind_missing"
    elif layer2_score >= 80.0 and layer1_score < 80.0:
        claim = "knowledge_depth_without_usage_effect"
    else:
        claim = "not_proven"
    return {
        "schema_version": "kiu.final-artifact-effect/v0.1",
        "ready": ready,
        "claim": claim,
        "layer1_immediate_usage_effect_100": layer1_score,
        "layer2_knowledge_depth_effect_100": layer2_score,
        "layer3_external_blind_preference_effect_100": external_blind_score,
        "minimum_layer1_100": 80.0,
        "minimum_layer2_100": 80.0,
        "minimum_layer3_100": 80.0,
        "reasons": reasons,
    }


def _build_cangjie_methodology_quality(
    *,
    pipeline_artifacts: dict[str, Any],
    same_scenario_usage: dict[str, Any],
) -> dict[str, Any]:
    summary = same_scenario_usage.get("summary", {}) if isinstance(same_scenario_usage, dict) else {}
    usage_win_ratio = 1.0 if summary.get("usage_winner") == "kiu" else 0.0
    usage_case_ratio = min(_safe_ratio(summary.get("scenario_count", 0), 20), 1.0)
    usage_pressure_ratio = min(usage_win_ratio, usage_case_ratio)

    triple_summary = (
        pipeline_artifacts.get("triple_verification_summary", {})
        if isinstance(pipeline_artifacts.get("triple_verification_summary"), dict)
        else {}
    )
    stage_status = (
        pipeline_artifacts.get("ria_tv_stage_status", {})
        if isinstance(pipeline_artifacts.get("ria_tv_stage_status"), dict)
        else {}
    )
    stage_present = bool(pipeline_artifacts.get("ria_tv_stage_report_present"))

    principle_depth_ratio = _artifact_ratio(
        pipeline_artifacts,
        "principle_depth_review_ratio",
        "principle_depth_review_present",
    )
    if principle_depth_ratio == 0.0 and stage_present:
        principle_depth_ratio = _average(
            [
                1.0 if stage_status.get("stage0_book_overview") else 0.0,
                1.0 if stage_status.get("stage1_parallel_extractors") else 0.0,
                _bounded_ratio(triple_summary.get("predictive_action_ratio")),
                _bounded_ratio(triple_summary.get("uniqueness_ratio")),
            ]
        )
    cross_chapter_ratio = _artifact_ratio(
        pipeline_artifacts,
        "cross_chapter_synthesis_ratio",
        "cross_chapter_synthesis_present",
    )
    if cross_chapter_ratio == 0.0 and stage_present:
        cross_chapter_ratio = max(
            _bounded_ratio(triple_summary.get("cross_evidence_ratio")),
            1.0 if stage_status.get("stage3_linking") else 0.0,
        )
    triple_verification_ratio = _artifact_ratio(
        pipeline_artifacts,
        "triple_verification_ratio",
        "triple_verification_present",
    )
    if triple_verification_ratio == 0.0 and triple_summary:
        triple_verification_ratio = _average(
            [
                triple_summary.get("cross_evidence_ratio"),
                triple_summary.get("predictive_action_ratio"),
                triple_summary.get("uniqueness_ratio"),
            ]
        )
    decoy_pressure_ratio = _artifact_ratio(
        pipeline_artifacts,
        "decoy_pressure_test_ratio",
        "decoy_pressure_test_present",
    )
    pressure_summary = pipeline_artifacts.get("pressure_test_summary", {})
    if isinstance(pressure_summary, dict) and pressure_summary.get("pass_ratio") is not None:
        decoy_pressure_ratio = _bounded_ratio(pressure_summary.get("pass_ratio"))
    blind_review_ratio = _artifact_ratio(
        pipeline_artifacts,
        "blind_preference_review_ratio",
        "blind_preference_review_present",
    )
    blind_summary = pipeline_artifacts.get("blind_preference_summary", {})
    if isinstance(blind_summary, dict) and blind_summary.get("pass_ratio") is not None:
        blind_review_ratio = _bounded_ratio(blind_summary.get("pass_ratio"))

    internal_score = round(
        100.0
        * _average(
            [
                usage_pressure_ratio,
                principle_depth_ratio,
                cross_chapter_ratio,
                triple_verification_ratio,
                decoy_pressure_ratio,
            ]
        ),
        1,
    )
    external_blind_score = round(100.0 * blind_review_ratio, 1)
    closure_score = round(min(internal_score, external_blind_score), 1)
    details = {
        "same_scenario_usage_pressure_ratio": round(usage_pressure_ratio, 4),
        "principle_depth_review_ratio": round(principle_depth_ratio, 4),
        "cross_chapter_synthesis_ratio": round(cross_chapter_ratio, 4),
        "triple_verification_ratio": round(triple_verification_ratio, 4),
        "decoy_pressure_test_ratio": round(decoy_pressure_ratio, 4),
        "blind_preference_review_ratio": round(blind_review_ratio, 4),
    }
    gate = _build_cangjie_methodology_gate(
        internal_score_100=internal_score,
        external_blind_score_100=external_blind_score,
        closure_score_100=closure_score,
        details=details,
        usage_win=bool(usage_win_ratio),
    )
    return {
        "score_100": closure_score,
        "internal_score_100": internal_score,
        "external_blind_preference_score_100": external_blind_score,
        "closure_score_100": closure_score,
        "details": details,
        "gate": gate,
    }


def _artifact_ratio(
    artifacts: dict[str, Any],
    ratio_key: str,
    present_key: str,
) -> float:
    if ratio_key in artifacts:
        return _bounded_ratio(artifacts.get(ratio_key))
    return 1.0 if artifacts.get(present_key) else 0.0


def _bounded_ratio(value: Any) -> float:
    try:
        return min(max(float(value or 0.0), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.0


def _build_cangjie_methodology_gate(
    *,
    internal_score_100: float,
    external_blind_score_100: float,
    closure_score_100: float,
    details: dict[str, float],
    usage_win: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    if internal_score_100 < 80.0:
        reasons.append("cangjie_methodology_internal_below_80")
    if closure_score_100 < 80.0:
        reasons.append("cangjie_methodology_closure_below_80")
    if not usage_win:
        reasons.append("same_scenario_usage_not_won_by_kiu")
    thresholds = {
        "principle_depth_review_ratio": "principle_depth_review_missing_or_weak",
        "cross_chapter_synthesis_ratio": "cross_chapter_synthesis_missing_or_weak",
        "triple_verification_ratio": "triple_verification_missing_or_weak",
        "decoy_pressure_test_ratio": "decoy_pressure_test_missing_or_weak",
        "blind_preference_review_ratio": "blind_preference_review_missing_or_weak",
    }
    for key, reason in thresholds.items():
        if float(details.get(key, 0.0) or 0.0) < 0.8:
            reasons.append(reason)

    ready = not reasons
    if ready:
        claim = "cangjie_methodology_absorbed"
    elif usage_win:
        claim = "same_scenario_usage_win_only"
    else:
        claim = "not_proven"
    return {
        "schema_version": "kiu.cangjie-methodology-gate/v0.1",
        "ready": ready,
        "claim": claim,
        "minimum_methodology_internal_100": 80.0,
        "minimum_external_blind_preference_100": 80.0,
        "minimum_methodology_closure_100": 80.0,
        "actual_methodology_internal_100": internal_score_100,
        "actual_external_blind_preference_100": external_blind_score_100,
        "actual_methodology_closure_100": closure_score_100,
        "required_evidence": [
            "principle_depth_review",
            "cross_chapter_synthesis",
            "triple_verification",
            "decoy_pressure_test",
            "blind_preference_review",
        ],
        "reasons": reasons,
    }


def _review_graph_to_skill_distillation(bundle: Any) -> dict[str, Any]:
    graph_doc = getattr(bundle, "graph_doc", {}) or {}
    inferred_edge_ids = {
        str(edge.get("id"))
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict) and edge.get("id") and edge.get("extraction_kind") == "INFERRED"
    }
    ambiguous_ids = {
        str(edge.get("id"))
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict) and edge.get("id") and edge.get("extraction_kind") == "AMBIGUOUS"
    }
    ambiguous_ids.update(
        str(node.get("id"))
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("id") and node.get("extraction_kind") == "AMBIGUOUS"
    )

    referenced_inferred: set[str] = set()
    referenced_ambiguous: set[str] = set()
    graph_scenario_count = 0
    source_action_count = 0
    contract_count = 0
    navigation_skill_count = 0
    skill_count = len(getattr(bundle, "skills", {}) or {})

    for skill in getattr(bundle, "skills", {}).values():
        candidate_doc = _load_candidate_yaml(skill.skill_dir / "candidate.yaml")
        contract = candidate_doc.get("graph_to_skill_distillation", {}) if isinstance(candidate_doc, dict) else {}
        if isinstance(contract, dict) and contract.get("schema_version") == "kiu.graph-to-skill-distillation/v0.1":
            contract_count += 1
            navigation = contract.get("graph_navigation", {})
            if isinstance(navigation, dict) and navigation.get("communities"):
                navigation_skill_count += 1
        elif "Graph navigation:" in "\n".join(skill.sections.values()):
            navigation_skill_count += 1

        scenario_families = getattr(skill, "scenario_families", {})
        if not isinstance(scenario_families, dict):
            continue
        for bucket, ids in (
            ("should_trigger", inferred_edge_ids),
            ("edge_case", ambiguous_ids),
            ("refusal", ambiguous_ids),
        ):
            items = scenario_families.get(bucket, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("distillation_role", ""))
                scenario_id = str(item.get("scenario_id", ""))
                anchor_refs = {str(anchor) for anchor in item.get("anchor_refs", [])}
                graph_refs = anchor_refs & ids
                if role or scenario_id.startswith("graph-") or graph_refs:
                    graph_scenario_count += 1
                    if item.get("source_location") and item.get("next_action_shape"):
                        source_action_count += 1
                if bucket == "should_trigger":
                    referenced_inferred.update(anchor_refs & inferred_edge_ids)
                else:
                    referenced_ambiguous.update(anchor_refs & ambiguous_ids)

    inferred_ratio = _safe_ratio(len(referenced_inferred), len(inferred_edge_ids))
    ambiguous_ratio = _safe_ratio(len(referenced_ambiguous), len(ambiguous_ids))
    source_action_ratio = _safe_ratio(source_action_count, graph_scenario_count)
    contract_ratio = _safe_ratio(contract_count, skill_count)
    navigation_ratio = _safe_ratio(navigation_skill_count, skill_count)
    applicable = bool(inferred_edge_ids or ambiguous_ids)
    overall = 0.0
    if applicable:
        overall = round(
            100.0
            * _average(
                [
                    inferred_ratio if inferred_edge_ids else 1.0,
                    ambiguous_ratio if ambiguous_ids else 1.0,
                    source_action_ratio,
                    contract_ratio,
                    navigation_ratio,
                ]
            ),
            1,
        )
    return {
        "schema_version": "kiu.graph-to-skill-distillation-review/v0.1",
        "applicable": applicable,
        "overall_score_100": overall,
        "inferred_edge_count": len(inferred_edge_ids),
        "ambiguous_signal_count": len(ambiguous_ids),
        "referenced_inferred_edge_count": len(referenced_inferred),
        "referenced_ambiguous_signal_count": len(referenced_ambiguous),
        "graph_scenario_count": graph_scenario_count,
        "inferred_trigger_expansion_ratio": round(inferred_ratio, 4),
        "ambiguous_boundary_probe_ratio": round(ambiguous_ratio, 4),
        "source_location_action_ratio": round(source_action_ratio, 4),
        "contract_coverage_ratio": round(contract_ratio, 4),
        "graph_navigation_ratio": round(navigation_ratio, 4),
        "referenced_inferred_edge_ids": sorted(referenced_inferred),
        "referenced_ambiguous_signal_ids": sorted(referenced_ambiguous),
    }


def _load_candidate_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _build_v061_distillation_gate(
    *,
    generated_run: dict[str, Any] | None,
    same_scenario_usage: dict[str, Any],
    distillation_score_100: float,
) -> dict[str, Any]:
    reasons: list[str] = []
    if generated_run is None:
        reasons.append("missing_generated_run")
    elif not generated_run.get("workflow_boundary_preserved"):
        reasons.append("workflow_boundary_not_preserved")

    if distillation_score_100 < 90.0:
        reasons.append("graph_to_skill_distillation_below_90")

    summary = same_scenario_usage.get("summary", {}) if isinstance(same_scenario_usage, dict) else {}
    scenario_count = int(summary.get("scenario_count", 0) or 0)
    if scenario_count:
        if summary.get("usage_winner") != "kiu":
            reasons.append("same_scenario_usage_not_won_by_kiu")
        if summary.get("failure_tag_counts"):
            reasons.append("same_scenario_failure_tags_present")
        kiu_pass = float(summary.get("kiu_weighted_pass_rate", 0.0) or 0.0)
        reference_pass = float(summary.get("reference_weighted_pass_rate", 0.0) or 0.0)
        if kiu_pass < reference_pass:
            reasons.append("same_scenario_pass_rate_regressed")

    return {
        "schema_version": "kiu.v061-distillation-gate/v0.1",
        "ready": not reasons,
        "minimum_graph_to_skill_distillation_100": 90.0,
        "actual_graph_to_skill_distillation_100": distillation_score_100,
        "same_scenario_case_count": scenario_count,
        "reasons": reasons,
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


def _evaluate_kiu_usage_case(
    *,
    skill: Any,
    case: dict[str, Any],
    alignment_strength: float,
) -> dict[str, Any]:
    review = _review_kiu_skill(skill)
    contract = skill.contract or {}
    trigger = contract.get("trigger", {}) if isinstance(contract.get("trigger"), dict) else {}
    boundary = contract.get("boundary", {}) if isinstance(contract.get("boundary"), dict) else {}
    judgment_schema = (
        contract.get("judgment_schema", {})
        if isinstance(contract.get("judgment_schema"), dict)
        else {}
    )
    scenario_families = getattr(skill, "scenario_families", {})
    if not isinstance(scenario_families, dict):
        scenario_families = {}
    trigger_text = "\n".join(
        [
            skill.skill_id,
            str(skill.title),
            yaml.safe_dump(trigger, sort_keys=True, allow_unicode=True),
            str(skill.sections.get("Rationale", "")),
            str(skill.sections.get("Evidence Summary", "")),
            _render_scenario_family_text(
                scenario_families,
                buckets=("should_trigger",),
            ),
        ]
    )
    boundary_text = "\n".join(
        [
            yaml.safe_dump(boundary, sort_keys=True, allow_unicode=True),
            str(skill.sections.get("Revision Summary", "")),
            _render_scenario_family_text(
                scenario_families,
                buckets=("should_not_trigger", "edge_case", "refusal"),
            ),
        ]
    )
    action_text = "\n".join(
        [
            yaml.safe_dump(judgment_schema, sort_keys=True, allow_unicode=True),
            str(skill.sections.get("Usage Summary", "")),
            str(skill.sections.get("Evaluation Summary", "")),
            _render_scenario_family_text(
                scenario_families,
                buckets=("should_trigger", "edge_case", "refusal"),
            ),
        ]
    )
    return _evaluate_usage_case(
        case=case,
        review=review,
        title_text=f"{skill.skill_id}\n{skill.title}",
        trigger_text=trigger_text,
        boundary_text=boundary_text,
        action_text=action_text,
        supports_do_not_fire=bool(boundary.get("do_not_fire_when")),
        supports_edge=_supports_edge_handling(
            yaml.safe_dump(judgment_schema, sort_keys=True, allow_unicode=True)
            + "\n"
            + yaml.safe_dump(boundary, sort_keys=True, allow_unicode=True)
        ),
        supports_decline=_supports_decline_action(
            yaml.safe_dump(judgment_schema, sort_keys=True, allow_unicode=True)
            + "\n"
            + yaml.safe_dump(boundary, sort_keys=True, allow_unicode=True)
        ),
        alignment_strength=alignment_strength,
    )


def _evaluate_reference_usage_case(
    *,
    skill_id: str,
    markdown: str,
    frontmatter: dict[str, Any],
    sections: dict[str, str],
    case: dict[str, Any],
) -> dict[str, Any]:
    review = _review_reference_skill(
        skill_id=skill_id,
        frontmatter=frontmatter,
        sections=sections,
        markdown=markdown,
    )
    description = str(frontmatter.get("description", "") or "")
    trigger_text = "\n".join(
        [
            skill_id,
            description,
            _find_section(sections, prefixes=("A2",), keywords=("触发", "Trigger")),
            _find_section(sections, prefixes=("R",), keywords=("原文", "Reading")),
        ]
    )
    boundary_text = _find_section(
        sections,
        prefixes=("B",),
        keywords=("边界", "Boundary"),
    )
    action_text = _find_section(
        sections,
        prefixes=("E",),
        keywords=("执行", "Execution"),
    )
    return _evaluate_usage_case(
        case=case,
        review=review,
        title_text=f"{skill_id}\n{description}",
        trigger_text=trigger_text,
        boundary_text=boundary_text,
        action_text=action_text,
        supports_do_not_fire=bool(boundary_text),
        supports_edge=_supports_edge_handling(boundary_text + "\n" + action_text),
        supports_decline=_supports_decline_action(boundary_text + "\n" + action_text),
        alignment_strength=1.0,
    )


def _evaluate_usage_case(
    *,
    case: dict[str, Any],
    review: dict[str, Any],
    title_text: str,
    trigger_text: str,
    boundary_text: str,
    action_text: str,
    supports_do_not_fire: bool,
    supports_edge: bool,
    supports_decline: bool,
    alignment_strength: float,
) -> dict[str, Any]:
    case_type = str(case.get("type", "") or "")
    prompt = str(case.get("prompt", "") or "")
    expected_behavior = str(case.get("expected_behavior", "") or "")
    notes = str(case.get("notes", "") or "")
    case_text = "\n".join([prompt, expected_behavior, notes])

    trigger_clarity = float(review.get("trigger_clarity_100", 0.0) or 0.0) / 100.0
    boundary_clarity = float(review.get("boundary_clarity_100", 0.0) or 0.0) / 100.0
    actionability = float(review.get("actionability_100", 0.0) or 0.0) / 100.0
    core_overlap = max(
        _text_overlap_ratio(case_text, title_text),
        _text_overlap_ratio(expected_behavior, trigger_text),
    )
    boundary_overlap = _text_overlap_ratio(expected_behavior + "\n" + notes, boundary_text)
    action_overlap = _text_overlap_ratio(expected_behavior, action_text)
    concept_query = _looks_like_concept_query(case_text)
    concept_query_boundary = _supports_concept_query_boundary(boundary_text)

    if case_type == "should_trigger":
        trigger_ratio = _average(
            [
                alignment_strength,
                trigger_clarity,
                max(core_overlap, alignment_strength * 0.55),
            ]
        )
        boundary_ratio = _average(
            [
                boundary_clarity,
                1.0 if supports_do_not_fire else 0.45,
                max(boundary_overlap, 0.2 if supports_do_not_fire else 0.0),
            ]
        )
        next_action_ratio = _average(
            [
                actionability,
                max(action_overlap, 0.35),
                1.0 if supports_decline else 0.6,
            ]
        )
        threshold = 75.0
        overall = round(
            100.0 * (0.45 * trigger_ratio + 0.20 * boundary_ratio + 0.35 * next_action_ratio),
            1,
        )
    elif case_type == "should_not_trigger":
        restraint_reason = max(
            boundary_overlap,
            1.0 if concept_query and concept_query_boundary else 0.0,
        )
        trigger_ratio = _average(
            [
                boundary_clarity,
                1.0 if supports_do_not_fire else 0.0,
                restraint_reason,
            ]
        )
        boundary_ratio = _average(
            [
                boundary_clarity,
                restraint_reason,
                1.0 if (concept_query_boundary or (supports_do_not_fire and not concept_query)) else 0.0,
            ]
        )
        next_action_ratio = _average(
            [
                actionability,
                1.0 if supports_decline else 0.2,
                restraint_reason,
            ]
        )
        threshold = 75.0
        overall = round(
            100.0 * (0.25 * trigger_ratio + 0.50 * boundary_ratio + 0.25 * next_action_ratio),
            1,
        )
    else:
        edge_ratio = 1.0 if supports_edge else 0.0
        trigger_ratio = _average(
            [
                alignment_strength,
                trigger_clarity,
                max(core_overlap, alignment_strength * 0.45),
            ]
        )
        boundary_ratio = _average(
            [
                boundary_clarity,
                edge_ratio,
                max(boundary_overlap, 0.2 if supports_do_not_fire else 0.0),
            ]
        )
        next_action_ratio = _average(
            [
                actionability,
                max(action_overlap, 0.3),
                1.0 if supports_decline else 0.55,
            ]
        )
        threshold = 65.0
        overall = round(
            100.0 * (0.30 * trigger_ratio + 0.40 * boundary_ratio + 0.30 * next_action_ratio),
            1,
        )

    verdict, credit = _usage_verdict(
        score_100=overall,
        threshold_100=threshold,
        strict=(case_type == "should_not_trigger"),
    )
    failure_analysis = _build_failure_analysis(
        case_type=case_type,
        verdict=verdict,
        threshold_100=threshold,
        overall_score_100=overall,
        trigger_ratio=trigger_ratio,
        boundary_ratio=boundary_ratio,
        next_action_ratio=next_action_ratio,
        core_overlap=core_overlap,
        boundary_overlap=boundary_overlap,
        action_overlap=action_overlap,
        supports_do_not_fire=supports_do_not_fire,
        supports_edge=supports_edge,
        concept_query=concept_query,
        concept_query_boundary=concept_query_boundary,
    )
    review_notes = [
        f"alignment_strength:{round(alignment_strength, 2)}",
        "concept_query_case" if concept_query else "",
        "concept_query_boundary_missing" if concept_query and not concept_query_boundary else "",
        "boundary_reason_sparse" if boundary_overlap < 0.12 else "boundary_reason_covered",
        "next_action_sparse" if action_overlap < 0.12 and not supports_decline else "",
        "edge_support_missing" if case_type == "edge_case" and not supports_edge else "",
    ]
    return {
        "overall_score_100": overall,
        "trigger_precision_100": round(100.0 * trigger_ratio, 1),
        "boundary_discipline_100": round(100.0 * boundary_ratio, 1),
        "next_action_specificity_100": round(100.0 * next_action_ratio, 1),
        "verdict": verdict,
        "credit": credit,
        "failure_analysis": failure_analysis,
        "notes": [note for note in review_notes if note],
    }


def _summarize_usage_case_reviews(
    *,
    case_reviews: list[dict[str, Any]],
    minimum_pass_rate: float,
) -> dict[str, Any]:
    scenario_count = len(case_reviews)
    pass_count = sum(1 for item in case_reviews if item.get("verdict") == "pass")
    partial_count = sum(1 for item in case_reviews if item.get("verdict") == "partial")
    fail_count = sum(1 for item in case_reviews if item.get("verdict") == "fail")
    credit_total = sum(float(item.get("credit", 0.0) or 0.0) for item in case_reviews)
    strict_non_trigger_passed = all(
        item.get("verdict") == "pass"
        for item in case_reviews
        if item.get("type") == "should_not_trigger"
    )
    pass_rate = _safe_ratio(credit_total, scenario_count)
    failure_tag_counts = _aggregate_failure_counts(
        item.get("failure_analysis", {}).get("tag_counts", {})
        if isinstance(item.get("failure_analysis"), dict)
        else {}
        for item in case_reviews
    )
    repair_target_counts = _aggregate_failure_counts(
        item.get("failure_analysis", {}).get("repair_target_counts", {})
        if isinstance(item.get("failure_analysis"), dict)
        else {}
        for item in case_reviews
    )
    repair_owner_counts = _aggregate_failure_counts(
        item.get("failure_analysis", {}).get("repair_owner_counts", {})
        if isinstance(item.get("failure_analysis"), dict)
        else {}
        for item in case_reviews
    )
    severity_counts = _aggregate_failure_counts(
        (
            {str(item.get("failure_analysis", {}).get("severity", "none")): 1}
            if isinstance(item.get("failure_analysis"), dict)
            else {}
        )
        for item in case_reviews
    )
    return {
        "overall_score_100": round(
            _average([item.get("overall_score_100") for item in case_reviews]),
            1,
        ),
        "scenario_count": scenario_count,
        "pass_count": pass_count,
        "partial_count": partial_count,
        "fail_count": fail_count,
        "credit_total": round(credit_total, 4),
        "weighted_pass_rate": round(pass_rate, 4),
        "minimum_pass_rate": minimum_pass_rate,
        "strict_non_trigger_passed": strict_non_trigger_passed,
        "meets_minimum_pass_rate": bool(
            scenario_count
            and pass_rate >= minimum_pass_rate
            and strict_non_trigger_passed
        ),
        "failure_tag_counts": failure_tag_counts,
        "top_failure_modes": _aggregate_top_items([failure_tag_counts]),
        "repair_target_counts": repair_target_counts,
        "dominant_repair_targets": _aggregate_top_items([repair_target_counts]),
        "repair_owner_counts": repair_owner_counts,
        "dominant_repair_owners": _aggregate_top_items([repair_owner_counts]),
        "severity_counts": severity_counts,
        "critical_case_count": int(severity_counts.get("critical", 0) or 0),
        "major_case_count": int(severity_counts.get("major", 0) or 0),
    }


def _usage_verdict(
    *,
    score_100: float,
    threshold_100: float,
    strict: bool,
) -> tuple[str, float]:
    if score_100 >= threshold_100:
        return "pass", 1.0
    partial_floor = threshold_100 - (20.0 if strict else 15.0)
    if score_100 >= partial_floor:
        return "partial", 0.0 if strict else 0.5
    return "fail", 0.0


def _usage_winner(
    *,
    kiu_score: float,
    reference_score: float,
    kiu_pass_rate: float,
    reference_pass_rate: float,
) -> str:
    if kiu_pass_rate > reference_pass_rate:
        return "kiu"
    if kiu_pass_rate < reference_pass_rate:
        return "reference"
    if kiu_score > reference_score:
        return "kiu"
    if kiu_score < reference_score:
        return "reference"
    return "tie"


def _build_failure_analysis(
    *,
    case_type: str,
    verdict: str,
    threshold_100: float,
    overall_score_100: float,
    trigger_ratio: float,
    boundary_ratio: float,
    next_action_ratio: float,
    core_overlap: float,
    boundary_overlap: float,
    action_overlap: float,
    supports_do_not_fire: bool,
    supports_edge: bool,
    concept_query: bool,
    concept_query_boundary: bool,
) -> dict[str, Any]:
    tags: list[str] = []
    if case_type == "should_trigger" and trigger_ratio < 0.72:
        tags.append("trigger_miss")
    if (
        case_type == "should_not_trigger"
        and (
            boundary_ratio < 0.75
            or not supports_do_not_fire
            or (concept_query and not concept_query_boundary)
        )
    ):
        tags.append("boundary_leak")
    if next_action_ratio < 0.62:
        tags.append("next_step_blunt")
    if case_type == "edge_case" and not supports_edge:
        tags.append("edge_case_collapse")
    if max(core_overlap, boundary_overlap, action_overlap) < 0.14:
        tags.append("generic_reasoning")

    primary_gap = _primary_failure_gap(
        case_type=case_type,
        tags=tags,
        trigger_ratio=trigger_ratio,
        boundary_ratio=boundary_ratio,
        next_action_ratio=next_action_ratio,
    )
    score_gap_100 = round(max(threshold_100 - overall_score_100, 0.0), 1)
    severity = _failure_severity(
        case_type=case_type,
        verdict=verdict,
        tags=tags,
        score_gap_100=score_gap_100,
    )
    repair_targets = _repair_targets_for_tags(tags, primary_gap=primary_gap)
    repair_owners = _repair_owners_for_tags(tags, primary_gap=primary_gap)
    return {
        "tags": tags,
        "tag_counts": {tag: 1 for tag in tags},
        "severity": severity,
        "repair_targets": repair_targets,
        "repair_target_counts": {target: 1 for target in repair_targets},
        "repair_owners": repair_owners,
        "repair_owner_counts": {owner: 1 for owner in repair_owners},
        "primary_gap": primary_gap,
        "score_gap_100": score_gap_100,
    }


def _primary_failure_gap(
    *,
    case_type: str,
    tags: list[str],
    trigger_ratio: float,
    boundary_ratio: float,
    next_action_ratio: float,
) -> str:
    priority = [
        "boundary_leak",
        "trigger_miss",
        "edge_case_collapse",
        "next_step_blunt",
        "generic_reasoning",
    ]
    for item in priority:
        if item in tags:
            return item
    if case_type == "should_not_trigger":
        return "boundary_leak" if boundary_ratio <= min(trigger_ratio, next_action_ratio) else "next_step_blunt"
    if trigger_ratio <= min(boundary_ratio, next_action_ratio):
        return "trigger_miss"
    if next_action_ratio <= min(trigger_ratio, boundary_ratio):
        return "next_step_blunt"
    return "generic_reasoning"


def _failure_severity(
    *,
    case_type: str,
    verdict: str,
    tags: list[str],
    score_gap_100: float,
) -> str:
    if not tags and verdict == "pass":
        return "none"
    if (
        (case_type == "should_not_trigger" and verdict == "fail")
        or ("boundary_leak" in tags and score_gap_100 >= 10.0)
        or score_gap_100 >= 25.0
    ):
        return "critical"
    if verdict == "fail" or len(tags) >= 2 or score_gap_100 >= 12.0:
        return "major"
    return "minor"


def _repair_targets_for_tags(tags: list[str], *, primary_gap: str) -> list[str]:
    mapping = {
        "trigger_miss": [
            "contract.trigger.patterns",
            "contract.intake.required",
        ],
        "boundary_leak": [
            "contract.boundary.do_not_fire_when",
            "contract.boundary.fails_when",
        ],
        "next_step_blunt": [
            "contract.judgment_schema.output",
            "usage_summary.representative_cases",
        ],
        "generic_reasoning": [
            "evidence_summary.anchor_refs",
            "usage_summary.representative_cases",
        ],
        "edge_case_collapse": [
            "contract.boundary.fails_when",
            "usage_summary.representative_cases",
        ],
    }
    ordered_tags = list(tags) if tags else [primary_gap]
    targets: list[str] = []
    for tag in ordered_tags:
        for target in mapping.get(tag, []):
            if target not in targets:
                targets.append(target)
    return targets


def _repair_owners_for_tags(tags: list[str], *, primary_gap: str) -> list[str]:
    mapping = {
        "trigger_miss": ["contract", "extraction"],
        "boundary_leak": ["contract", "routing"],
        "next_step_blunt": ["drafting", "contract"],
        "generic_reasoning": ["extraction", "drafting"],
        "edge_case_collapse": ["seed_verification", "contract"],
    }
    ordered_tags = list(tags) if tags else [primary_gap]
    owners: list[str] = []
    for tag in ordered_tags:
        for owner in mapping.get(tag, []):
            if owner not in owners:
                owners.append(owner)
    return owners


def _aggregate_failure_counts(count_docs: Any) -> dict[str, int]:
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


def _aggregate_top_items(count_docs: Any) -> list[dict[str, Any]]:
    counts = _aggregate_failure_counts(count_docs)
    return [
        {"name": key, "count": value}
        for key, value in counts.items()
    ][:5]


def _relationship_alignment_strength(relationship: str | None) -> float:
    mapping = {
        "direct_match": 1.0,
        "close_match": 0.9,
        "thematic_overlap": 0.75,
        "partial_overlap": 0.65,
        "exact_slug_match": 1.0,
        "aligned": 0.8,
    }
    return mapping.get(str(relationship or "aligned"), 0.8)


def _supports_edge_handling(text: str) -> bool:
    return _contains_any(
        text,
        (
            "edge",
            "partial",
            "ask_or_delegate",
            "act_with_boundary",
            "bounded temporary action",
            "谨慎",
            "边界",
            "圈外",
            "圈内",
            "部分",
            "defer",
            "delegate",
            "authorization",
            "study_more",
        ),
    )


def _supports_decline_action(text: str) -> bool:
    return _contains_any(
        text,
        (
            "decline",
            "study_more",
            "defer",
            "pass",
            "reject",
            "do_not_fire",
            "do_not_apply",
            "ask_or_delegate",
            "refuse",
            "不要",
            "不应",
            "拒绝",
            "暂缓",
            "放弃",
        ),
    )


def _has_decision_action_field(output_schema: dict[str, Any]) -> bool:
    return any(
        field in output_schema
        for field in (
            "next_action",
            "recommended_action",
            "first_preventive_action",
            "avoid_rules",
        )
    )


def _has_diagnostic_action_field(output_schema: dict[str, Any]) -> bool:
    return any(
        field in output_schema
        for field in (
            "evidence_to_check",
            "decline_reason",
            "missing_knowledge",
            "failure_modes",
        )
    )


def _usage_summary_has_cases(text: str) -> bool:
    summary = str(text or "")
    return bool(
        re.search(r"Representative cases:", summary)
        or re.search(r"^\s*-\s+`", summary, flags=re.MULTILINE)
    )


def _supports_concept_query_boundary(text: str) -> bool:
    return _contains_any(
        text,
        (
            "concept",
            "definition",
            "explain",
            "history",
            "概念",
            "定义",
            "解释",
            "历史",
            "知识查询",
            "知识问答",
        ),
    )


def _looks_like_concept_query(text: str) -> bool:
    return _contains_any(
        text,
        (
            "是什么",
            "怎么定义",
            "定义",
            "概念",
            "讲几个",
            "历史故事",
            "解释",
            "what is",
            "define",
            "history",
            "concept",
        ),
    )


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def _render_scenario_family_text(
    scenario_families: dict[str, Any],
    *,
    buckets: tuple[str, ...],
) -> str:
    lines: list[str] = []
    for bucket in buckets:
        items = scenario_families.get(bucket, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            scenario_id = str(item.get("scenario_id", f"{bucket}-scenario"))
            summary = str(item.get("summary", "") or "").strip()
            boundary_reason = str(item.get("boundary_reason", "") or "").strip()
            next_action_shape = str(item.get("next_action_shape", "") or "").strip()
            signals = [
                str(signal).strip()
                for signal in item.get("prompt_signals", [])
                if str(signal).strip()
            ]
            anchor_refs = [
                str(anchor).strip()
                for anchor in item.get("anchor_refs", [])
                if str(anchor).strip()
            ]
            lines.append(f"{bucket}:{scenario_id}")
            if summary:
                lines.append(summary)
            if signals:
                lines.append("signals: " + " ".join(signals))
            if boundary_reason:
                lines.append("boundary: " + boundary_reason)
            if next_action_shape:
                lines.append("next: " + next_action_shape)
            if anchor_refs:
                lines.append("anchors: " + " ".join(anchor_refs))
    return "\n".join(lines)


def _text_overlap_ratio(query_text: str, doc_text: str) -> float:
    query_tokens = _usage_tokens(query_text)
    doc_tokens = _usage_tokens(doc_text)
    if not query_tokens or not doc_tokens:
        return 0.0
    overlap = len(query_tokens & doc_tokens)
    denominator = max(4, min(len(query_tokens), 12))
    return round(min(overlap / denominator, 1.0), 4)


def _usage_tokens(text: str) -> set[str]:
    lowered = text.lower()
    ascii_tokens = set(re.findall(r"[a-z][a-z0-9_-]{1,}", lowered))
    cjk_tokens: set[str] = set()
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        cjk_tokens.add(segment)
        for width in (2, 3):
            if len(segment) < width:
                continue
            for index in range(len(segment) - width + 1):
                cjk_tokens.add(segment[index : index + width])
    return ascii_tokens | cjk_tokens


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
    output_schema = (
        judgment_schema.get("output", {}).get("schema", {})
        if isinstance(judgment_schema.get("output"), dict)
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
            1.0 if len(output_schema) >= 3 else 0.0,
            1.0 if _has_decision_action_field(output_schema) else 0.0,
            1.0 if _has_diagnostic_action_field(output_schema) else 0.0,
            1.0 if skill.trace_refs else 0.0,
            1.0 if skill.sections.get("Usage Summary") else 0.0,
            1.0 if _usage_summary_has_cases(skill.sections.get("Usage Summary", "")) else 0.0,
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
        resolved_pairs = []
        for pair in pairs:
            if not isinstance(pair, dict):
                continue
            kiu_skill_id = _resolve_alignment_skill_id(
                requested_id=pair.get("kiu_skill_id"),
                available_reviews=kiu_reviews,
            )
            reference_skill_id = _resolve_alignment_skill_id(
                requested_id=pair.get("reference_skill_id"),
                available_reviews=reference_reviews,
            )
            if kiu_skill_id is None or reference_skill_id is None:
                continue
            resolved_pair = dict(pair)
            resolved_pair["kiu_skill_id"] = kiu_skill_id
            resolved_pair["reference_skill_id"] = reference_skill_id
            resolved_pairs.append(resolved_pair)
        return _dedupe_alignment_pairs(resolved_pairs)
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


def _resolve_alignment_skill_id(
    *,
    requested_id: Any,
    available_reviews: dict[str, Any],
) -> str | None:
    if not isinstance(requested_id, str) or not requested_id:
        return None
    if requested_id in available_reviews:
        return requested_id

    requested_base = _normalize_alignment_skill_id(requested_id)
    matches = sorted(
        skill_id
        for skill_id in available_reviews
        if _normalize_alignment_skill_id(skill_id) == requested_base
    )
    if len(matches) == 1:
        return matches[0]
    return None


def _normalize_alignment_skill_id(skill_id: str) -> str:
    normalized = str(skill_id or "")
    for suffix in ("-source-note",):
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)]
    return normalized


def _dedupe_alignment_pairs(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_reference: dict[str, tuple[tuple[float, int, int], int]] = {}
    for index, pair in enumerate(pairs):
        reference_skill_id = pair.get("reference_skill_id")
        if not isinstance(reference_skill_id, str) or not reference_skill_id:
            continue
        rank = _alignment_pair_rank(pair, index=index)
        current = best_by_reference.get(reference_skill_id)
        if current is None or rank > current[0]:
            best_by_reference[reference_skill_id] = (rank, index)
    selected_indexes = sorted(item[1] for item in best_by_reference.values())
    return [pairs[index] for index in selected_indexes]


def _alignment_pair_rank(pair: dict[str, Any], *, index: int) -> tuple[float, int, int]:
    kiu_skill_id = str(pair.get("kiu_skill_id", "") or "")
    reference_skill_id = str(pair.get("reference_skill_id", "") or "")
    return (
        _relationship_alignment_strength(pair.get("relationship")),
        1
        if _normalize_alignment_skill_id(kiu_skill_id)
        == _normalize_alignment_skill_id(reference_skill_id)
        else 0,
        -index,
    )


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
    pipeline_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = yaml.safe_load((source_bundle_path / "manifest.yaml").read_text(encoding="utf-8")) or {}
    graph_path = source_bundle_path / manifest.get("graph", {}).get("path", "graph/graph.json")
    source_snapshot_present = any((source_bundle_path / "sources").glob("*"))
    book_overview_path = source_bundle_path / "BOOK_OVERVIEW.md"
    source_chunks_path = source_bundle_path / "ingestion" / "source-chunks-v0.1.json"
    bundle_id = str(manifest.get("bundle_id", ""))
    extraction_result_path = None
    intermediate_graph_path = None
    reports_root = run_root / "reports"
    verification_summary_path = reports_root / "verification-summary.json"
    ria_tv_stage_report_path = reports_root / "ria-tv-stage-report.json"
    pressure_report_path = reports_root / "pressure-tests.json"
    extractor_kinds: set[str] = set()
    verification_summary: dict[str, Any] = {}
    ria_tv_stage_report: dict[str, Any] = {}
    pressure_report: dict[str, Any] = {}
    if verification_summary_path.exists():
        try:
            verification_summary = json.loads(verification_summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            verification_summary = {}
    if ria_tv_stage_report_path.exists():
        try:
            ria_tv_stage_report = json.loads(ria_tv_stage_report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ria_tv_stage_report = {}
    if pressure_report_path.exists():
        try:
            pressure_report = json.loads(pressure_report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pressure_report = {}
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
    stage1 = ria_tv_stage_report.get("stage1_parallel_extractors", {})
    responsibilities = (
        stage1.get("extractor_responsibilities", {})
        if isinstance(stage1, dict) and isinstance(stage1.get("extractor_responsibilities"), dict)
        else {}
    )
    for extractor_kind in responsibilities:
        if isinstance(extractor_kind, str) and extractor_kind:
            extractor_kinds.add(_normalize_extractor_kind(extractor_kind))
    ria_tv_stage_status = _summarize_ria_tv_stage_status(ria_tv_stage_report)
    triple_verification_summary = _summarize_triple_verification(verification_summary)
    pipeline_provenance = pipeline_provenance or {}
    raw_book_no_seed_cold_start = bool(
        pipeline_provenance.get("raw_book_no_seed_cold_start")
    )
    return {
        "raw_book_no_seed_cold_start": raw_book_no_seed_cold_start,
        "pipeline_mode": pipeline_provenance.get("pipeline_mode", "unknown"),
        "source_bundle_skill_count": int(
            pipeline_provenance.get("source_bundle_skill_count", 0) or 0
        ),
        "raw_source_present": source_snapshot_present,
        "book_overview_present": book_overview_path.exists(),
        "source_chunks_present": source_chunks_path.exists(),
        "extraction_result_present": extraction_result_path.exists() if extraction_result_path else False,
        "graph_present": graph_path.exists() or (intermediate_graph_path.exists() if intermediate_graph_path else False),
        "verification_summary_present": verification_summary_path.exists(),
        "extractor_kinds": sorted(extractor_kinds),
        "ria_tv_stage_report_present": ria_tv_stage_report_path.exists(),
        "ria_tv_stage_status": ria_tv_stage_status,
        "triple_verification_summary": triple_verification_summary,
        "pressure_test_summary": pressure_report.get("summary", {}) if isinstance(pressure_report, dict) else {},
    }


def _summarize_ria_tv_stage_status(report: dict[str, Any]) -> dict[str, bool]:
    stage_keys = [
        "stage0_book_overview",
        "stage1_parallel_extractors",
        "stage1_5_triple_verification",
        "stage2_skill_distillation",
        "stage3_linking",
        "stage4_pressure_test",
    ]
    status: dict[str, bool] = {}
    for key in stage_keys:
        value = report.get(key, {}) if isinstance(report, dict) else {}
        status[key] = bool(value.get("present")) if isinstance(value, dict) else bool(value)
    return status


def _summarize_triple_verification(verification_summary: dict[str, Any]) -> dict[str, float]:
    values: dict[str, list[float]] = {
        "cross_evidence_ratio": [],
        "predictive_action_ratio": [],
        "uniqueness_ratio": [],
    }
    accepted = verification_summary.get("accepted", []) if isinstance(verification_summary, dict) else []
    if not isinstance(accepted, list):
        return {}
    for item in accepted:
        if not isinstance(item, dict):
            continue
        verification = item.get("verification", {})
        if not isinstance(verification, dict):
            continue
        triple = verification.get("triple_verification", {})
        if not isinstance(triple, dict):
            continue
        for key in values:
            values[key].append(_bounded_ratio(triple.get(key)))
    return {
        key: round(_average(items), 4)
        for key, items in values.items()
        if items
    }


def _workflow_verification_ready_ratio(
    *,
    verification_summary: dict[str, Any],
    workflow_candidate_count: int,
) -> float:
    if workflow_candidate_count <= 0:
        return 1.0
    accepted = verification_summary.get("accepted", [])
    if not isinstance(accepted, list) or not accepted:
        return 0.0
    workflow_total = 0
    workflow_ready = 0
    for item in accepted:
        if not isinstance(item, dict):
            continue
        if item.get("disposition") != "workflow_script_candidate":
            continue
        workflow_total += 1
        verification = item.get("verification", {})
        if isinstance(verification, dict) and verification.get("workflow_ready"):
            workflow_ready += 1
    denominator = workflow_total if workflow_total > 0 else workflow_candidate_count
    return round(_safe_ratio(workflow_ready, denominator), 4)


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
    same_scenario_usage = report.get("same_scenario_usage", {})
    scorecard = report["scorecard"]
    generated_run = report.get("generated_run") or {}
    same_scenario_summary = same_scenario_usage.get("summary", {})
    top_failure_modes = ", ".join(
        f"{item.get('name')} ({item.get('count')})"
        for item in same_scenario_summary.get("top_failure_modes", [])
        if isinstance(item, dict) and item.get("name")
    ) or "none"
    repair_targets = ", ".join(
        f"{item.get('name')} ({item.get('count')})"
        for item in same_scenario_summary.get("dominant_repair_targets", [])
        if isinstance(item, dict) and item.get("name")
    ) or "none"
    repair_owners = ", ".join(
        f"{item.get('name')} ({item.get('count')})"
        for item in same_scenario_summary.get("dominant_repair_owners", [])
        if isinstance(item, dict) and item.get("name")
    ) or "none"
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
            f"- Unmatched KiU skills: `{concept_alignment['summary']['unmatched_kiu_skill_count']}`",
            f"- Unmatched reference skills: `{concept_alignment['summary']['unmatched_reference_skill_count']}`",
            "",
            "## Same-Scenario Usage",
            "",
            f"- Matched pairs: `{same_scenario_usage.get('summary', {}).get('matched_pair_count')}`",
            f"- Scenario count: `{same_scenario_usage.get('summary', {}).get('scenario_count')}`",
            f"- KiU usage score: `{same_scenario_usage.get('summary', {}).get('kiu_average_usage_score_100')}`",
            f"- Reference usage score: `{same_scenario_usage.get('summary', {}).get('reference_average_usage_score_100')}`",
            f"- Average delta: `{same_scenario_usage.get('summary', {}).get('average_usage_score_delta_100')}`",
            f"- KiU weighted pass rate: `{same_scenario_usage.get('summary', {}).get('kiu_weighted_pass_rate')}`",
            f"- Reference weighted pass rate: `{same_scenario_usage.get('summary', {}).get('reference_weighted_pass_rate')}`",
            f"- Weighted pass-rate delta: `{same_scenario_usage.get('summary', {}).get('weighted_pass_rate_delta')}`",
            f"- Usage winner: `{same_scenario_usage.get('summary', {}).get('usage_winner')}`",
            f"- Top failure modes: `{top_failure_modes}`",
            f"- Repair targets: `{repair_targets}`",
            f"- Upstream owners: `{repair_owners}`",
            "",
            "## Scorecard",
            "",
            f"- KiU foundation retained: `{scorecard['kiu_foundation_retained_100']}`",
            f"- Graphify core absorbed: `{scorecard['graphify_core_absorbed_100']}`",
            f"- cangjie core absorbed: `{scorecard['cangjie_core_absorbed_100']}`",
            f"- cangjie methodology internal: `{scorecard.get('cangjie_methodology_internal_100')}`",
            f"- cangjie external blind preference: `{scorecard.get('cangjie_methodology_external_blind_100')}`",
            f"- cangjie methodology closure: `{scorecard.get('cangjie_methodology_closure_100')}`",
            f"- cangjie methodology quality (deprecated closure alias): `{scorecard.get('cangjie_methodology_quality_100')}`",
            f"- cangjie methodology gate ready: `{scorecard.get('cangjie_methodology_gate', {}).get('ready')}`",
            f"- cangjie methodology claim: `{scorecard.get('cangjie_methodology_gate', {}).get('claim')}`",
            f"- cangjie methodology gate reasons: `{', '.join(scorecard.get('cangjie_methodology_gate', {}).get('reasons', [])) or 'none'}`",
            f"- final artifact effect ready: `{scorecard.get('final_artifact_effect', {}).get('ready')}`",
            f"- final artifact effect claim: `{scorecard.get('final_artifact_effect', {}).get('claim')}`",
            f"- final artifact Layer 1 usage effect: `{scorecard.get('final_artifact_effect', {}).get('layer1_immediate_usage_effect_100')}`",
            f"- final artifact Layer 2 knowledge depth effect: `{scorecard.get('final_artifact_effect', {}).get('layer2_knowledge_depth_effect_100')}`",
            f"- final artifact Layer 3 external blind preference effect: `{scorecard.get('final_artifact_effect', {}).get('layer3_external_blind_preference_effect_100')}`",
            f"- final artifact effect reasons: `{', '.join(scorecard.get('final_artifact_effect', {}).get('reasons', [])) or 'none'}`",
            f"- Book-to-skill cold start proven: `{scorecard.get('book_to_skill_cold_start_proven')}`",
            f"- Graph-to-skill distillation: `{scorecard.get('graph_to_skill_distillation_100')}`",
            f"- v0.6.1 distillation gate ready: `{scorecard.get('v061_distillation_gate', {}).get('ready')}`",
            "",
            "## Cangjie Core Baseline Matrix",
            "",
            *_render_cangjie_matrix_lines(scorecard.get("cangjie_core_baseline_matrix", {})),
            "",
        ]
    )


def _render_cangjie_matrix_lines(matrix: dict[str, Any]) -> list[str]:
    rows = matrix.get("rows", []) if isinstance(matrix, dict) else []
    if not rows:
        return ["- Matrix: `not available`"]
    lines = [
        f"- Ready: `{matrix.get('summary', {}).get('ready')}`",
        f"- Missing capabilities: `{', '.join(matrix.get('summary', {}).get('missing_capabilities', [])) or 'none'}`",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('capability_id')}: `{row.get('status')}` "
            f"score=`{row.get('score_ratio')}` reason=`{row.get('missing_reason') or 'none'}`"
        )
    return lines
