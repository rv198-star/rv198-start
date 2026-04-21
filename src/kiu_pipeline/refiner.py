from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .baseline import build_candidate_baseline
from .models import SourceBundle
from .mutate import mutate_candidate
from .reports import write_final_decision, write_round_report, write_scorecard
from .scoring import DEFAULT_WEIGHTS, decide_terminal_state, quality_from_eval_summary, score_candidate


def refine_candidate(
    *,
    candidate: dict[str, Any],
    source_bundle: SourceBundle,
    run_root: str | Path,
    mutation_strategy: str = "default",
) -> dict[str, Any]:
    config = source_bundle.profile.get("autonomous_refiner", {})
    weights = config.get("weights") or DEFAULT_WEIGHTS
    bonuses = config.get("bonuses", {})
    current = _initialize_candidate_metrics(candidate, weights=weights)
    nearest_skill_id = current.get("nearest_skill_id") or current["candidate"].get("gold_match_hint") or current["candidate"]["candidate_id"]
    baseline = build_candidate_baseline(
        source_bundle=source_bundle,
        nearest_skill_id=nearest_skill_id,
    )

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
        scorecard = score_candidate(
            boundary_quality=float(current["candidate"]["boundary_quality"]),
            eval_aggregate=float(current["candidate"]["eval_aggregate"]),
            cross_subset_stability=float(current["candidate"]["cross_subset_stability"]),
            baseline=baseline,
            bonuses=bonuses,
            weights=weights,
        )
        history.append(scorecard)
        structural_valid = _structural_gate(current)
        decision = decide_terminal_state(
            round_index=round_index,
            config=config,
            scorecard=scorecard,
            history=history,
            structural_valid=structural_valid,
        )
        current["candidate"].update(scorecard)
        current["candidate"]["terminal_state"] = decision["terminal_state"]
        write_round_report(
            run_root,
            round_index,
            {
                "candidate_id": current["candidate"]["candidate_id"],
                "mutation_plan": mutation_plan,
                "scorecard": scorecard,
                "decision": decision,
            },
            candidate_id=current["candidate"]["candidate_id"],
        )
        if not decision["continue_loop"]:
            write_final_decision(
                run_root,
                {
                    "candidate_id": current["candidate"]["candidate_id"],
                    "terminal_state": decision["terminal_state"],
                    "reason": decision["reason"],
                    "overall_quality": current["candidate"].get("overall_quality"),
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
            "net_positive_value": current["candidate"].get("net_positive_value"),
        },
    )
    return current


def refine_bundle_candidates(
    *,
    candidates: list[dict[str, Any]],
    source_bundle: SourceBundle,
    run_root: str | Path,
) -> list[dict[str, Any]]:
    refined: list[dict[str, Any]] = []
    states: Counter[str] = Counter()
    final_docs: list[dict[str, Any]] = []
    for candidate in candidates:
        result = refine_candidate(
            candidate=candidate,
            source_bundle=source_bundle,
            run_root=run_root,
        )
        refined.append(result)
        state = result["candidate"]["terminal_state"]
        states[state] += 1
        final_docs.append(
            {
                "candidate_id": result["candidate"]["candidate_id"],
                "terminal_state": state,
                "overall_quality": result["candidate"].get("overall_quality"),
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
            f"Autonomous refinement round {round_index} tightened boundary signals and"
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
    initialized["candidate"].setdefault("loop_mode", "autonomous_refiner")
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
