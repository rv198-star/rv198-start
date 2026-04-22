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
    seed_content = seed.seed_content or {}
    title = source_skill.title if source_skill else seed_content.get("title", _titleize(seed.candidate_id))
    contract = source_skill.contract if source_skill else seed_content.get("contract", _fallback_contract(seed))
    relations = source_skill.relations if source_skill else seed_content.get("relations", EMPTY_RELATIONS)
    trace_refs = source_skill.trace_refs if source_skill else list(seed_content.get("trace_refs", []))

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
        else seed_content.get("rationale", "").strip() or _fallback_rationale(source_bundle, seed)
    )
    evidence_summary = _build_evidence_summary(source_bundle, seed)
    usage_summary = seed_content.get("usage_summary", "").strip() or _build_usage_summary(
        trace_refs,
        usage_notes=seed_content.get("usage_notes", []),
    )
    evaluation_summary = (
        "This candidate was prefilled by the v0.2 deterministic pipeline and remains"
        " `under_evaluation`. Shared evaluation cases are attached in `eval/summary.yaml`"
        " and must be reviewed before publication."
    )
    if not source_skill:
        evaluation_summary = _build_seed_evaluation_summary(seed)
    revision_summary = (
        "Revision 1 is the initial v0.2 pipeline seed. The next loop must confirm"
        " trigger precision, boundary quality, and whether the attached evidence is"
        " sufficient for publication. See `iterations/revisions.yaml`."
    )
    if not source_skill:
        revision_summary = _build_seed_revision_summary(seed)

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
    source_skill = seed.source_skill
    if source_skill:
        base = source_skill.sections.get("Evidence Summary", "").strip()
        if base:
            return (
                f"{base}\n\n"
                "The v0.2 seed preserves graph/source double anchoring and records the"
                " workflow-vs-agentic routing decision in `candidate.yaml`."
            )
    seed_evidence = seed.seed_content.get("evidence_summary", "").strip()
    if seed_evidence:
        return seed_evidence
    anchors = _collect_anchor_descriptors(source_bundle, seed)
    if anchors:
        primary = anchors[0]
        supporting = anchors[1:]
        lines = [
            (
                f"Primary evidence comes from `{primary['label']}`: {primary['snippet']}"
                f"[^anchor:{primary['anchor_id']}]"
            ),
        ]
        if supporting:
            support_text = " ".join(
                f"`{item['label']}` adds context: {item['snippet']}[^anchor:{item['anchor_id']}]"
                for item in supporting
            )
            lines.append(support_text)
        lines.append("See `anchors.yaml` and `candidate.yaml` for the released graph/source bindings.")
        return "\n\n".join(lines)
    return (
        "The current draft is anchored to the released graph snapshot and awaits"
        " source/scenario evidence enrichment before it can move beyond"
        " `under_evaluation`. See `anchors.yaml` and `candidate.yaml`."
    )


def _build_usage_summary(trace_refs: list[str], usage_notes: list[str] | None = None) -> str:
    lines = [f"Current trace attachments: {len(trace_refs)}.", ""]
    for note in usage_notes or []:
        lines.append(f"- {note}")
    if usage_notes:
        lines.append("")
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


def _fallback_rationale(source_bundle: SourceBundle, seed: CandidateSeed) -> str:
    anchors = _collect_anchor_descriptors(source_bundle, seed)
    if not anchors:
        return (
            "This candidate was seeded from the graph snapshot and still needs human"
            " review to turn the draft into a stable judgment contract."
        )
    primary = anchors[0]
    supporting = anchors[1:]
    support_text = ""
    if supporting:
        support_text = " ".join(
            f"`{item['label']}` provides supporting context: {item['snippet']}[^anchor:{item['anchor_id']}]"
            for item in supporting
        )
    return (
        f"The candidate centers on `{primary['label']}` and is grounded in the source excerpt "
        f"\"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
        "The initial deterministic draft therefore keeps the judgment focused on the source-backed "
        "principle rather than broadening into generic advice. "
        f"{support_text}".strip()
    )


