from __future__ import annotations

from typing import Any

from .models import SourceBundle
from .scoring import DEFAULT_WEIGHTS, quality_from_eval_summary


def build_candidate_baseline(
    *,
    source_bundle: SourceBundle,
    nearest_skill_id: str,
) -> dict[str, Any]:
    weights = (
        source_bundle.profile.get("refinement_scheduler", {}).get("weights")
        or DEFAULT_WEIGHTS
    )
    nearest_skill = source_bundle.skills.get(nearest_skill_id)
    if nearest_skill is not None:
        nearest_metrics = quality_from_eval_summary(
            nearest_skill.eval_summary,
            weights=weights,
        )
        nearest_overall_quality = round(nearest_metrics["overall_quality"], 4)
    else:
        nearest_overall_quality = 0.0
    bundle_scores = [
        quality_from_eval_summary(skill.eval_summary, weights=weights)["overall_quality"]
        for skill in source_bundle.skills.values()
    ]
    bundle_proxy_overall_quality = (
        sum(bundle_scores) / len(bundle_scores) if bundle_scores else 0.0
    )
    return {
        "nearest_skill_id": nearest_skill_id,
        "nearest_skill_overall_quality": nearest_overall_quality,
        "bundle_proxy_overall_quality": round(bundle_proxy_overall_quality, 4),
    }
