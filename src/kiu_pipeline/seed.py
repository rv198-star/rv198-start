from __future__ import annotations

from typing import Any

from .models import CandidateSeed, NormalizedGraph, SourceBundle


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
        candidate_kind = override.get("candidate_kind", "general_agentic")
        gold_match_hint = override.get("gold_match_hint")
        source_skill = bundle.skills.get(gold_match_hint) if gold_match_hint else None
        support = _collect_support(node["id"], graph)
        metadata = derive_candidate_metadata(
            candidate_id=gold_match_hint or _slugify(node["label"]),
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
        )
        score = (
            len(source_skill.trace_refs) if source_skill else 0
        ) + len(support["supporting_edge_ids"]) + len(support["community_ids"])
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

    return {
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
    }


def _collect_support(node_id: str, graph: NormalizedGraph) -> dict[str, list[str]]:
    supporting_node_ids = []
    supporting_edge_ids = []
    community_ids = []
    for edge in graph.adjacency.get(node_id, []):
        supporting_edge_ids.append(edge["id"])
        other = edge["to"] if edge["from"] == node_id else edge["from"]
        supporting_node_ids.append(other)
    for community in graph.communities.values():
        if node_id in community.get("node_ids", []):
            community_ids.append(community["id"])
    return {
        "supporting_node_ids": sorted(set(supporting_node_ids)),
        "supporting_edge_ids": sorted(set(supporting_edge_ids)),
        "community_ids": sorted(set(community_ids)),
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
