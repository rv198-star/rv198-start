from __future__ import annotations

import re
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
    eval_summary: dict[str, Any] | None = None,
    revisions: dict[str, Any] | None = None,
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
    eval_summary_doc = eval_summary
    if eval_summary_doc is None:
        eval_summary_doc = source_skill.eval_summary if source_skill else seed_content.get("eval_summary", {})
    evaluation_summary = build_evaluation_summary_markdown(eval_summary_doc)

    revisions_doc = revisions
    if revisions_doc is None:
        revisions_doc = source_skill.revisions if source_skill else seed_content.get("revisions", {})
        if not revisions_doc and not source_skill:
            revisions_doc = {
                "current_revision": skill_revision,
                "history": [
                    {
                        "revision": skill_revision,
                        "summary": _build_seed_revision_summary(seed),
                        "evidence_changes": [],
                    }
                ],
                "open_gaps": [],
            }
    revision_summary = build_revision_summary_markdown(revisions_doc)

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
    contract_key = seed.candidate_id.replace("-", "_")
    return {
        "trigger": {
            "patterns": [
                f"{contract_key}_needed",
                f"{contract_key}_decision_window",
            ],
            "exclusions": [f"{contract_key}_out_of_scope"],
        },
        "intake": {
            "required": [
                {
                    "name": "scenario",
                    "type": "structured",
                    "description": "Scenario summary that may require this skill.",
                },
                {
                    "name": "decision_goal",
                    "type": "string",
                    "description": "What decision or action the user is trying to make.",
                },
                {
                    "name": "current_constraints",
                    "type": "list[string]",
                    "description": "Operational constraints, boundary conditions, or missing context signals.",
                }
            ]
        },
        "judgment_schema": {
            "output": {
                "type": "structured",
                "schema": {
                    "verdict": "enum[apply|defer|do_not_apply]",
                    "next_action": "string",
                    "confidence": "enum[low|medium|high]",
                },
            },
            "reasoning_chain_required": True,
        },
        "boundary": {
            "fails_when": [f"{contract_key}_evidence_conflict"],
            "do_not_fire_when": [f"{contract_key}_scenario_missing"],
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
        "The draft treats this passage as an operational principle rather than a generic summary: "
        "it captures what should be checked, what kind of context must already be present, and "
        "what evidence would make the recommendation unsafe to apply. "
        "This keeps the contract narrow enough to be testable while preserving the source text's "
        "decision logic. "
        f"{support_text} "
        "As a result, the initial skill draft is expected to help a reviewer decide whether this "
        "principle should actively fire, be deferred for more context, or remain outside scope."
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


def build_evaluation_summary_markdown(eval_summary: dict[str, Any]) -> str:
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


def build_revision_summary_markdown(revisions: dict[str, Any]) -> str:
    current_revision = int(revisions.get("current_revision", 1) or 1)
    history = revisions.get("history", [])
    current_entry = next(
        (
            entry
            for entry in reversed(history)
            if int(entry.get("revision", 0) or 0) == current_revision
        ),
        history[-1] if history else {},
    )
    lines = [
        current_entry.get(
            "summary",
            (
                "Revision 1 is the initial v0.2 pipeline seed. The next loop must confirm"
                " trigger precision, boundary quality, and whether the attached evidence is"
                " sufficient for publication. See `iterations/revisions.yaml`."
            ),
        )
    ]
    evidence_changes = current_entry.get("evidence_changes", [])
    if evidence_changes:
        lines.append("")
        lines.append("本轮补入：")
        for item in evidence_changes:
            lines.append(f"- {item}")
    open_gaps = revisions.get("open_gaps", [])
    if open_gaps:
        lines.append("")
        lines.append("当前待补缺口：")
        for item in open_gaps:
            lines.append(f"- {item}")
    return "\n".join(lines)


def synchronize_candidate_skill_markdown(
    skill_markdown: str,
    *,
    eval_summary: dict[str, Any],
    revisions: dict[str, Any],
    skill_revision: int,
    status: str = "under_evaluation",
) -> str:
    updated = _update_skill_markdown_metadata(
        skill_markdown,
        skill_revision=skill_revision,
        status=status,
    )
    updated = replace_markdown_section(
        updated,
        "Evaluation Summary",
        build_evaluation_summary_markdown(eval_summary),
    )
    updated = replace_markdown_section(
        updated,
        "Revision Summary",
        build_revision_summary_markdown(revisions),
    )
    return updated


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
        relative_path = source_anchor.get("path")
        line_start = source_anchor.get("line_start")
        line_end = source_anchor.get("line_end")
        snippet = source_anchor.get("snippet")
        if not relative_path:
            relative_path = node_doc.get("source_file")
            source_location = node_doc.get("source_location", {})
            if isinstance(source_location, dict):
                line_start = source_location.get("line_start", line_start)
                line_end = source_location.get("line_end", line_end)
        if not snippet:
            snippet = _read_snippet_from_bundle(
                source_bundle=source_bundle,
                relative_path=relative_path,
                line_start=int(line_start or 1),
                line_end=int(line_end or line_start or 1),
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


def replace_markdown_section(markdown: str, section_name: str, body: str) -> str:
    pattern = rf"(^## {re.escape(section_name)}\n)(.*?)(?=^## |\Z)"
    replacement = rf"\1{body.strip()}\n\n"
    if re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL):
        return re.sub(pattern, replacement, markdown, count=1, flags=re.MULTILINE | re.DOTALL)
    return markdown.rstrip() + f"\n\n## {section_name}\n{body.strip()}\n"


def _update_skill_markdown_metadata(
    skill_markdown: str,
    *,
    skill_revision: int,
    status: str,
) -> str:
    updated = skill_markdown
    updated = re.sub(
        r"status:\s+\w+",
        f"status: {status}",
        updated,
        count=1,
    )
    updated = re.sub(
        r"skill_revision:\s+\d+",
        f"skill_revision: {skill_revision}",
        updated,
        count=1,
    )
    return updated


def _yaml_block(doc: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True).rstrip()
    return f"```yaml\n{rendered}\n```"


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
