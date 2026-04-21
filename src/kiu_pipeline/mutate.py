from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from typing import Any


def mutate_candidate(
    *,
    candidate: dict[str, Any],
    round_index: int,
    mutation_plan: dict[str, Any],
) -> dict[str, Any]:
    mutated = deepcopy(candidate)
    candidate_doc = mutated["candidate"]

    candidate_doc["current_round"] = round_index
    candidate_doc["boundary_quality"] = round(
        min(0.99, candidate_doc.get("boundary_quality", 0.70) + mutation_plan.get("boundary_strength_delta", 0.0)),
        4,
    )
    candidate_doc["eval_aggregate"] = round(
        min(0.99, candidate_doc.get("eval_aggregate", 0.70) + mutation_plan.get("eval_gain_delta", 0.0)),
        4,
    )
    candidate_doc["cross_subset_stability"] = round(
        min(0.99, candidate_doc.get("cross_subset_stability", 0.70) + mutation_plan.get("stability_delta", 0.0)),
        4,
    )

    trace_ref = mutation_plan.get("append_trace_ref")
    if trace_ref:
        mutated["skill_markdown"] = _append_trace_reference(
            mutated["skill_markdown"],
            trace_ref,
        )

    mutated["eval_summary"] = _update_eval_summary(
        mutated["eval_summary"],
        candidate_doc,
    )
    mutated["revisions"] = _update_revisions(
        mutated["revisions"],
        round_index,
        mutation_plan.get("revision_note", "Autonomous refinement updated candidate quality."),
        candidate_doc.get("source_graph_hash", ""),
    )
    current_revision = mutated["revisions"]["current_revision"]
    mutated["eval_summary"]["skill_revision"] = current_revision
    mutated["skill_markdown"] = _update_skill_markdown_metadata(
        mutated["skill_markdown"],
        skill_revision=current_revision,
    )
    return mutated


def _append_trace_reference(skill_markdown: str, trace_ref: str) -> str:
    needle = "## Evaluation Summary"
    bullet = f"- `{trace_ref}`\n\n"
    if trace_ref in skill_markdown:
        return skill_markdown
    if needle in skill_markdown and "Representative cases:" in skill_markdown:
        return skill_markdown.replace(needle, bullet + needle, 1)
    return skill_markdown.rstrip() + "\n\n" + bullet


def _update_eval_summary(
    eval_summary: dict[str, Any],
    candidate_doc: dict[str, Any],
) -> dict[str, Any]:
    updated = deepcopy(eval_summary)
    updated["status"] = "under_evaluation"
    boundary_quality = float(candidate_doc.get("boundary_quality", 0.0))
    eval_aggregate = float(candidate_doc.get("eval_aggregate", 0.0))

    updated.setdefault("kiu_test", {})
    updated["kiu_test"]["trigger_test"] = "pass" if eval_aggregate >= 0.80 else "pending"
    updated["kiu_test"]["fire_test"] = "pass" if eval_aggregate >= 0.82 else "pending"
    updated["kiu_test"]["boundary_test"] = "pass" if boundary_quality >= 0.85 else "pending"

    subsets = updated.setdefault("subsets", {})
    for subset_name, offset in (
        ("real_decisions", 0.00),
        ("synthetic_adversarial", -0.03),
        ("out_of_distribution", -0.05),
    ):
        subset = subsets.setdefault(subset_name, {})
        total = int(subset.get("total", 0) or 0)
        target_ratio = max(0.0, min(1.0, eval_aggregate + offset))
        passed = int(round(target_ratio * total)) if total > 0 else 0
        subset["passed"] = min(total, passed)
        if total > 0 and passed == total:
            subset["status"] = "pass"
        else:
            subset["status"] = "under_evaluation"
    return updated


def _update_revisions(
    revisions: dict[str, Any],
    round_index: int,
    note: str,
    graph_hash: str,
) -> dict[str, Any]:
    updated = deepcopy(revisions)
    current_revision = int(updated.get("current_revision", 1) or 1) + 1
    updated["current_revision"] = current_revision
    updated.setdefault("history", []).append(
        {
            "revision": current_revision,
            "date": date.today().isoformat(),
            "summary": note,
            "graph_hash": graph_hash,
            "effective_status": "under_evaluation",
            "evidence_changes": [note],
        }
    )
    return updated


def _update_skill_markdown_metadata(
    skill_markdown: str,
    *,
    skill_revision: int,
) -> str:
    updated = skill_markdown
    updated = re.sub(
        r"status:\s+\w+",
        "status: under_evaluation",
        updated,
        count=1,
    )
    updated = re.sub(
        r"skill_revision:\s+\d+",
        f"skill_revision: {skill_revision}",
        updated,
        count=1,
    )
    return updated
