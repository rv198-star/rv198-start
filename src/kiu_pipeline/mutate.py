from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from typing import Any

from .draft import _build_usage_summary, replace_markdown_section, synchronize_candidate_skill_markdown
from .load import parse_sections


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
    mutated["skill_markdown"] = synchronize_candidate_skill_markdown(
        mutated["skill_markdown"],
        eval_summary=mutated["eval_summary"],
        revisions=mutated["revisions"],
        skill_revision=current_revision,
        status=mutated["eval_summary"].get("status", "under_evaluation"),
        scenario_families=mutated.get("scenario_families", {}),
    )
    return mutated


def _append_trace_reference(skill_markdown: str, trace_ref: str) -> str:
    sections = parse_sections(skill_markdown)
    usage_summary = sections.get("Usage Summary", "")
    if trace_ref in usage_summary:
        return skill_markdown

    if "Representative cases:" in usage_summary:
        rendered_usage = usage_summary.rstrip() + f"\n- `{trace_ref}`"
        return replace_markdown_section(skill_markdown, "Usage Summary", rendered_usage)

    trace_refs = re.findall(r"traces/[\w./-]+\.yaml", usage_summary)
    trace_refs.append(trace_ref)
    usage_notes = _extract_usage_notes(usage_summary)
    rendered_usage = _build_usage_summary(trace_refs, usage_notes=usage_notes)
    return replace_markdown_section(skill_markdown, "Usage Summary", rendered_usage)


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

def _extract_usage_notes(usage_summary: str) -> list[str]:
    notes: list[str] = []
    for line in usage_summary.splitlines():
        stripped = line.strip()
        if stripped == "Representative cases:":
            break
        if stripped.startswith("- ") and "traces/" not in stripped:
            notes.append(stripped[2:].strip())
    return notes
