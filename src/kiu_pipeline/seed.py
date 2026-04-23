from __future__ import annotations

from typing import Any

from .models import CandidateSeed, NormalizedGraph, SourceBundle
from .verification_gate import assess_candidate_seed, summarize_seed_verification


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
DEFAULT_MAX_TRI_STATE_SUPPORT_RATIO_FOR_WORKFLOW = 0.5


def mine_candidate_seeds(
    bundle: SourceBundle,
    graph: NormalizedGraph,
    *,
    drafting_mode: str = "deterministic",
) -> list[CandidateSeed]:
    assessment = mine_candidate_seed_assessment(
        bundle,
        graph,
        drafting_mode=drafting_mode,
    )
    return assessment["accepted"]


def mine_candidate_seed_assessment(
    bundle: SourceBundle,
    graph: NormalizedGraph,
    *,
    drafting_mode: str = "deterministic",
) -> dict[str, Any]:
    seeds = _mine_candidate_seed_candidates(
        bundle,
        graph,
        drafting_mode=drafting_mode,
    )
    accepted: list[CandidateSeed] = []
    rejected: list[dict[str, Any]] = []
    for seed in seeds:
        verification = assess_candidate_seed(
            seed=seed,
            bundle=bundle,
            graph=graph,
        )
        routing_evidence = seed.metadata.setdefault("routing_evidence", {})
        routing_evidence["verification_passed"] = verification["passed"]
        routing_evidence["verification_workflow_ready"] = verification["workflow_ready"]
        routing_evidence["verification_overall_score"] = verification["overall_score"]
        routing_evidence["workflow_promotion_blocked_by_verification"] = False
        if seed.candidate_kind == "workflow_script" and not verification["workflow_ready"]:
            routing_evidence["workflow_promotion_blocked_by_verification"] = True
            routing_evidence["selected_candidate_kind"] = "general_agentic"
            _reapply_candidate_kind_metadata(
                seed=seed,
                bundle=bundle,
                candidate_kind="general_agentic",
            )
        seed.metadata["verification"] = verification
        if verification["passed"]:
            accepted.append(seed)
        else:
            rejected.append(
                {
                    "candidate_id": seed.candidate_id,
                    "candidate_kind": seed.candidate_kind,
                    "disposition": seed.metadata.get("disposition"),
                    "reasons": verification["reasons"],
                    "verification": verification,
                }
            )
    accepted = accepted[: bundle.profile.get("max_candidates", len(accepted))]
    summary = summarize_seed_verification(
        accepted=accepted,
        rejected=rejected,
    )
    return {
        "accepted": accepted,
        "rejected": rejected,
        "summary": summary,
    }


def _reapply_candidate_kind_metadata(
    *,
    seed: CandidateSeed,
    bundle: SourceBundle,
    candidate_kind: str,
) -> None:
    existing_metadata = dict(seed.metadata)
    existing_seed_doc = dict(existing_metadata.get("seed", {}))
    routing_evidence = dict(existing_metadata.get("routing_evidence", {}))
    updated_metadata = derive_candidate_metadata(
        candidate_id=seed.candidate_id,
        seed_node_id=seed.primary_node_id,
        candidate_kind=candidate_kind,
        graph_hash=existing_metadata["source_graph_hash"],
        bundle_id=existing_metadata["source_bundle_id"],
        routing_profile=bundle.profile,
        supporting_node_ids=existing_seed_doc.get("supporting_node_ids", seed.supporting_node_ids),
        supporting_edge_ids=existing_seed_doc.get("supporting_edge_ids", seed.supporting_edge_ids),
        community_ids=existing_seed_doc.get("community_ids", seed.community_ids),
        gold_match_hint=seed.gold_match_hint,
        drafting_mode=existing_metadata.get("drafting_mode", "deterministic"),
        routing_evidence=routing_evidence,
    )
    if "merged_primary_node_ids" in existing_seed_doc:
        updated_metadata["seed"]["merged_primary_node_ids"] = existing_seed_doc["merged_primary_node_ids"]
    if "merged_candidate_count" in existing_seed_doc:
        updated_metadata["seed"]["merged_candidate_count"] = existing_seed_doc["merged_candidate_count"]
    if "verification" in existing_metadata:
        updated_metadata["verification"] = existing_metadata["verification"]
    seed.candidate_kind = candidate_kind
    seed.metadata = updated_metadata


