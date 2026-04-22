from __future__ import annotations

from typing import Any

from .models import CandidateSeed, NormalizedGraph, SourceBundle


DEFAULT_WORKFLOW_TYPE_HINTS = {"control_principle", "control_signal"}
DEFAULT_WORKFLOW_LABEL_KEYWORDS = (
    "checklist",
    "preflight",
    "gate",
    "步骤",
    "清单",
    "检查",
    "预检",
)


def mine_candidate_seeds(
    bundle: SourceBundle,
    graph: NormalizedGraph,
    *,
    drafting_mode: str = "deterministic",
) -> list[CandidateSeed]:
    profile = bundle.profile
    seed_node_types = set(profile.get("seed_node_types", ["skill_principle"]))
    seeds: list[CandidateSeed] = []
    for node in graph.nodes.values():
        if node.get("type") not in seed_node_types:
            continue
        override = profile.get("seed_overrides", {}).get(node["id"], {})
        gold_match_hint = override.get("gold_match_hint")
        source_skill = bundle.skills.get(gold_match_hint) if gold_match_hint else None
        seed_content = override.get("skill_seed") or node.get("skill_seed", {})
        support = _collect_support(node["id"], graph)
        candidate_kind, routing_evidence = _resolve_candidate_kind(
            node=node,
            override=override,
            support=support,
            profile=profile,
        )
        metadata = derive_candidate_metadata(
            candidate_id=override.get("candidate_id") or gold_match_hint or _slugify(node["label"]),
            seed_node_id=node["id"],
            candidate_kind=candidate_kind,
            graph_hash=bundle.manifest["graph"]["graph_hash"],
            bundle_id=bundle.manifest["bundle_id"],
            routing_profile=profile,
            supporting_node_ids=support["supporting_node_ids"],
            supporting_edge_ids=support["supporting_edge_ids"],
            community_ids=support["community_ids"],
            gold_match_hint=gold_match_hint,
            drafting_mode=drafting_mode,
            routing_evidence=routing_evidence,
        )
        score = (
            len(source_skill.trace_refs) if source_skill else 0
        ) + len(support["supporting_edge_ids"]) + len(support["community_ids"]) + int(
            routing_evidence.get("workflow_cues", 0) or 0
        )
        seeds.append(
            CandidateSeed(
                candidate_id=metadata["candidate_id"],
                candidate_kind=candidate_kind,
                primary_node_id=node["id"],
                supporting_node_ids=support["supporting_node_ids"],
                supporting_edge_ids=support["supporting_edge_ids"],
                community_ids=support["community_ids"],
                gold_match_hint=gold_match_hint,
                source_skill=source_skill,
                score=score,
                metadata=metadata,
                seed_content=seed_content,
            )
        )
    seeds.sort(key=lambda seed: (-seed.score, seed.candidate_id))
    return seeds[: profile.get("max_candidates", len(seeds))]


