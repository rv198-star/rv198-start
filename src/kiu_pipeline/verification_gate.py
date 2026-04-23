from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import CandidateSeed, NormalizedGraph, SourceBundle


VERIFICATION_GATE_SCHEMA_VERSION = "kiu.verification-gate/v0.1"


def assess_candidate_seed(
    *,
    seed: CandidateSeed,
    bundle: SourceBundle,
    graph: NormalizedGraph,
) -> dict[str, Any]:
    del graph

    bundle_id = str(bundle.manifest.get("bundle_id", "") or "")
    routing = (
        seed.metadata.get("routing_evidence", {})
        if isinstance(seed.metadata.get("routing_evidence"), dict)
        else {}
    )
    extracted_evidence_support_count = _nonnegative_int(
        routing.get("extracted_evidence_support_count")
    )
    evidence_support_count = _nonnegative_int(routing.get("evidence_support_count"))
    context_cues = _nonnegative_int(routing.get("context_cues"))
    workflow_cues = _nonnegative_int(routing.get("workflow_cues"))
    manual_override = routing.get("inference_mode") == "manual_override"
    fixture_seed_prefill = (
        bundle_id.endswith("-source-v0.1")
        and isinstance(seed.seed_content, dict)
        and bool(
            seed.seed_content.get("trace_refs")
            or seed.seed_content.get("eval_summary")
        )
    )

    if extracted_evidence_support_count <= 0 and seed.source_skill and seed.source_skill.trace_refs:
        extracted_evidence_support_count = max(
            extracted_evidence_support_count,
            min(len(seed.source_skill.trace_refs), 2),
        )
    if extracted_evidence_support_count <= 0 and fixture_seed_prefill:
        extracted_evidence_support_count = 1
    if extracted_evidence_support_count <= 0 and manual_override and seed.supporting_edge_ids:
        extracted_evidence_support_count = 1
    if evidence_support_count <= 0 and extracted_evidence_support_count > 0:
        evidence_support_count = extracted_evidence_support_count
    if manual_override and extracted_evidence_support_count > 0:
        workflow_cues = max(workflow_cues, 1)
        if seed.community_ids:
            context_cues = max(context_cues, 1)

    tri_state_support_ratio = _float_ratio(routing.get("tri_state_support_ratio"))
    matched_keywords = sorted(
        {
            keyword
            for keyword in routing.get("matched_keywords", [])
            if isinstance(keyword, str) and keyword
        }
    )
    evidence_chunk_ids = sorted(
        {
            chunk_id
            for chunk_id in routing.get("evidence_chunk_ids", [])
            if isinstance(chunk_id, str) and chunk_id
        }
    )

    corroboration_score = _average(
        [
            min(extracted_evidence_support_count / 1.0, 1.0),
            min((len(seed.supporting_edge_ids) + len(seed.supporting_node_ids)) / 4.0, 1.0),
            1.0
            if seed.community_ids
            else (0.5 if seed.supporting_edge_ids or seed.supporting_node_ids else 0.0),
        ]
    )
    predictive_usefulness_score = _average(
        [
            min((context_cues + min(workflow_cues, 1)) / 2.0, 1.0),
            1.0
            if (
                extracted_evidence_support_count > 0
                or evidence_chunk_ids
                or seed.source_skill
                or fixture_seed_prefill
            )
            else 0.0,
            1.0
            if (
                matched_keywords
                or seed.gold_match_hint
                or seed.source_skill
                or manual_override
                or fixture_seed_prefill
            )
            else (0.5 if evidence_support_count > 0 else 0.0),
        ]
    )
    distinctiveness_score = _average(
        [
            _candidate_specificity(seed.candidate_id),
            min(max(len(matched_keywords), len(set(seed.supporting_node_ids))) / 2.0, 1.0),
            1.0
            if len(set(seed.supporting_node_ids)) >= 2
            else (0.5 if len(set(seed.supporting_node_ids)) == 1 else 0.0),
        ]
    )

    overall_score = _average(
        [
            corroboration_score,
            predictive_usefulness_score,
            distinctiveness_score,
        ]
    )

    reasons: list[str] = []
    if extracted_evidence_support_count <= 0:
        reasons.append("missing_extracted_evidence")
    if corroboration_score < 0.55:
        reasons.append("corroboration_too_thin")
    if predictive_usefulness_score < 0.45:
        reasons.append("predictive_usefulness_too_thin")
    if distinctiveness_score < 0.40:
        reasons.append("distinctiveness_too_thin")

    passed = (
        extracted_evidence_support_count > 0
        and corroboration_score >= 0.55
        and predictive_usefulness_score >= 0.45
        and distinctiveness_score >= 0.40
        and overall_score >= 0.55
    )
    workflow_corroboration_threshold = 0.65 if len(matched_keywords) >= 2 else 0.75
    workflow_distinctiveness_threshold = 0.50 if manual_override else 0.70
    workflow_ready = (
        passed
        and corroboration_score >= workflow_corroboration_threshold
        and predictive_usefulness_score >= 0.60
        and distinctiveness_score >= workflow_distinctiveness_threshold
        and tri_state_support_ratio <= 0.60
    )
    if passed and not workflow_ready:
        reasons.append("workflow_requires_stronger_verification")

    return {
        "schema_version": VERIFICATION_GATE_SCHEMA_VERSION,
        "candidate_id": seed.candidate_id,
        "passed": passed,
        "workflow_ready": workflow_ready,
        "corroboration_score": corroboration_score,
        "predictive_usefulness_score": predictive_usefulness_score,
        "distinctiveness_score": distinctiveness_score,
        "overall_score": overall_score,
        "reasons": reasons,
        "evidence": {
            "extracted_evidence_support_count": extracted_evidence_support_count,
            "evidence_support_count": evidence_support_count,
            "context_cues": context_cues,
            "workflow_cues": workflow_cues,
            "tri_state_support_ratio": tri_state_support_ratio,
            "matched_keywords": matched_keywords,
            "evidence_chunk_ids": evidence_chunk_ids,
            "supporting_node_count": len(seed.supporting_node_ids),
            "supporting_edge_count": len(seed.supporting_edge_ids),
            "community_count": len(seed.community_ids),
        },
    }


