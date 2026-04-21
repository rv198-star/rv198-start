from __future__ import annotations

from typing import Any

import yaml

from .models import CandidateSeed, SourceBundle


EMPTY_RELATIONS = {
    "depends_on": [],
    "delegates_to": [],
    "constrained_by": [],
    "complements": [],
    "contradicts": [],
}


def build_candidate_skill_markdown(
    *,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
    bundle_version: str,
    skill_revision: int,
) -> str:
    source_skill = seed.source_skill
    title = source_skill.title if source_skill else _titleize(seed.candidate_id)
    contract = source_skill.contract if source_skill else _fallback_contract(seed)
    relations = source_skill.relations if source_skill else EMPTY_RELATIONS
    trace_refs = source_skill.trace_refs if source_skill else []

    identity = {
        "skill_id": seed.candidate_id,
        "title": title,
        "status": "under_evaluation",
        "bundle_version": bundle_version,
        "skill_revision": skill_revision,
    }

    rationale = (
        source_skill.sections.get("Rationale", "").strip()
        if source_skill
        else (
            "This candidate was seeded from the graph snapshot and still needs human"
            " review to turn the draft into a stable judgment contract."
        )
    )
    evidence_summary = _build_evidence_summary(source_bundle, seed)
    usage_summary = _build_usage_summary(trace_refs)
    evaluation_summary = (
        "This candidate was prefilled by the v0.2 deterministic pipeline and remains"
        " `under_evaluation`. Shared evaluation cases are attached in `eval/summary.yaml`"
        " and must be reviewed before publication."
    )
    revision_summary = (
        "Revision 1 is the initial v0.2 pipeline seed. The next loop must confirm"
        " trigger precision, boundary quality, and whether the attached evidence is"
        " sufficient for publication. See `iterations/revisions.yaml`."
    )

    sections = [
        ("Identity", _yaml_block(identity)),
        ("Contract", _yaml_block(contract)),
        ("Rationale", rationale),
        ("Evidence Summary", evidence_summary),
        ("Relations", _yaml_block(relations)),
        ("Usage Summary", usage_summary),
        ("Evaluation Summary", evaluation_summary),
        ("Revision Summary", revision_summary),
    ]

    lines = [f"# {title}", ""]
    for section_name, body in sections:
        lines.append(f"## {section_name}")
        lines.append(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_evidence_summary(source_bundle: SourceBundle, seed: CandidateSeed) -> str:
    del source_bundle
    source_skill = seed.source_skill
    if source_skill:
        base = source_skill.sections.get("Evidence Summary", "").strip()
        if base:
            return (
                f"{base}\n\n"
                "The v0.2 seed preserves graph/source double anchoring and records the"
                " workflow-vs-agentic routing decision in `candidate.yaml`."
            )
    return (
        "The current draft is anchored to the released graph snapshot and awaits"
        " source/scenario evidence enrichment before it can move beyond"
        " `under_evaluation`. See `anchors.yaml` and `candidate.yaml`."
    )


def _build_usage_summary(trace_refs: list[str]) -> str:
    lines = [f"Current trace attachments: {len(trace_refs)}.", ""]
    if trace_refs:
        lines.append("Representative cases:")
        for trace_ref in trace_refs:
            lines.append(f"- `{trace_ref}`")
    else:
        lines.append("Representative cases are still pending curation.")
    return "\n".join(lines)


def _fallback_contract(seed: CandidateSeed) -> dict[str, Any]:
    return {
        "trigger": {
            "patterns": [f"candidate_seed::{seed.primary_node_id}"],
            "exclusions": [],
        },
        "intake": {
            "required": [
                {
                    "name": "scenario",
                    "type": "structured",
                    "description": "Scenario data required to review this candidate.",
                }
            ]
        },
        "judgment_schema": {
            "output": {
                "type": "structured",
                "schema": {"verdict": "enum[pending_review]"},
            },
            "reasoning_chain_required": True,
        },
        "boundary": {
            "fails_when": ["evidence_is_too_sparse_for_candidate_review"],
            "do_not_fire_when": ["candidate_has_not_been_reviewed_by_human"],
        },
    }


def _titleize(text: str) -> str:
    return text.replace("-", " ").title()


def _yaml_block(doc: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True).rstrip()
    return f"```yaml\n{rendered}\n```"