def derive_candidate_metadata(
    *,
    candidate_id: str,
    seed_node_id: str,
    candidate_kind: str,
    graph_hash: str,
    bundle_id: str,
    routing_profile: dict[str, Any],
    supporting_node_ids: list[str] | None = None,
    supporting_edge_ids: list[str] | None = None,
    community_ids: list[str] | None = None,
    gold_match_hint: str | None = None,
    drafting_mode: str = "deterministic",
    routing_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kind_doc = routing_profile.get("candidate_kinds", {}).get(candidate_kind, {})
    workflow_certainty = kind_doc.get("workflow_certainty", "medium")
    context_certainty = kind_doc.get("context_certainty", "medium")
    execution_mode = "general_agentic"
    disposition = "skill_candidate"
    for rule in routing_profile.get("routing_rules", []):
        when = rule.get("when", {})
        if _matches_rule(
            when,
            workflow_certainty=workflow_certainty,
            context_certainty=context_certainty,
        ):
            execution_mode = rule["recommended_execution_mode"]
            disposition = rule["disposition"]
            break

    metadata = {
        "candidate_id": candidate_id,
        "source_bundle_id": bundle_id,
        "source_graph_hash": graph_hash,
        "seed": {
            "primary_node_id": seed_node_id,
            "supporting_node_ids": supporting_node_ids or [],
            "supporting_edge_ids": supporting_edge_ids or [],
            "community_ids": community_ids or [],
        },
        "candidate_kind": candidate_kind,
        "workflow_certainty": workflow_certainty,
        "context_certainty": context_certainty,
        "recommended_execution_mode": execution_mode,
        "disposition": disposition,
        "gold_match_hint": gold_match_hint,
        "drafting_mode": drafting_mode,
        "loop_mode": "refinement_scheduler",
        "current_round": 0,
        "terminal_state": "pending",
        "human_gate": "skipped",
    }
    if routing_evidence:
        metadata["routing_evidence"] = routing_evidence
    return metadata


def _resolve_candidate_kind(
    *,
    node: dict[str, Any],
    override: dict[str, Any],
    support: dict[str, list[str] | int],
    profile: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    override_candidate_kind = override.get("candidate_kind")
    if isinstance(override_candidate_kind, str) and override_candidate_kind:
        return (
            override_candidate_kind,
            {
                "inference_mode": "manual_override",
                "selected_candidate_kind": override_candidate_kind,
            },
        )
    return _infer_candidate_kind(
        node=node,
        support=support,
        profile=profile,
    )


def _infer_candidate_kind(
    *,
    node: dict[str, Any],
    support: dict[str, list[str] | int],
    profile: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    routing_inference = profile.get("routing_inference", {})
    workflow_script_doc = routing_inference.get("workflow_script", {})
    default_candidate_kind = routing_inference.get("default_candidate_kind", "general_agentic")

    type_hints = set(workflow_script_doc.get("type_hints", DEFAULT_WORKFLOW_TYPE_HINTS))
    label_keywords = tuple(
        workflow_script_doc.get("label_keywords", DEFAULT_WORKFLOW_LABEL_KEYWORDS)
    )
    min_workflow_cues = _normalize_nonnegative_int(
        workflow_script_doc.get("min_workflow_cues", 1)
    )
    min_context_cues = _normalize_nonnegative_int(
        workflow_script_doc.get("min_context_cues", 1)
    )

    node_hints = node.get("routing_hints", {})
    if not isinstance(node_hints, dict):
        node_hints = {}

    label = str(node.get("label", ""))
    label_lower = label.lower()
    label_matches = sorted(
        {
            keyword
            for keyword in label_keywords
            if keyword and keyword.lower() in label_lower
        }
    )
    workflow_cues = _normalize_nonnegative_int(node_hints.get("workflow_cues"))
    context_cues = _normalize_nonnegative_int(node_hints.get("context_cues"))
    evidence_support_count = _normalize_nonnegative_int(support.get("evidence_support_count"))
    if context_cues == 0 and evidence_support_count > 0:
        context_cues = 1

    matched_keywords = [
        keyword
        for keyword in node_hints.get("matched_keywords", [])
        if isinstance(keyword, str) and keyword
    ]
    matched_keywords = sorted(set([*matched_keywords, *label_matches]))

    workflow_signal_total = workflow_cues + len(label_matches)
    selected_candidate_kind = default_candidate_kind
    if node.get("type") in type_hints:
        selected_candidate_kind = "workflow_script"
    elif (
        workflow_signal_total >= min_workflow_cues
        and context_cues >= min_context_cues
        and evidence_support_count > 0
    ):
        selected_candidate_kind = "workflow_script"

    routing_evidence = {
        "inference_mode": "extraction_derived",
        "selected_candidate_kind": selected_candidate_kind,
        "workflow_cues": workflow_cues,
        "context_cues": context_cues,
        "evidence_support_count": evidence_support_count,
        "matched_keywords": matched_keywords,
    }
    evidence_chunk_ids = [
        chunk_id
        for chunk_id in node_hints.get("evidence_chunk_ids", [])
        if isinstance(chunk_id, str) and chunk_id
    ]
    if evidence_chunk_ids:
        routing_evidence["evidence_chunk_ids"] = evidence_chunk_ids
    return selected_candidate_kind, routing_evidence


def _collect_support(node_id: str, graph: NormalizedGraph) -> dict[str, list[str] | int]:
    supporting_node_ids = []
    supporting_edge_ids = []
    community_ids = []
    evidence_support_count = 0
    for edge in graph.adjacency.get(node_id, []):
        supporting_edge_ids.append(edge["id"])
        other = edge["to"] if edge["from"] == node_id else edge["from"]
        supporting_node_ids.append(other)
        if edge.get("type") == "supported_by_evidence":
            evidence_support_count += 1
    for community in graph.communities.values():
        if node_id in community.get("node_ids", []):
            community_ids.append(community["id"])
    return {
        "supporting_node_ids": sorted(set(supporting_node_ids)),
        "supporting_edge_ids": sorted(set(supporting_edge_ids)),
        "community_ids": sorted(set(community_ids)),
        "evidence_support_count": evidence_support_count,
    }


def _matches_rule(
    rule_when: dict[str, Any],
    *,
    workflow_certainty: str,
    context_certainty: str,
) -> bool:
    for key, expected in rule_when.items():
        actual = {
            "workflow_certainty": workflow_certainty,
            "context_certainty": context_certainty,
        }.get(key)
        if actual != expected:
            return False
    return True


def _slugify(text: str) -> str:
    return (
        text.lower()
        .replace("'", "")
        .replace("/", "-")
        .replace(" ", "-")
    )


def _normalize_nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    return 0
