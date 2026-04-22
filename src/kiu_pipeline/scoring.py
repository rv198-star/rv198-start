from __future__ import annotations

from typing import Any


DEFAULT_WEIGHTS = {
    "boundary_quality": 0.45,
    "eval_aggregate": 0.35,
    "cross_subset_stability": 0.20,
}


def quality_from_eval_summary(
    eval_summary: dict[str, Any],
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    weights = weights or DEFAULT_WEIGHTS
    boundary_quality = _boundary_quality_from_eval(eval_summary)
    subset_scores = _subset_scores(eval_summary)
    if subset_scores:
        eval_aggregate = sum(subset_scores) / len(subset_scores)
        cross_subset_stability = max(0.0, 1.0 - (max(subset_scores) - min(subset_scores)))
    else:
        eval_aggregate = 0.0
        cross_subset_stability = 0.0
    overall_quality = (
        weights["boundary_quality"] * boundary_quality
        + weights["eval_aggregate"] * eval_aggregate
        + weights["cross_subset_stability"] * cross_subset_stability
    )
    return {
        "boundary_quality": round(boundary_quality, 4),
        "eval_aggregate": round(eval_aggregate, 4),
        "cross_subset_stability": round(cross_subset_stability, 4),
        "overall_quality": round(overall_quality, 4),
    }


def score_candidate(
    *,
    boundary_quality: float,
    eval_aggregate: float,
    cross_subset_stability: float,
    baseline: dict[str, Any],
    bonuses: dict[str, float],
    weights: dict[str, float],
) -> dict[str, float | str]:
    overall_quality = (
        weights["boundary_quality"] * boundary_quality
        + weights["eval_aggregate"] * eval_aggregate
        + weights["cross_subset_stability"] * cross_subset_stability
    )
    delta_vs_nearest = overall_quality - baseline["nearest_skill_overall_quality"]
    delta_vs_bundle = overall_quality - baseline["bundle_proxy_overall_quality"]
    net_positive_value = min(delta_vs_nearest, delta_vs_bundle)
    if delta_vs_nearest > 0 and delta_vs_bundle > 0:
        net_positive_value += bonuses.get("clarity", 0.0) + bonuses.get("coverage", 0.0)

    return {
        "nearest_skill_id": baseline["nearest_skill_id"],
        "boundary_quality": round(boundary_quality, 4),
        "eval_aggregate": round(eval_aggregate, 4),
        "cross_subset_stability": round(cross_subset_stability, 4),
        "overall_quality": round(overall_quality, 4),
        "delta_vs_nearest": round(delta_vs_nearest, 4),
        "delta_vs_bundle": round(delta_vs_bundle, 4),
        "net_positive_value": round(net_positive_value, 4),
    }


def decide_terminal_state(
    *,
    round_index: int,
    config: dict[str, Any],
    scorecard: dict[str, Any],
    history: list[dict[str, Any]],
    structural_valid: bool,
) -> dict[str, Any]:
    if not structural_valid:
        return {
            "terminal_state": "do_not_publish",
            "continue_loop": False,
            "reason": "structural_gate_failed",
        }

    targets = config.get("targets", {})
    min_rounds = config.get("min_rounds", 2)
    max_rounds = config.get("max_rounds", 5)
    patience = config.get("patience", 2)
    artifact_quality_target = targets.get("artifact_quality")
    production_quality_target = targets.get("production_quality")
    content_quality_ready = True
    if artifact_quality_target is not None:
        content_quality_ready = (
            content_quality_ready
            and scorecard.get("artifact_quality", 0.0) >= artifact_quality_target
        )
    if production_quality_target is not None:
        content_quality_ready = (
            content_quality_ready
            and scorecard.get("production_quality", 0.0) >= production_quality_target
        )

    if (
        round_index >= min_rounds
        and scorecard["overall_quality"] >= targets.get("overall_quality", 1.0)
        and scorecard["boundary_quality"] >= targets.get("boundary_quality", 1.0)
        and scorecard["delta_vs_nearest"] >= targets.get("min_positive_delta", 0.0)
        and scorecard["delta_vs_bundle"] >= targets.get("min_positive_delta", 0.0)
        and content_quality_ready
    ):
        return {
            "terminal_state": "ready_for_review",
            "continue_loop": False,
            "reason": "targets_met",
        }

    if round_index >= min_rounds and scorecard["net_positive_value"] <= 0:
        return {
            "terminal_state": "do_not_publish",
            "continue_loop": False,
            "reason": "no_net_positive_value",
        }

    if _is_stalled(history, patience=patience):
        return {
            "terminal_state": "do_not_publish",
            "continue_loop": False,
            "reason": "stalled_progress",
        }

    if round_index >= min_rounds and not content_quality_ready and round_index < max_rounds:
        return {
            "terminal_state": "pending",
            "continue_loop": True,
            "reason": "content_quality_below_release_bar",
        }

    if round_index >= max_rounds:
        return {
            "terminal_state": "max_rounds_reached",
            "continue_loop": False,
            "reason": "max_rounds_reached",
        }

    return {
        "terminal_state": "pending",
        "continue_loop": True,
        "reason": "continue",
    }


def _boundary_quality_from_eval(eval_summary: dict[str, Any]) -> float:
    kiu_test = eval_summary.get("kiu_test", {})
    passed = sum(
        1
        for gate in ("trigger_test", "fire_test", "boundary_test")
        if kiu_test.get(gate) == "pass"
    )
    return (passed / 3.0) * 0.9


def _subset_scores(eval_summary: dict[str, Any]) -> list[float]:
    subsets = eval_summary.get("subsets", {})
    scores: list[float] = []
    for subset_name in (
        "real_decisions",
        "synthetic_adversarial",
        "out_of_distribution",
    ):
        subset = subsets.get(subset_name, {})
        threshold = float(subset.get("threshold", 0.0) or 0.0)
        total = int(subset.get("total", 0) or 0)
        passed = int(subset.get("passed", 0) or 0)
        if subset.get("status") == "pass" and threshold > 0:
            scores.append(threshold)
        elif total > 0:
            scores.append(passed / total)
        else:
            scores.append(0.0)
    return scores


def _is_stalled(history: list[dict[str, Any]], *, patience: int) -> bool:
    if patience <= 0 or len(history) < patience:
        return False
    window = history[-patience:]
    values = [float(entry.get("overall_quality", 0.0)) for entry in window]
    if len(values) < 2:
        return False
    return max(values) - min(values) < 0.01
