from __future__ import annotations

import re
from typing import Any

from .load import extract_yaml_section, parse_sections
from .scoring import DEFAULT_WEIGHTS, quality_from_eval_summary


DEFAULT_RELEASE_QUALITY_WEIGHTS = {
    "artifact_quality": 0.65,
    "loop_quality": 0.35,
}

DEFAULT_RELEASE_THRESHOLDS = {
    "artifact_quality": 0.74,
    "production_quality": 0.78,
}

GENERIC_PLACEHOLDER_STRINGS = (
    "This candidate was seeded from the graph snapshot",
    "The current draft is anchored to the released graph snapshot",
    "Representative cases are still pending curation.",
    "Auto-seeded candidate still needs human review before publication.",
)

GENERIC_BOUNDARY_SYMBOLS = {
    "evidence_is_too_sparse_for_candidate_review",
    "candidate_has_not_been_reviewed_by_human",
    "scenario_missing_decision_context",
    "disconfirming_evidence_present",
}

GENERIC_TRIGGER_SUFFIXES = (
    "_needed",
    "_decision_window",
    "_out_of_scope",
)

GENERIC_BOUNDARY_SUFFIXES = (
    "_scenario_missing",
    "_evidence_conflict",
)


def assess_candidate_artifact(
    *,
    candidate: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    skill_markdown = candidate.get("skill_markdown", "")
    sections = parse_sections(skill_markdown)
    contract = extract_yaml_section(sections.get("Contract", ""))
    rationale_text = sections.get("Rationale", "")
    evidence_text = sections.get("Evidence Summary", "")
    usage_text = sections.get("Usage Summary", "")
    anchors = candidate.get("anchors", {})
    eval_summary = candidate.get("eval_summary", {})
    revisions = candidate.get("revisions", {})
    skill_id = (
        candidate.get("candidate", {}).get("candidate_id")
        or eval_summary.get("skill_id")
        or "<unknown-skill>"
    )

    blockers: list[str] = []
    notes: list[str] = []

    contract_assessment = _score_contract(contract)
    blockers.extend(contract_assessment["blockers"])

    rationale_assessment = _score_rationale(rationale_text, profile=profile)
    blockers.extend(rationale_assessment["blockers"])

    evidence_assessment = _score_evidence(
        evidence_text,
        anchors=anchors,
        profile=profile,
    )
    blockers.extend(evidence_assessment["blockers"])

    usage_assessment = _score_usage(usage_text)
    blockers.extend(usage_assessment["blockers"])

    eval_assessment = _score_eval(eval_summary)
    blockers.extend(eval_assessment["blockers"])

    revision_assessment = _score_revisions(revisions)
    blockers.extend(revision_assessment["blockers"])

    if any(token in skill_markdown for token in GENERIC_PLACEHOLDER_STRINGS):
        blockers.append("generic_placeholder_text")
    if "candidate_seed::" in skill_markdown:
        blockers.append("placeholder_contract")
    if "pending_review" in skill_markdown:
        blockers.append("placeholder_judgment")

    artifact_quality = round(
        (
            0.22 * contract_assessment["score"]
            + 0.22 * rationale_assessment["score"]
            + 0.18 * evidence_assessment["score"]
            + 0.14 * usage_assessment["score"]
            + 0.16 * eval_assessment["score"]
            + 0.08 * revision_assessment["score"]
        ),
        4,
    )
    quality_grade = quality_grade_from_score(artifact_quality)

    if artifact_quality < DEFAULT_RELEASE_THRESHOLDS["artifact_quality"]:
        notes.append("artifact_quality_below_good_bar")

    return {
        "candidate_id": skill_id,
        "artifact_quality": artifact_quality,
        "quality_grade": quality_grade,
        "component_scores": {
            "contract_specificity": contract_assessment["score"],
            "rationale_depth": rationale_assessment["score"],
            "evidence_grounding": evidence_assessment["score"],
            "usage_readiness": usage_assessment["score"],
            "eval_readiness": eval_assessment["score"],
            "revision_traceability": revision_assessment["score"],
        },
        "signals": {
            "trigger_patterns": contract_assessment["signals"]["trigger_patterns"],
            "intake_fields": contract_assessment["signals"]["intake_fields"],
            "rationale_chars": rationale_assessment["signals"]["rationale_chars"],
            "rationale_anchor_refs": rationale_assessment["signals"]["rationale_anchor_refs"],
            "evidence_anchor_refs": evidence_assessment["signals"]["evidence_anchor_refs"],
            "graph_anchor_sets": evidence_assessment["signals"]["graph_anchor_sets"],
            "source_anchor_sets": evidence_assessment["signals"]["source_anchor_sets"],
            "trace_refs": usage_assessment["signals"]["trace_refs"],
            "usage_notes": usage_assessment["signals"]["usage_notes"],
            "eval_cases_total": eval_assessment["signals"]["eval_cases_total"],
            "passed_kiu_tests": eval_assessment["signals"]["passed_kiu_tests"],
            "revision_history_entries": revision_assessment["signals"]["revision_history_entries"],
        },
        "blockers": sorted(set(blockers)),
        "notes": sorted(set(notes)),
    }


def assess_candidate_output(
    *,
    candidate: dict[str, Any],
    profile: dict[str, Any],
    loop_scorecard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = assess_candidate_artifact(candidate=candidate, profile=profile)
    refiner_cfg = profile.get("refinement_scheduler", {})
    weights = refiner_cfg.get("weights") or DEFAULT_WEIGHTS
    release_cfg = refiner_cfg.get("release_quality", {})
    release_weights = _merge_float_dict(
        DEFAULT_RELEASE_QUALITY_WEIGHTS,
        release_cfg.get("weights", {}),
    )
    thresholds = _merge_float_dict(
        DEFAULT_RELEASE_THRESHOLDS,
        release_cfg.get("thresholds", {}),
    )
    targets = refiner_cfg.get("targets", {})
    if "artifact_quality" in targets:
        thresholds["artifact_quality"] = float(targets["artifact_quality"])
    if "production_quality" in targets:
        thresholds["production_quality"] = float(targets["production_quality"])

    if loop_scorecard is None:
        candidate_doc = candidate.get("candidate", {})
        if "overall_quality" in candidate_doc:
            loop_scorecard = {
                "overall_quality": candidate_doc.get("overall_quality", 0.0),
                "boundary_quality": candidate_doc.get("boundary_quality", 0.0),
                "eval_aggregate": candidate_doc.get("eval_aggregate", 0.0),
                "cross_subset_stability": candidate_doc.get("cross_subset_stability", 0.0),
            }
        else:
            loop_scorecard = quality_from_eval_summary(
                candidate.get("eval_summary", {}),
                weights=weights,
            )

    loop_overall_quality = float(loop_scorecard.get("overall_quality", 0.0))
    production_quality = round(
        release_weights["artifact_quality"] * artifact["artifact_quality"]
        + release_weights["loop_quality"] * loop_overall_quality,
        4,
    )
    quality_grade = quality_grade_from_score(production_quality)
    release_ready = (
        artifact["artifact_quality"] >= thresholds["artifact_quality"]
        and production_quality >= thresholds["production_quality"]
        and quality_grade in {"good", "excellent"}
    )

    return {
        "candidate_id": artifact["candidate_id"],
        "artifact_quality": artifact["artifact_quality"],
        "artifact_grade": artifact["quality_grade"],
        "production_quality": production_quality,
        "quality_grade": quality_grade,
        "release_ready": release_ready,
        "loop_overall_quality": round(loop_overall_quality, 4),
        "component_scores": artifact["component_scores"],
        "signals": artifact["signals"],
        "blockers": artifact["blockers"],
        "notes": artifact["notes"],
        "thresholds": thresholds,
    }


def assess_run_quality(
    *,
    candidates: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    skill_reports = [
        assess_candidate_output(candidate=candidate, profile=profile)
        for candidate in candidates
    ]
    production_scores = [item["production_quality"] for item in skill_reports]
    artifact_scores = [item["artifact_quality"] for item in skill_reports]
    release_ready = bool(skill_reports) and all(item["release_ready"] for item in skill_reports)

    grade_counts: dict[str, int] = {}
    for item in skill_reports:
        grade_counts[item["quality_grade"]] = grade_counts.get(item["quality_grade"], 0) + 1

    minimum_production_quality = min(production_scores) if production_scores else 0.0
    minimum_artifact_quality = min(artifact_scores) if artifact_scores else 0.0
    bundle_quality_grade = quality_grade_from_score(minimum_production_quality)

    thresholds = skill_reports[0]["thresholds"] if skill_reports else dict(DEFAULT_RELEASE_THRESHOLDS)
    return {
        "candidate_count": len(skill_reports),
        "artifact_release_ready": release_ready,
        "behavior_release_ready": None,
        "release_ready": release_ready,
        "release_gate_reasons": [],
        "bundle_quality_grade": bundle_quality_grade,
        "average_artifact_quality": round(
            sum(artifact_scores) / len(artifact_scores),
            4,
        ) if artifact_scores else 0.0,
        "average_production_quality": round(
            sum(production_scores) / len(production_scores),
            4,
        ) if production_scores else 0.0,
        "minimum_artifact_quality": round(minimum_artifact_quality, 4),
        "minimum_production_quality": round(minimum_production_quality, 4),
        "grade_counts": grade_counts,
        "thresholds": thresholds,
        "skills": skill_reports,
    }


def quality_grade_from_score(score: float) -> str:
    if score >= 0.9:
        return "excellent"
    if score >= 0.78:
        return "good"
    if score >= 0.62:
        return "fair"
    return "poor"


def _score_contract(contract: dict[str, Any]) -> dict[str, Any]:
    trigger = contract.get("trigger", {})
    intake = contract.get("intake", {})
    boundary = contract.get("boundary", {})
    raw_patterns = [
        item for item in trigger.get("patterns", [])
        if isinstance(item, str)
    ]
    patterns = [item for item in raw_patterns if "candidate_seed::" not in item]
    exclusions = [item for item in trigger.get("exclusions", []) if isinstance(item, str)]
    intake_fields = [
        item for item in intake.get("required", [])
        if isinstance(item, dict)
    ]
    contract_text = str(contract)
    fails_when = [item for item in boundary.get("fails_when", []) if isinstance(item, str)]
    do_not_fire_when = [
        item for item in boundary.get("do_not_fire_when", [])
        if isinstance(item, str)
    ]

    placeholder_contract = len(patterns) != len(raw_patterns) or "pending_review" in contract_text
    generic_trigger = bool(patterns or exclusions) and all(
        _looks_generic_trigger_symbol(item)
        for item in [*patterns, *exclusions]
        if isinstance(item, str)
    )
    boundary_symbols = set(fails_when + do_not_fire_when)
    generic_boundary = bool(boundary_symbols) and all(
        item in GENERIC_BOUNDARY_SYMBOLS or _looks_generic_boundary_symbol(item)
        for item in boundary_symbols
    )

    verdict_score = 0.0
    if "pending_review" not in contract_text and "enum[" in contract_text:
        verdict_score = 1.0
    elif "schema" in contract_text:
        verdict_score = 0.5

    boundary_score = 0.0
    if fails_when:
        boundary_score += 0.5
    if do_not_fire_when:
        boundary_score += 0.5
    if generic_boundary:
        boundary_score *= 0.45

    score = round(
        (
            min(len(patterns) / 2.0, 1.0)
            + (1.0 if exclusions else 0.0)
            + min(len(intake_fields) / 3.0, 1.0)
            + verdict_score
            + boundary_score
        ) / 5.0,
        4,
    )
    if placeholder_contract:
        score = round(score * 0.35, 4)
    if generic_trigger:
        score = round(score * 0.55, 4)
    if generic_boundary:
        score = round(score * 0.75, 4)

    blockers: list[str] = []
    if placeholder_contract:
        blockers.append("placeholder_contract")
    if generic_trigger:
        blockers.append("generic_trigger_contract")
    if len(patterns) == 0:
        blockers.append("missing_trigger_patterns")
    if len(intake_fields) < 2:
        blockers.append("shallow_intake_contract")
    if verdict_score == 0.0:
        blockers.append("weak_judgment_schema")
    if boundary_score < 0.6:
        blockers.append("weak_boundary_contract")

    return {
        "score": score,
        "signals": {
            "trigger_patterns": len(patterns),
            "intake_fields": len(intake_fields),
        },
        "blockers": blockers,
    }


def _looks_generic_trigger_symbol(symbol: str) -> bool:
    return any(symbol.endswith(suffix) for suffix in GENERIC_TRIGGER_SUFFIXES)


def _looks_generic_boundary_symbol(symbol: str) -> bool:
    return any(symbol.endswith(suffix) for suffix in GENERIC_BOUNDARY_SUFFIXES)


def _score_rationale(
    rationale_text: str,
    *,
    profile: dict[str, Any],
) -> dict[str, Any]:
    rationale_cfg = profile.get("content_density", {}).get("rationale", {})
    min_chars = int(rationale_cfg.get("warning_min_chars", 180))
    min_anchor_refs = int(rationale_cfg.get("min_anchor_refs", 1))
    rationale_chars = _dense_char_count(rationale_text)
    rationale_anchor_refs = _count_anchor_refs(rationale_text)
    target_chars = max(min_chars + 80, int(min_chars * 1.25))
    target_anchor_refs = max(min_anchor_refs + 1, 2)
    char_score = min(rationale_chars / target_chars, 1.0) if target_chars > 0 else 0.0
    anchor_score = min(rationale_anchor_refs / target_anchor_refs, 1.0)
    score = round(0.7 * char_score + 0.3 * anchor_score, 4)

    blockers: list[str] = []
    if rationale_chars < min_chars:
        blockers.append("thin_rationale")
    if rationale_anchor_refs < min_anchor_refs:
        blockers.append("unanchored_rationale")
    if "This candidate was seeded from the graph snapshot" in rationale_text:
        blockers.append("placeholder_rationale")
        score = round(score * 0.35, 4)

    return {
        "score": score,
        "signals": {
            "rationale_chars": rationale_chars,
            "rationale_anchor_refs": rationale_anchor_refs,
        },
        "blockers": blockers,
    }


def _score_evidence(
    evidence_text: str,
    *,
    anchors: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    evidence_cfg = profile.get("content_density", {}).get("evidence_summary", {})
    min_anchor_refs = int(evidence_cfg.get("min_anchor_refs", 1))
    evidence_anchor_refs = _count_anchor_refs(evidence_text)
    target_anchor_refs = max(min_anchor_refs + 1, 2)
    graph_anchor_sets = len(anchors.get("graph_anchor_sets", []))
    source_anchor_sets = len(anchors.get("source_anchor_sets", []))
    anchor_ref_score = min(evidence_anchor_refs / target_anchor_refs, 1.0)
    source_score = min(source_anchor_sets / 2.0, 1.0)
    graph_score = 1.0 if graph_anchor_sets > 0 else 0.0
    grounding_bonus = 0.0 if "awaits" in evidence_text and "under_evaluation" in evidence_text else 1.0
    score = round(
        0.3 * anchor_ref_score + 0.35 * source_score + 0.25 * graph_score + 0.1 * grounding_bonus,
        4,
    )

    blockers: list[str] = []
    if evidence_anchor_refs < min_anchor_refs:
        blockers.append("evidence_missing_anchor_refs")
    if source_anchor_sets == 0:
        blockers.append("missing_source_anchors")
    if graph_anchor_sets == 0:
        blockers.append("missing_graph_anchors")

    return {
        "score": score,
        "signals": {
            "evidence_anchor_refs": evidence_anchor_refs,
            "graph_anchor_sets": graph_anchor_sets,
            "source_anchor_sets": source_anchor_sets,
        },
        "blockers": blockers,
    }


def _score_usage(usage_text: str) -> dict[str, Any]:
    trace_refs = re.findall(r"traces/[\w./-]+\.yaml", usage_text)
    usage_notes = [
        line.strip()
        for line in usage_text.splitlines()
        if line.strip().startswith("- ") and "traces/" not in line
    ]
    placeholder_usage = "Representative cases are still pending curation." in usage_text
    score = round(
        0.65 * min(len(trace_refs) / 2.0, 1.0)
        + 0.2 * (1.0 if usage_notes else 0.0)
        + 0.15 * (0.0 if placeholder_usage else 1.0),
        4,
    )

    blockers: list[str] = []
    if len(trace_refs) == 0:
        blockers.append("missing_trace_examples")
    if placeholder_usage:
        blockers.append("usage_still_placeholder")

    return {
        "score": score,
        "signals": {
            "trace_refs": len(trace_refs),
            "usage_notes": len(usage_notes),
        },
        "blockers": blockers,
    }


def _score_eval(eval_summary: dict[str, Any]) -> dict[str, Any]:
    kiu_test = eval_summary.get("kiu_test", {})
    subsets = eval_summary.get("subsets", {})
    total_cases = 0
    subset_scores: list[float] = []
    for subset_name in (
        "real_decisions",
        "synthetic_adversarial",
        "out_of_distribution",
    ):
        subset = subsets.get(subset_name, {})
        total = int(subset.get("total", 0) or 0)
        total_cases += total
        status = subset.get("status", "pending")
        coverage_score = 1.0 if total > 0 else 0.0
        status_score = {
            "pass": 1.0,
            "under_evaluation": 0.7,
            "pending": 0.35,
        }.get(status, 0.0)
        subset_scores.append(0.6 * coverage_score + 0.4 * status_score)

    gate_scores = [
        1.0 if kiu_test.get(gate) == "pass" else 0.35 if kiu_test.get(gate) == "pending" else 0.0
        for gate in ("trigger_test", "fire_test", "boundary_test")
    ]
    passed_kiu_tests = sum(
        1 for gate in ("trigger_test", "fire_test", "boundary_test")
        if kiu_test.get(gate) == "pass"
    )
    key_failure_modes = eval_summary.get("key_failure_modes", [])
    score = round(
        0.55 * (sum(subset_scores) / len(subset_scores) if subset_scores else 0.0)
        + 0.25 * (sum(gate_scores) / len(gate_scores) if gate_scores else 0.0)
        + 0.20 * (1.0 if key_failure_modes else 0.0),
        4,
    )

    blockers: list[str] = []
    if total_cases == 0:
        blockers.append("eval_cases_missing")
    if not key_failure_modes:
        blockers.append("missing_failure_modes")

    return {
        "score": score,
        "signals": {
            "eval_cases_total": total_cases,
            "passed_kiu_tests": passed_kiu_tests,
        },
        "blockers": blockers,
    }


def _score_revisions(revisions: dict[str, Any]) -> dict[str, Any]:
    history = revisions.get("history", [])
    open_gaps = revisions.get("open_gaps", [])
    score = round(
        0.4 * (1.0 if history else 0.0)
        + 0.3 * min(len(history) / 2.0, 1.0)
        + 0.3 * (1.0 if open_gaps else 0.0),
        4,
    )

    blockers: list[str] = []
    if not history:
        blockers.append("missing_revision_history")

    return {
        "score": score,
        "signals": {
            "revision_history_entries": len(history),
        },
        "blockers": blockers,
    }


def _merge_float_dict(base: dict[str, float], override: dict[str, Any]) -> dict[str, float]:
    merged = dict(base)
    for key, value in override.items():
        try:
            merged[key] = float(value)
        except (TypeError, ValueError):
            continue
    return merged


def _dense_char_count(text: str) -> int:
    stripped = re.sub(r"\[\^(?:anchor|trace):[^\]]+\]", "", text)
    stripped = re.sub(r"[`*_>#\-\[\]\(\)\s]+", "", stripped)
    return len(stripped)


def _count_anchor_refs(text: str) -> int:
    return len(re.findall(r"\[\^(?:anchor|trace):[^\]]+\]", text))