def _mine_candidate_seed_candidates(
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
        support = _collect_support(node["id"], graph)
        candidate_kind, routing_evidence = _resolve_candidate_kind(
            node=node,
            override=override,
            support=support,
            profile=profile,
        )
        base_candidate_id = (
            override.get("candidate_id")
            or node.get("candidate_id")
            or override.get("gold_match_hint")
            or _slugify(node["label"])
        )
        base_seed_content = override.get("skill_seed") or node.get("skill_seed", {})
        for spec in _resolve_candidate_specs(
            bundle=bundle,
            node=node,
            override=override,
            base_candidate_id=base_candidate_id,
            base_candidate_kind=candidate_kind,
            base_seed_content=base_seed_content,
            routing_evidence=routing_evidence,
        ):
            gold_match_hint = spec.get("gold_match_hint")
            source_skill = _resolve_source_skill(
                bundle=bundle,
                candidate_id=spec["candidate_id"],
                gold_match_hint=gold_match_hint,
            )
            metadata = derive_candidate_metadata(
                candidate_id=spec["candidate_id"],
                seed_node_id=node["id"],
                candidate_kind=spec["candidate_kind"],
                graph_hash=bundle.manifest["graph"]["graph_hash"],
                bundle_id=bundle.manifest["bundle_id"],
                routing_profile=profile,
                supporting_node_ids=support["supporting_node_ids"],
                supporting_edge_ids=support["supporting_edge_ids"],
                community_ids=support["community_ids"],
                gold_match_hint=gold_match_hint,
                drafting_mode=drafting_mode,
                routing_evidence=spec["routing_evidence"],
            )
            if spec.get("derived_from_candidate_id"):
                metadata["seed"]["derived_from_candidate_id"] = spec["derived_from_candidate_id"]
                metadata["seed"]["derivation_mode"] = spec.get(
                    "derivation_mode",
                    "additional_candidate",
                )
            score = _candidate_seed_score(
                seed_content=spec["seed_content"],
                source_skill=source_skill,
                support=support,
                routing_evidence=spec["routing_evidence"],
            )
            seeds.append(
                CandidateSeed(
                    candidate_id=metadata["candidate_id"],
                    candidate_kind=spec["candidate_kind"],
                    primary_node_id=node["id"],
                    supporting_node_ids=support["supporting_node_ids"],
                    supporting_edge_ids=support["supporting_edge_ids"],
                    community_ids=support["community_ids"],
                    gold_match_hint=gold_match_hint,
                    source_skill=source_skill,
                    score=score,
                    metadata=metadata,
                    seed_content=spec["seed_content"],
                )
            )
    merged_seeds = _merge_duplicate_candidate_seeds(
        bundle=bundle,
        seeds=seeds,
    )
    merged_seeds.sort(key=lambda seed: (-seed.score, seed.candidate_id))
    return merged_seeds


def _resolve_candidate_specs(
    *,
    bundle: SourceBundle,
    node: dict[str, Any],
    override: dict[str, Any],
    base_candidate_id: str,
    base_candidate_kind: str,
    base_seed_content: dict[str, Any],
    routing_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    specs = [
        {
            "candidate_id": base_candidate_id,
            "candidate_kind": base_candidate_kind,
            "gold_match_hint": override.get("gold_match_hint"),
            "seed_content": base_seed_content,
            "routing_evidence": dict(routing_evidence),
        }
    ]
    additional_candidate_docs = []
    node_seed_content = node.get("skill_seed", {})
    if isinstance(node_seed_content, dict):
        additional_candidate_docs.extend(
            item
            for item in node_seed_content.get("additional_candidates", [])
            if isinstance(item, dict)
        )
    additional_candidate_docs.extend(
        item
        for item in override.get("additional_candidates", [])
        if isinstance(item, dict)
    )
    for item in additional_candidate_docs:
        candidate_id = item.get("candidate_id") or item.get("gold_match_hint")
        if not isinstance(candidate_id, str) or not candidate_id:
            continue
        candidate_kind = item.get("candidate_kind") or base_candidate_kind
        if not isinstance(candidate_kind, str) or not candidate_kind:
            candidate_kind = base_candidate_kind
        derived_seed_content = _build_additional_seed_content(
            item=item,
            candidate_id=candidate_id,
            fallback_seed_content=base_seed_content,
        )
        derived_routing_evidence = dict(routing_evidence)
        derived_routing_evidence["derivation_mode"] = "additional_candidate"
        derived_routing_evidence["derived_from_candidate_id"] = base_candidate_id
        derived_routing_evidence["selected_candidate_kind"] = candidate_kind
        specs.append(
            {
                "candidate_id": candidate_id,
                "candidate_kind": candidate_kind,
                "gold_match_hint": item.get("gold_match_hint"),
                "seed_content": derived_seed_content,
                "routing_evidence": derived_routing_evidence,
                "derived_from_candidate_id": base_candidate_id,
                "derivation_mode": "additional_candidate",
            }
        )
    return specs


def _build_additional_seed_content(
    *,
    item: dict[str, Any],
    candidate_id: str,
    fallback_seed_content: dict[str, Any],
) -> dict[str, Any]:
    skill_seed = item.get("skill_seed")
    if isinstance(skill_seed, dict) and skill_seed:
        return dict(skill_seed)

    derived = dict(fallback_seed_content) if isinstance(fallback_seed_content, dict) else {}
    for key in (
        "title",
        "contract",
        "relations",
        "rationale",
        "evidence_summary",
        "trace_refs",
        "usage_notes",
        "scenario_families",
        "source_anchor_sets",
        "eval_summary",
        "revision_seed",
    ):
        if key in item:
            derived[key] = item[key]
    derived["title"] = derived.get("title") or _titleize(candidate_id)
    return derived


def _resolve_source_skill(
    *,
    bundle: SourceBundle,
    candidate_id: str,
    gold_match_hint: str | None,
):
    if gold_match_hint and gold_match_hint in bundle.skills:
        return bundle.skills[gold_match_hint]
    return bundle.skills.get(candidate_id)


def _candidate_seed_score(
    *,
    seed_content: dict[str, Any],
    source_skill: Any,
    support: dict[str, list[str] | int],
    routing_evidence: dict[str, Any],
) -> int:
    trace_ref_count = (
        len(source_skill.trace_refs)
        if source_skill
        else len(
            [
                item
                for item in seed_content.get("trace_refs", [])
                if isinstance(item, str) and item
            ]
        )
    )
    return trace_ref_count + len(support["supporting_edge_ids"]) + len(
        support["community_ids"]
    ) + int(routing_evidence.get("workflow_cues", 0) or 0)


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
    max_tri_state_support_ratio = workflow_script_doc.get(
        "max_tri_state_support_ratio_for_workflow",
        DEFAULT_MAX_TRI_STATE_SUPPORT_RATIO_FOR_WORKFLOW,
    )
    if not isinstance(max_tri_state_support_ratio, (int, float)):
        max_tri_state_support_ratio = DEFAULT_MAX_TRI_STATE_SUPPORT_RATIO_FOR_WORKFLOW
    max_tri_state_support_ratio = min(max(float(max_tri_state_support_ratio), 0.0), 1.0)

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
    extracted_evidence_support_count = _normalize_nonnegative_int(
        support.get("extracted_evidence_support_count")
    )
    tri_state_support_count = _normalize_nonnegative_int(support.get("tri_state_support_count"))
    support_entity_count = _normalize_nonnegative_int(support.get("support_entity_count"))
    tri_state_support_ratio = _safe_ratio(tri_state_support_count, support_entity_count)
    if context_cues == 0 and extracted_evidence_support_count > 0:
        context_cues = 1

    matched_keywords = [
        keyword
        for keyword in node_hints.get("matched_keywords", [])
        if isinstance(keyword, str) and keyword
    ]
    matched_keywords = sorted(set([*matched_keywords, *label_matches]))
    matched_keyword_count = len(matched_keywords)

    workflow_signal_total = workflow_cues + len(label_matches)
    has_multi_signal_workflow_hint = matched_keyword_count >= 2
    workflow_requires_multi_signal = (
        workflow_signal_total >= max(min_workflow_cues, 2)
        and (
            context_cues >= max(min_context_cues, 2)
            or has_multi_signal_workflow_hint
        )
        and (
            extracted_evidence_support_count >= 2
            or has_multi_signal_workflow_hint
        )
    )
    workflow_promotion_blocked_by_evidence = (
        tri_state_support_ratio > max_tri_state_support_ratio
        and tri_state_support_count > extracted_evidence_support_count
    )
    selected_candidate_kind = default_candidate_kind
    if (
        node.get("type") in type_hints
        and workflow_requires_multi_signal
        and not workflow_promotion_blocked_by_evidence
    ):
        selected_candidate_kind = "workflow_script"
    elif (
        workflow_requires_multi_signal
        and extracted_evidence_support_count > 0
        and not workflow_promotion_blocked_by_evidence
    ):
        selected_candidate_kind = "workflow_script"

    routing_evidence = {
        "inference_mode": "extraction_derived",
        "selected_candidate_kind": selected_candidate_kind,
        "workflow_cues": workflow_cues,
        "workflow_signal_total": workflow_signal_total,
        "context_cues": context_cues,
        "evidence_support_count": evidence_support_count,
        "extracted_evidence_support_count": extracted_evidence_support_count,
        "tri_state_support_count": tri_state_support_count,
        "support_entity_count": support_entity_count,
        "tri_state_support_ratio": tri_state_support_ratio,
        "ambiguous_support_node_count": _normalize_nonnegative_int(
            support.get("ambiguous_support_node_count")
        ),
        "inferred_support_node_count": _normalize_nonnegative_int(
            support.get("inferred_support_node_count")
        ),
        "ambiguous_support_edge_count": _normalize_nonnegative_int(
            support.get("ambiguous_support_edge_count")
        ),
        "inferred_support_edge_count": _normalize_nonnegative_int(
            support.get("inferred_support_edge_count")
        ),
        "workflow_promotion_blocked_by_evidence": workflow_promotion_blocked_by_evidence,
        "workflow_requires_multi_signal": workflow_requires_multi_signal,
        "has_multi_signal_workflow_hint": has_multi_signal_workflow_hint,
        "matched_keyword_count": matched_keyword_count,
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
    extracted_evidence_support_count = 0
    ambiguous_support_node_ids: set[str] = set()
    inferred_support_node_ids: set[str] = set()
    ambiguous_support_edge_ids: set[str] = set()
    inferred_support_edge_ids: set[str] = set()
    extracted_support_edge_ids: set[str] = set()
    for edge in graph.adjacency.get(node_id, []):
        supporting_edge_ids.append(edge["id"])
        other = edge["to"] if edge["from"] == node_id else edge["from"]
        supporting_node_ids.append(other)
        edge_kind = edge.get("extraction_kind")
        if edge_kind == "AMBIGUOUS":
            ambiguous_support_edge_ids.add(edge["id"])
        elif edge_kind == "INFERRED":
            inferred_support_edge_ids.add(edge["id"])
        elif edge_kind == "EXTRACTED":
            extracted_support_edge_ids.add(edge["id"])
        if edge.get("type") == "supported_by_evidence":
            evidence_support_count += 1
            if edge_kind == "EXTRACTED":
                extracted_evidence_support_count += 1
        other_node = graph.nodes.get(other, {})
        node_kind = other_node.get("extraction_kind")
        if node_kind == "AMBIGUOUS":
            ambiguous_support_node_ids.add(other)
        elif node_kind == "INFERRED":
            inferred_support_node_ids.add(other)
    for community in graph.communities.values():
        if node_id in community.get("node_ids", []):
            community_ids.append(community["id"])
    unique_node_ids = sorted(set(supporting_node_ids))
    unique_edge_ids = sorted(set(supporting_edge_ids))
    tri_state_support_count = (
        len(ambiguous_support_node_ids)
        + len(inferred_support_node_ids)
        + len(ambiguous_support_edge_ids)
        + len(inferred_support_edge_ids)
    )
    support_entity_count = len(unique_node_ids) + len(unique_edge_ids)
    return {
        "supporting_node_ids": unique_node_ids,
        "supporting_edge_ids": unique_edge_ids,
        "community_ids": sorted(set(community_ids)),
        "evidence_support_count": evidence_support_count,
        "extracted_evidence_support_count": extracted_evidence_support_count,
        "ambiguous_support_node_count": len(ambiguous_support_node_ids),
        "inferred_support_node_count": len(inferred_support_node_ids),
        "ambiguous_support_edge_count": len(ambiguous_support_edge_ids),
        "inferred_support_edge_count": len(inferred_support_edge_ids),
        "extracted_support_edge_count": len(extracted_support_edge_ids),
        "tri_state_support_count": tri_state_support_count,
        "support_entity_count": support_entity_count,
    }


def _merge_duplicate_candidate_seeds(
    *,
    bundle: SourceBundle,
    seeds: list[CandidateSeed],
) -> list[CandidateSeed]:
    grouped: dict[str, list[CandidateSeed]] = {}
    for seed in seeds:
        grouped.setdefault(seed.candidate_id, []).append(seed)

    merged_seeds: list[CandidateSeed] = []
    for group in grouped.values():
        if len(group) == 1:
            merged_seeds.append(group[0])
            continue
        merged_seeds.append(_merge_seed_group(bundle=bundle, group=group))
    return merged_seeds


def _merge_seed_group(
    *,
    bundle: SourceBundle,
    group: list[CandidateSeed],
) -> CandidateSeed:
    candidate_kind = _select_merged_candidate_kind(group)
    primary_seed = _select_primary_seed(group, candidate_kind=candidate_kind)
    merged_primary_node_ids = sorted({seed.primary_node_id for seed in group})
    supporting_node_ids = sorted(
        {
            node_id
            for seed in group
            for node_id in [*seed.supporting_node_ids, seed.primary_node_id]
            if node_id != primary_seed.primary_node_id
        }
    )
    supporting_edge_ids = sorted(
        {
            edge_id
            for seed in group
            for edge_id in seed.supporting_edge_ids
        }
    )
    community_ids = sorted(
        {
            community_id
            for seed in group
            for community_id in seed.community_ids
        }
    )
    source_skill = next((seed.source_skill for seed in group if seed.source_skill), None)
    gold_match_hint = next((seed.gold_match_hint for seed in group if seed.gold_match_hint), None)
    routing_evidence = _merge_routing_evidence(group, candidate_kind=candidate_kind)
    metadata = derive_candidate_metadata(
        candidate_id=primary_seed.candidate_id,
        seed_node_id=primary_seed.primary_node_id,
        candidate_kind=candidate_kind,
        graph_hash=bundle.manifest["graph"]["graph_hash"],
        bundle_id=bundle.manifest["bundle_id"],
        routing_profile=bundle.profile,
        supporting_node_ids=supporting_node_ids,
        supporting_edge_ids=supporting_edge_ids,
        community_ids=community_ids,
        gold_match_hint=gold_match_hint,
        drafting_mode=primary_seed.metadata.get("drafting_mode", "deterministic"),
        routing_evidence=routing_evidence,
    )
    metadata["seed"]["merged_primary_node_ids"] = merged_primary_node_ids
    metadata["seed"]["merged_candidate_count"] = len(group)

    score = (
        len(source_skill.trace_refs) if source_skill else 0
    ) + len(supporting_edge_ids) + len(community_ids) + int(
        routing_evidence.get("workflow_cues", 0) or 0
    )
    return CandidateSeed(
        candidate_id=primary_seed.candidate_id,
        candidate_kind=candidate_kind,
        primary_node_id=primary_seed.primary_node_id,
        supporting_node_ids=supporting_node_ids,
        supporting_edge_ids=supporting_edge_ids,
        community_ids=community_ids,
        gold_match_hint=gold_match_hint,
        source_skill=source_skill,
        score=score,
        metadata=metadata,
        seed_content=_merge_seed_content(group, preferred=primary_seed),
    )


def _select_merged_candidate_kind(group: list[CandidateSeed]) -> str:
    if any(
        seed.candidate_kind == "workflow_script"
        or seed.metadata.get("disposition") == "workflow_script_candidate"
        for seed in group
    ):
        return "workflow_script"
    return max(group, key=lambda seed: seed.score).candidate_kind


def _select_primary_seed(
    group: list[CandidateSeed],
    *,
    candidate_kind: str,
) -> CandidateSeed:
    prefer_workflow = candidate_kind == "workflow_script"
    return min(
        group,
        key=lambda seed: (
            0
            if prefer_workflow
            and (
                seed.candidate_kind == "workflow_script"
                or seed.metadata.get("disposition") == "workflow_script_candidate"
            )
            else 1,
            -seed.score,
            0 if seed.source_skill else 1,
            seed.primary_node_id,
        ),
    )


def _merge_routing_evidence(
    group: list[CandidateSeed],
    *,
    candidate_kind: str,
) -> dict[str, Any]:
    routing_docs = [
        doc
        for seed in group
        if isinstance(seed.metadata.get("routing_evidence"), dict)
        for doc in [seed.metadata["routing_evidence"]]
    ]
    if not routing_docs:
        return {
            "inference_mode": "merged_seed_support",
            "selected_candidate_kind": candidate_kind,
            "merged_from_node_ids": sorted({seed.primary_node_id for seed in group}),
        }

    merged = {
        "inference_mode": "merged_seed_support",
        "selected_candidate_kind": candidate_kind,
        "workflow_cues": max(
            _normalize_nonnegative_int(doc.get("workflow_cues")) for doc in routing_docs
        ),
        "context_cues": max(
            _normalize_nonnegative_int(doc.get("context_cues")) for doc in routing_docs
        ),
        "evidence_support_count": sum(
            _normalize_nonnegative_int(doc.get("evidence_support_count")) for doc in routing_docs
        ),
        "extracted_evidence_support_count": sum(
            _normalize_nonnegative_int(doc.get("extracted_evidence_support_count"))
            for doc in routing_docs
        ),
        "tri_state_support_count": sum(
            _normalize_nonnegative_int(doc.get("tri_state_support_count")) for doc in routing_docs
        ),
        "support_entity_count": sum(
            _normalize_nonnegative_int(doc.get("support_entity_count")) for doc in routing_docs
        ),
        "ambiguous_support_node_count": sum(
            _normalize_nonnegative_int(doc.get("ambiguous_support_node_count"))
            for doc in routing_docs
        ),
        "inferred_support_node_count": sum(
            _normalize_nonnegative_int(doc.get("inferred_support_node_count"))
            for doc in routing_docs
        ),
        "ambiguous_support_edge_count": sum(
            _normalize_nonnegative_int(doc.get("ambiguous_support_edge_count"))
            for doc in routing_docs
        ),
        "inferred_support_edge_count": sum(
            _normalize_nonnegative_int(doc.get("inferred_support_edge_count"))
            for doc in routing_docs
        ),
        "merged_from_node_ids": sorted({seed.primary_node_id for seed in group}),
        "workflow_promotion_blocked_by_evidence": any(
            bool(doc.get("workflow_promotion_blocked_by_evidence")) for doc in routing_docs
        ),
    }
    merged["tri_state_support_ratio"] = _safe_ratio(
        merged["tri_state_support_count"],
        merged["support_entity_count"],
    )
    matched_keywords = sorted(
        {
            keyword
            for doc in routing_docs
            for keyword in doc.get("matched_keywords", [])
            if isinstance(keyword, str) and keyword
        }
    )
    if matched_keywords:
        merged["matched_keywords"] = matched_keywords
    evidence_chunk_ids = sorted(
        {
            chunk_id
            for doc in routing_docs
            for chunk_id in doc.get("evidence_chunk_ids", [])
            if isinstance(chunk_id, str) and chunk_id
        }
    )
    if evidence_chunk_ids:
        merged["evidence_chunk_ids"] = evidence_chunk_ids
    return merged


def _merge_seed_content(
    group: list[CandidateSeed],
    *,
    preferred: CandidateSeed,
) -> dict[str, Any]:
    if preferred.seed_content:
        return preferred.seed_content
    for seed in group:
        if seed.seed_content:
            return seed.seed_content
    return {}


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


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)
