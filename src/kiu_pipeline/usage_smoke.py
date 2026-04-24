from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .load import extract_yaml_section, parse_sections
from .render import load_generated_candidates


def write_smoke_usage_reviews(run_root: Path) -> None:
    """Emit source-backed smoke usage reviews for generated skill candidates."""
    bundle_root = run_root / "bundle"
    usage_root = run_root / "usage-review"
    usage_root.mkdir(parents=True, exist_ok=True)
    candidates = load_generated_candidates(bundle_root)
    for candidate in candidates:
        skill_id = candidate["candidate"]["candidate_id"]
        anchors = candidate.get("anchors", {})
        source_anchors = anchors.get("source_anchor_sets", [])
        primary_anchor = source_anchors[0] if source_anchors else {}
        secondary_anchor = source_anchors[1] if len(source_anchors) > 1 else primary_anchor
        sections = parse_sections(candidate.get("skill_markdown", ""))
        contract = extract_yaml_section(sections.get("Contract", ""))
        trigger_patterns = [
            item
            for item in contract.get("trigger", {}).get("patterns", [])
            if isinstance(item, str)
        ]
        output_schema = (
            contract.get("judgment_schema", {})
            .get("output", {})
            .get("schema", {})
        )
        verdict = output_schema.get("verdict", "apply")
        evidence_to_check = _derive_smoke_evidence_to_check(
            primary_anchor=primary_anchor,
            secondary_anchor=secondary_anchor,
            trigger_patterns=trigger_patterns,
        )
        next_action = _derive_specific_next_action(
            skill_id=skill_id,
            verdict=verdict if isinstance(verdict, str) else "apply",
            primary_anchor=primary_anchor,
            secondary_anchor=secondary_anchor,
        )
        usage_doc = {
            "review_case_id": f"{skill_id}-smoke-usage",
            "generated_run_root": str(run_root),
            "skill_path": str(bundle_root / "skills" / skill_id / "SKILL.md"),
            "input_scenario": {
                "scenario": primary_anchor.get("snippet", ""),
                "decision_goal": f"Decide whether `{skill_id}` should fire for this source-backed situation.",
                "decision_scope": (
                    f"Only use `{skill_id}` for the decision boundary implied by "
                    f"`{primary_anchor.get('anchor_id', skill_id)}`."
                ),
                "current_constraints": [
                    f"Confirm the scenario still satisfies `{trigger_patterns[0]}`."
                ] if trigger_patterns else [],
                "disconfirming_evidence": [
                    (
                        "Do not apply if new facts contradict the primary evidence "
                        f"anchored at `{primary_anchor.get('anchor_id', skill_id)}`."
                    )
                ],
            },
            "firing_assessment": {
                "should_fire": True,
                "why_this_skill_fired": [
                    f"The scenario directly resembles `{primary_anchor.get('anchor_id', skill_id)}`.",
                    f"The neighboring evidence in `{secondary_anchor.get('anchor_id', skill_id)}` keeps the boundary specific.",
                ],
            },
            "boundary_check": {
                "status": "pass",
                "notes": [
                    "This is an automated smoke usage review, not a production judgment.",
                    "The scenario still includes concrete evidence and decision context.",
                ],
            },
            "structured_output": {
                "verdict": verdict if isinstance(verdict, str) else "apply",
                "next_action": next_action,
                "evidence_to_check": evidence_to_check,
                "decline_reason": (
                    "Decline if the scenario loses concrete decision context or if disconfirming "
                    "evidence overrides the anchored pattern."
                ),
                "confidence": "medium",
            },
            "analysis_summary": (
                f"The smoke review fired `{skill_id}` because the scenario is anchored to "
                f"the same evidence path as `{primary_anchor.get('anchor_id', skill_id)}`."
            ),
            "quality_assessment": {
                "contract_fit": "strong" if trigger_patterns else "medium",
                "evidence_alignment": [
                    anchor.get("anchor_id")
                    for anchor in source_anchors[:2]
                    if isinstance(anchor, dict) and anchor.get("anchor_id")
                ],
                "caveats": [
                    "Replace this smoke review with real usage evidence before release."
                ],
            },
        }
        (usage_root / f"{skill_id}-smoke.yaml").write_text(
            yaml.safe_dump(usage_doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _derive_specific_next_action(
    *,
    skill_id: str,
    verdict: str,
    primary_anchor: dict[str, Any],
    secondary_anchor: dict[str, Any],
) -> str:
    primary_fragment = _smoke_action_fragment(primary_anchor, fallback=skill_id)
    secondary_fragment = _smoke_action_fragment(secondary_anchor, fallback=f"{skill_id}_boundary")
    normalized_verdict = verdict.strip().lower()

    if normalized_verdict == "do_not_apply":
        return f"test_{primary_fragment}_against_{secondary_fragment}_disconfirming_evidence"
    if normalized_verdict == "defer":
        return f"resolve_{secondary_fragment}_before_applying_{primary_fragment}"
    return f"verify_{primary_fragment}_evidence_and_{secondary_fragment}_boundary"


def _derive_smoke_evidence_to_check(
    *,
    primary_anchor: dict[str, Any],
    secondary_anchor: dict[str, Any],
    trigger_patterns: list[str],
) -> list[str]:
    evidence_items: list[str] = []
    for anchor in (primary_anchor, secondary_anchor):
        if not isinstance(anchor, dict):
            continue
        anchor_id = anchor.get("anchor_id")
        snippet = _compact_snippet(anchor.get("snippet", ""))
        if anchor_id:
            detail = f"`{anchor_id}`"
            if snippet:
                detail += f": {snippet}"
            evidence_items.append(detail)
    for pattern in trigger_patterns[:1]:
        evidence_items.append(f"Trigger still satisfied: `{pattern}`")
    return evidence_items or ["Re-check the anchored scenario before applying the draft."]


def _smoke_action_fragment(anchor: dict[str, Any], *, fallback: str) -> str:
    if not isinstance(anchor, dict):
        return _normalize_smoke_symbol(fallback)
    raw = anchor.get("anchor_id") or anchor.get("label") or anchor.get("snippet") or fallback
    return _normalize_smoke_symbol(str(raw))


def _normalize_smoke_symbol(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return normalized or "anchored_evidence"


def _compact_snippet(raw: str, *, limit: int = 96) -> str:
    text = " ".join(str(raw).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
