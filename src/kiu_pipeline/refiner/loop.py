from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..baseline import build_candidate_baseline
from ..models import SourceBundle
from ..mutate import mutate_candidate
from ..quality import assess_candidate_output
from ..reports import write_final_decision, write_round_report, write_scorecard
from ..scoring import (
    DEFAULT_WEIGHTS,
    decide_terminal_state,
    quality_from_eval_summary,
    score_candidate,
)
from .drafting import LLMBudgetTracker, apply_llm_drafting
from .providers import LLMProvider, create_provider_from_env


def refine_candidate(
    *,
    candidate: dict[str, Any],
    source_bundle: SourceBundle,
    run_root: str | Path,
    mutation_strategy: str = "default",
    llm_provider: LLMProvider | None = None,
    llm_budget_tokens: int = 100000,
    budget_tracker: LLMBudgetTracker | None = None,
) -> dict[str, Any]:
    config = source_bundle.profile.get("refinement_scheduler", {})
    weights = config.get("weights") or DEFAULT_WEIGHTS
    bonuses = config.get("bonuses", {})
    current = _initialize_candidate_metrics(candidate, weights=weights)
    nearest_skill_id = (
        current.get("nearest_skill_id")
        or current["candidate"].get("gold_match_hint")
        or current["candidate"]["candidate_id"]
    )
    baseline = build_candidate_baseline(
        source_bundle=source_bundle,
        nearest_skill_id=nearest_skill_id,
    )

    drafting_mode = current["candidate"].get("drafting_mode", "deterministic")
    provider = llm_provider
    token_budget = budget_tracker
    if drafting_mode == "llm-assisted":
        provider = provider or create_provider_from_env()
        token_budget = token_budget or LLMBudgetTracker(max_tokens=llm_budget_tokens)

    history: list[dict[str, Any]] = []
    for round_index in range(1, config.get("max_rounds", 5) + 1):
        mutation_plan = plan_round_mutation(
            current=current,
            round_index=round_index,
            mutation_strategy=mutation_strategy,
            source_bundle=source_bundle,
        )
        current = mutate_candidate(
            candidate=current,
            round_index=round_index,
            mutation_plan=mutation_plan,
        )

        llm_doc: dict[str, Any] | None = None
        llm_rejections: list[str] = []
        llm_stop_reason: str | None = None
        if drafting_mode == "llm-assisted" and provider is not None and token_budget is not None:
            current, llm_doc, llm_rejections, llm_stop_reason = apply_llm_drafting(
                candidate=current,
                source_bundle=source_bundle,
                run_root=run_root,
                round_index=round_index,
                llm_provider=provider,
                budget_tracker=token_budget,
            )

        scorecard = score_candidate(
            boundary_quality=float(current["candidate"]["boundary_quality"]),
            eval_aggregate=float(current["candidate"]["eval_aggregate"]),
            cross_subset_stability=float(current["candidate"]["cross_subset_stability"]),
            baseline=baseline,
            bonuses=bonuses,
            weights=weights,
        )
        quality_assessment = assess_candidate_output(
            candidate=current,
            profile=source_bundle.profile,
            loop_scorecard=scorecard,
        )
        scorecard.update(
            {
                "artifact_quality": quality_assessment["artifact_quality"],
                "artifact_grade": quality_assessment["artifact_grade"],
                "production_quality": quality_assessment["production_quality"],
                "quality_grade": quality_assessment["quality_grade"],
                "release_ready": quality_assessment["release_ready"],
            }
        )
        history.append(scorecard)
        structural_valid = _structural_gate(current)

        if llm_stop_reason == "llm_budget_exhausted":
            current["candidate"].update(scorecard)
            current["candidate"]["terminal_state"] = "do_not_publish"
            _write_round(
                run_root=run_root,
                round_index=round_index,
                current=current,
                mutation_plan=mutation_plan,
                scorecard=scorecard,
                decision={
                    "terminal_state": "do_not_publish",
                    "reason": llm_stop_reason,
                    "continue_loop": False,
                },
                llm_doc=llm_doc,
                llm_rejections=llm_rejections,
                quality_assessment=quality_assessment,
            )
            write_final_decision(
                run_root,
                {
                    "candidate_id": current["candidate"]["candidate_id"],
                    "terminal_state": "do_not_publish",
                    "reason": llm_stop_reason,
                    "overall_quality": current["candidate"].get("overall_quality"),
                    "production_quality": current["candidate"].get("production_quality"),
                    "quality_grade": current["candidate"].get("quality_grade"),
                    "net_positive_value": current["candidate"].get("net_positive_value"),
                },
            )
            return current

        decision = decide_terminal_state(
            round_index=round_index,
            config=config,
            scorecard=scorecard,
            history=history,
            structural_valid=structural_valid,
        )
        current["candidate"].update(scorecard)
        current["candidate"]["terminal_state"] = decision["terminal_state"]
        _write_round(
            run_root=run_root,
            round_index=round_index,
            current=current,
            mutation_plan=mutation_plan,
            scorecard=scorecard,
            decision=decision,
            llm_doc=llm_doc,
            llm_rejections=llm_rejections,
            quality_assessment=quality_assessment,
        )
        if not decision["continue_loop"]:
            write_final_decision(
                run_root,
                {
                    "candidate_id": current["candidate"]["candidate_id"],
                    "terminal_state": decision["terminal_state"],
                    "reason": decision["reason"],
                    "overall_quality": current["candidate"].get("overall_quality"),
                    "production_quality": current["candidate"].get("production_quality"),
                    "quality_grade": current["candidate"].get("quality_grade"),
                    "net_positive_value": current["candidate"].get("net_positive_value"),
                },
            )
            return current

    current["candidate"]["terminal_state"] = "max_rounds_reached"
    write_final_decision(
        run_root,
        {
            "candidate_id": current["candidate"]["candidate_id"],
            "terminal_state": "max_rounds_reached",
            "reason": "max_rounds_reached",
            "overall_quality": current["candidate"].get("overall_quality"),
            "production_quality": current["candidate"].get("production_quality"),
            "quality_grade": current["candidate"].get("quality_grade"),
            "net_positive_value": current["candidate"].get("net_positive_value"),
        },
    )
    return current


