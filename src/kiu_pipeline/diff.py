from __future__ import annotations

from .models import CandidateSeed, SourceBundle


def build_metrics(
    *,
    source_bundle: SourceBundle,
    rendered_seeds: list[CandidateSeed],
    workflow_only_seeds: list[CandidateSeed],
) -> dict:
    matched_gold_skill_ids = sorted(
        {
            seed.gold_match_hint
            for seed in rendered_seeds
            if seed.gold_match_hint in source_bundle.skills
        }
    )
    missing_gold_skill_ids = sorted(set(source_bundle.skills) - set(matched_gold_skill_ids))
    workflow_script_candidate_ids = sorted(seed.candidate_id for seed in workflow_only_seeds)

    return {
        "source_bundle_id": source_bundle.manifest["bundle_id"],
        "summary": {
            "skill_candidates": len(rendered_seeds),
            "workflow_script_candidates": len(workflow_only_seeds),
            "matched_gold_skills": len(matched_gold_skill_ids),
            "missing_gold_skills": len(missing_gold_skill_ids),
        },
        "matched_gold_skill_ids": matched_gold_skill_ids,
        "missing_gold_skill_ids": missing_gold_skill_ids,
        "workflow_script_candidate_ids": workflow_script_candidate_ids,
        "candidate_ids": [seed.candidate_id for seed in rendered_seeds],
    }
