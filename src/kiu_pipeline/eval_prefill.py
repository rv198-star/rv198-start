from __future__ import annotations

from .models import CandidateSeed


def build_prefilled_eval_summary(
    *,
    seed: CandidateSeed,
    bundle_version: str,
    skill_revision: int,
) -> dict:
    source_skill = seed.source_skill
    source_summary = source_skill.eval_summary if source_skill else seed.seed_content.get(
        "eval_summary",
        {},
    )
    subsets = source_summary.get("subsets", {})
    references = dict(source_summary.get("references", {}))
    references.setdefault("evaluation_root", "../../../evaluation")
    references["prefill_mode"] = seed.metadata.get("drafting_mode", "deterministic")
    references["gold_skill_id"] = seed.gold_match_hint

    return {
        "skill_id": seed.candidate_id,
        "bundle_version": bundle_version,
        "skill_revision": skill_revision,
        "status": "under_evaluation",
        "kiu_test": {
            "trigger_test": source_summary.get("kiu_test", {}).get("trigger_test", "pending"),
            "fire_test": source_summary.get("kiu_test", {}).get("fire_test", "pending"),
            "boundary_test": source_summary.get("kiu_test", {}).get("boundary_test", "pending"),
        },
        "subsets": {
            "real_decisions": _prefill_subset(subsets.get("real_decisions", {})),
            "synthetic_adversarial": _prefill_subset(
                subsets.get("synthetic_adversarial", {})
            ),
            "out_of_distribution": _prefill_subset(
                subsets.get("out_of_distribution", {})
            ),
        },
        "key_failure_modes": source_summary.get(
            "key_failure_modes",
            ["Auto-seeded candidate still needs human review before publication."],
        ),
        "references": references,
    }


def _prefill_subset(subset: dict) -> dict:
    return {
        "cases": subset.get("cases", []),
        "passed": subset.get("passed", 0),
        "total": subset.get("total", 0),
        "threshold": subset.get("threshold", 0.0),
        "status": subset.get("status", "pending"),
    }