def _build_seed_evaluation_summary(seed: CandidateSeed) -> str:
    eval_summary = seed.seed_content.get("eval_summary", {})
    kiu_test = eval_summary.get("kiu_test", {})
    subsets = eval_summary.get("subsets", {})
    lines = [
        (
            "当前 KiU Test 状态："
            f"trigger_test=`{kiu_test.get('trigger_test', 'pending')}`，"
            f"fire_test=`{kiu_test.get('fire_test', 'pending')}`，"
            f"boundary_test=`{kiu_test.get('boundary_test', 'pending')}`。"
        ),
        "",
        "已绑定最小评测集：",
    ]
    for subset_name in ("real_decisions", "synthetic_adversarial", "out_of_distribution"):
        subset = subsets.get(subset_name, {})
        lines.append(
            (
                f"- `{subset_name}`: passed={subset.get('passed', 0)} / total={subset.get('total', 0)}, "
                f"threshold={subset.get('threshold', 0.0)}, status=`{subset.get('status', 'pending')}`"
            )
        )
    key_failure_modes = eval_summary.get("key_failure_modes", [])
    if key_failure_modes:
        lines.append("")
        lines.append("关键失败模式：")
        for item in key_failure_modes:
            lines.append(f"- {item}")
    lines.append("")
    lines.append("详见 `eval/summary.yaml` 与共享 `evaluation/`。")
    return "\n".join(lines)


def _build_seed_revision_summary(seed: CandidateSeed) -> str:
    revision_seed = seed.seed_content.get("revision_seed", {})
    lines = [
        revision_seed.get(
            "summary",
            (
                "Revision 1 is the initial v0.2 pipeline seed. The next loop must confirm"
                " trigger precision, boundary quality, and whether the attached evidence is"
                " sufficient for publication. See `iterations/revisions.yaml`."
            ),
        )
    ]
    evidence_changes = revision_seed.get("evidence_changes", [])
    if evidence_changes:
        lines.append("")
        lines.append("本轮补入：")
        for item in evidence_changes:
            lines.append(f"- {item}")
    open_gaps = revision_seed.get("open_gaps", [])
    if open_gaps:
        lines.append("")
        lines.append("当前待补缺口：")
        for item in open_gaps:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _collect_anchor_descriptors(source_bundle: SourceBundle, seed: CandidateSeed) -> list[dict[str, str]]:
    node_docs = {
        node["id"]: node
        for node in source_bundle.graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    descriptors: list[dict[str, str]] = []
    for node_id in [seed.primary_node_id, *seed.supporting_node_ids]:
        node_doc = node_docs.get(node_id, {})
        source_anchor = node_doc.get("source_anchor", {})
        snippet = source_anchor.get("snippet")
        if not snippet:
            snippet = _read_snippet_from_bundle(
                source_bundle=source_bundle,
                relative_path=source_anchor.get("path"),
                line_start=int(source_anchor.get("line_start", 1)),
                line_end=int(source_anchor.get("line_end", source_anchor.get("line_start", 1))),
            )
        if not snippet:
            continue
        descriptors.append(
            {
                "anchor_id": f"{seed.candidate_id}-{node_id}",
                "label": node_doc.get("label", node_id),
                "snippet": snippet,
            }
        )
    return descriptors


def _read_snippet_from_bundle(
    *,
    source_bundle: SourceBundle,
    relative_path: str | None,
    line_start: int,
    line_end: int,
) -> str:
    if not relative_path:
        return ""
    path = source_bundle.root / relative_path
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = " ".join(
        line.strip()
        for line in lines[line_start - 1 : line_end]
        if line.strip()
    )
    return excerpt[:220] if len(excerpt) > 220 else excerpt


def _titleize(text: str) -> str:
    return text.replace("-", " ").title()


def _yaml_block(doc: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True).rstrip()
    return f"```yaml\n{rendered}\n```"