def refine_bundle_candidates(
    *,
    candidates: list[dict[str, Any]],
    source_bundle: SourceBundle,
    run_root: str | Path,
    llm_provider: LLMProvider | None = None,
    llm_budget_tokens: int = 100000,
) -> list[dict[str, Any]]:
    refined: list[dict[str, Any]] = []
    states: Counter[str] = Counter()
    final_docs: list[dict[str, Any]] = []
    shared_budget = LLMBudgetTracker(max_tokens=llm_budget_tokens)
    for candidate in candidates:
        result = refine_candidate(
            candidate=candidate,
            source_bundle=source_bundle,
            run_root=run_root,
            llm_provider=llm_provider,
            llm_budget_tokens=llm_budget_tokens,
            budget_tracker=shared_budget,
        )
        refined.append(result)
        state = result["candidate"]["terminal_state"]
        states[state] += 1
        final_docs.append(
            {
                "candidate_id": result["candidate"]["candidate_id"],
                "terminal_state": state,
                "overall_quality": result["candidate"].get("overall_quality"),
                "production_quality": result["candidate"].get("production_quality"),
                "quality_grade": result["candidate"].get("quality_grade"),
                "net_positive_value": result["candidate"].get("net_positive_value"),
            }
        )

    write_scorecard(
        run_root,
        {
            "candidate_count": len(refined),
            "terminal_states": dict(states),
            "candidates": final_docs,
        },
    )
    write_final_decision(
        run_root,
        {
            "terminal_states": dict(states),
            "candidates": final_docs,
            "llm_budget": {
                "spent_tokens": shared_budget.spent_tokens,
                "max_tokens": shared_budget.max_tokens,
                "remaining_tokens": shared_budget.remaining_tokens,
            },
        },
    )
    return refined


def plan_round_mutation(
    *,
    current: dict[str, Any],
    round_index: int,
    mutation_strategy: str,
    source_bundle: SourceBundle,
) -> dict[str, Any]:
    if mutation_strategy == "stalled":
        return {
            "boundary_strength_delta": 0.0,
            "eval_gain_delta": 0.0,
            "stability_delta": 0.0,
            "append_trace_ref": None,
            "revision_note": f"Round {round_index} produced no material improvement.",
        }

    skill_id = current["candidate"]["candidate_id"]
    source_skill = source_bundle.skills.get(skill_id)
    trace_refs = source_skill.trace_refs if source_skill else []
    trace_ref = trace_refs[min(round_index - 1, len(trace_refs) - 1)] if trace_refs else None
    return {
        "boundary_strength_delta": 0.05,
        "eval_gain_delta": 0.05,
        "stability_delta": 0.05,
        "append_trace_ref": trace_ref,
        "revision_note": (
            f"Refinement scheduler round {round_index} tightened boundary signals and"
            " improved evaluation support."
        ),
    }


def _initialize_candidate_metrics(
    candidate: dict[str, Any],
    *,
    weights: dict[str, float],
) -> dict[str, Any]:
    initialized = deepcopy(candidate)
    metrics = quality_from_eval_summary(
        initialized["eval_summary"],
        weights=weights,
    )
    for key in ("boundary_quality", "eval_aggregate", "cross_subset_stability"):
        initialized["candidate"].setdefault(key, metrics[key])
    initialized["candidate"].setdefault("current_round", 0)
    initialized["candidate"].setdefault("loop_mode", "refinement_scheduler")
    initialized["candidate"].setdefault("terminal_state", "pending")
    initialized["candidate"].setdefault("human_gate", "skipped")
    return initialized


def _structural_gate(candidate: dict[str, Any]) -> bool:
    return bool(
        candidate.get("skill_markdown")
        and candidate.get("anchors")
        and candidate.get("eval_summary")
        and candidate.get("revisions")
        and candidate.get("candidate")
    )


def _write_round(
    *,
    run_root: str | Path,
    round_index: int,
    current: dict[str, Any],
    mutation_plan: dict[str, Any],
    scorecard: dict[str, Any],
    decision: dict[str, Any],
    llm_doc: dict[str, Any] | None,
    llm_rejections: list[str],
    quality_assessment: dict[str, Any],
) -> None:
    doc = {
        "candidate_id": current["candidate"]["candidate_id"],
        "mutation_plan": mutation_plan,
        "scorecard": scorecard,
        "decision": decision,
        "quality_assessment": quality_assessment,
    }
    if llm_doc is not None or llm_rejections:
        doc["llm_drafting"] = llm_doc
        doc["llm_rejections"] = llm_rejections
    write_round_report(
        run_root,
        round_index,
        doc,
        candidate_id=current["candidate"]["candidate_id"],
    )