def summarize_seed_verification(
    *,
    accepted: list[CandidateSeed],
    rejected: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_docs = [
        {
            "candidate_id": seed.candidate_id,
            "candidate_kind": seed.candidate_kind,
            "disposition": seed.metadata.get("disposition"),
            "verification": seed.metadata.get("verification", {}),
        }
        for seed in accepted
    ]
    overall_scores = [
        float(doc["verification"].get("overall_score", 0.0) or 0.0)
        for doc in accepted_docs
        if isinstance(doc.get("verification"), dict)
    ]
    return {
        "schema_version": VERIFICATION_GATE_SCHEMA_VERSION,
        "accepted_candidate_count": len(accepted_docs),
        "rejected_candidate_count": len(rejected),
        "accepted": accepted_docs,
        "rejected": rejected,
        "average_overall_score": round(_average(overall_scores), 4),
    }


def write_seed_verification_reports(
    *,
    run_root: str | Path,
    summary: dict[str, Any],
) -> dict[str, str]:
    run_root = Path(run_root)
    reports_root = run_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    summary_path = reports_root / "verification-summary.json"
    rejection_log_path = reports_root / "rejection-log.yaml"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rejection_log_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": summary.get("schema_version", VERIFICATION_GATE_SCHEMA_VERSION),
                "rejected": summary.get("rejected", []),
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return {
        "summary_path": str(summary_path),
        "rejection_log_path": str(rejection_log_path),
    }


def _candidate_specificity(candidate_id: str) -> float:
    tokens = [token for token in str(candidate_id).split("-") if token]
    if len(tokens) >= 4:
        return 1.0
    if len(tokens) == 3:
        return 0.75
    if len(tokens) == 2:
        return 0.5
    return 0.25


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    return 0


def _float_ratio(value: Any) -> float:
    if isinstance(value, (int, float)):
        return min(max(float(value), 0.0), 1.0)
    return 0.0


def _average(values: list[float]) -> float:
    filtered = [float(value) for value in values if value is not None]
    if not filtered:
        return 0.0
    return round(sum(filtered) / len(filtered), 4)
