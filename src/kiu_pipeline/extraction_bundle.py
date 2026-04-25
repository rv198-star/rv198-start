from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from kiu_graph.clustering import derive_graph_communities
from kiu_graph.migrate import canonical_graph_hash

from .contracts import build_semantic_contract, identify_semantic_family


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_NODE_TYPES = [
    "principle_signal",
    "control_signal",
    "counter_example_signal",
    "narrative_pattern_signal",
    "case_mechanism",
    "situation_strategy_pattern",
]
BORROWED_VALUE_FAMILIES = {
    "historical-analogy-transfer-gate",
    "no-investigation-no-decision",
    "principal-contradiction-focus",
}
DEFAULT_CANDIDATE_KINDS = {
    "general_agentic": {
        "workflow_certainty": "medium",
        "context_certainty": "high",
    },
    "workflow_script": {
        "workflow_certainty": "high",
        "context_certainty": "high",
    },
}
DEFAULT_ROUTING_RULES = [
    {
        "when": {
            "workflow_certainty": "high",
            "context_certainty": "high",
        },
        "recommended_execution_mode": "workflow_script",
        "disposition": "workflow_script_candidate",
    },
    {
        "when": {
            "workflow_certainty": "medium",
            "context_certainty": "high",
        },
        "recommended_execution_mode": "llm_agentic",
        "disposition": "skill_candidate",
    },
]


def _is_borrowed_value_family(semantic_family: str) -> bool:
    return semantic_family in BORROWED_VALUE_FAMILIES


def _borrowed_value_profile(semantic_family: str) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {
        "historical-analogy-transfer-gate": {
            "source_pattern": "historical case mechanism",
            "trigger": "the user wants to borrow a historical, biographical, or case pattern for a current decision",
            "verdicts": "transfer / partial_transfer / do_not_transfer / ask_more_context",
            "output": "mechanism_mapping, transfer_conditions, anti_conditions, abuse_check, and transfer_checked_next_action",
            "positive_signals": ["历史案例能不能借鉴", "这个故事像不像我们的处境", "机制是否相同"],
            "negative_signals": ["讲讲这段历史", "翻译一下", "人物介绍", "单个故事成功所以照做"],
            "transfer_conditions": [
                "current_decision_is_explicit",
                "actor_incentive_constraint_outcome_chain_matches",
                "material_differences_are_named",
            ],
            "anti_conditions": [
                "single_case_overreach",
                "surface_similarity_only",
                "pure_history_query_or_translation",
            ],
        },
        "no-investigation-no-decision": {
            "source_pattern": "investigation-before-judgment strategy",
            "trigger": "the user is about to decide from reports, templates, book claims, or past experience without field evidence",
            "verdicts": "go_investigate / partial_judgment / do_not_decide",
            "output": "investigation_questions, transfer_conditions, anti_conditions, abuse_check, and field_evidence_next_action",
            "positive_signals": ["没有现场事实", "只看报告要拍板", "照搬过去经验", "先决定再补材料"],
            "negative_signals": ["作者原话是什么", "总结这篇文章", "人物介绍", "评价立场但没有我的决策"],
            "transfer_conditions": [
                "current_decision_is_explicit",
                "field_evidence_can_change_the_decision",
                "investigation_questions_are_actionable_before_commitment",
            ],
            "anti_conditions": [
                "context_transfer_abuse",
                "pure_author_position_query",
                "decision_window_already_closed",
            ],
        },
        "principal-contradiction-focus": {
            "source_pattern": "principal-contradiction focus strategy",
            "trigger": "the user faces multiple conflicts or fronts and must choose the main constraint before allocating action",
            "verdicts": "focus_here / split_after_focus / ask_more_context / do_not_apply",
            "output": "principal_contradiction, transfer_conditions, anti_conditions, abuse_check, and focused_action_program",
            "positive_signals": ["矛盾太多", "平均用力", "先抓哪个问题", "资源分散"],
            "negative_signals": ["总结主要矛盾理论", "评价作者立场", "单纯政治评论", "没有当前行动选择"],
            "transfer_conditions": [
                "multiple_conflicts_are_named",
                "one_constraint_materially_controls_the_next_action",
                "resource_allocation_changes_after_focus",
            ],
            "anti_conditions": [
                "context_transfer_abuse",
                "stance_commentary_without_user_decision",
                "all_conflicts_are_independent_and_need_parallel_workflows",
            ],
        },
    }
    return profiles[semantic_family]


def scaffold_extraction_bundle(
    *,
    source_chunks_path: str | Path,
    graph_path: str | Path,
    output_root: str | Path,
    inherits_from: str = "default",
    title: str | None = None,
) -> Path:
    source_chunks_input_path = Path(source_chunks_path)
    output_root = Path(output_root)

    source_chunks_doc = json.loads(source_chunks_input_path.read_text(encoding="utf-8"))
    graph_doc = json.loads(Path(graph_path).read_text(encoding="utf-8"))

    source_id = str(source_chunks_doc["source_id"])
    bundle_root = output_root / "bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)

    (bundle_root / "graph").mkdir(parents=True, exist_ok=True)
    (bundle_root / "sources").mkdir(parents=True, exist_ok=True)
    (bundle_root / "ingestion").mkdir(parents=True, exist_ok=True)
    (bundle_root / "skills").mkdir(parents=True, exist_ok=True)
    (bundle_root / "traces" / "canonical").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "real_decisions").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "synthetic_adversarial").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "out_of_distribution").mkdir(parents=True, exist_ok=True)

    source_file_map, copied_source_root = _copy_source_files(
        source_chunks_doc=source_chunks_doc,
        source_chunks_path=source_chunks_input_path,
        bundle_root=bundle_root,
        source_id=source_id,
    )

    persisted_source_chunks = _rewrite_source_chunks_doc(
        source_chunks_doc=source_chunks_doc,
        source_file_map=source_file_map,
        copied_source_root=copied_source_root,
    )
    (bundle_root / "ingestion" / "source-chunks-v0.1.json").write_text(
        json.dumps(persisted_source_chunks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rewritten_graph_doc = _rewrite_graph_source_paths(
        graph_doc=graph_doc,
        source_snapshot=source_id,
        source_file_map=source_file_map,
    )
    if not rewritten_graph_doc.get("communities"):
        rewritten_graph_doc["communities"] = derive_graph_communities(rewritten_graph_doc)

    skill_seed_specs = _hydrate_graph_with_skill_seeds(
        bundle_root=bundle_root,
        graph_doc=rewritten_graph_doc,
    )

    graph_hash = canonical_graph_hash(rewritten_graph_doc)
    rewritten_graph_doc["graph_hash"] = graph_hash
    (bundle_root / "graph" / "graph.json").write_text(
        json.dumps(rewritten_graph_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "bundle_id": f"{source_id}-source-v0.6",
        "title": title or _humanize_title(source_id),
        "bundle_version": "0.6.0-dev",
        "schema_version": "kiu.bundle.schema/v0.1",
        "skill_spec_version": "kiu.skill-spec/v0.6",
        "relation_enum_version": "kiu.relation-enum/v1",
        "language": source_chunks_doc.get("language", "zh-CN"),
        "domain": inherits_from,
        "created_at": date.today().isoformat(),
        "graph": {
            "path": "graph/graph.json",
            "graph_version": rewritten_graph_doc["graph_version"],
            "graph_hash": graph_hash,
        },
        "skills": [],
        "shared_assets": {
            "traces": "traces",
            "evaluation": "evaluation",
            "sources": "sources",
        },
    }
    _write_yaml(bundle_root / "manifest.yaml", manifest)
    _write_yaml(
        bundle_root / "automation.yaml",
        {
            "profile_version": "kiu.pipeline-profile/v0.3",
            "source_bundle_id": manifest["bundle_id"],
            "inherits_from": inherits_from,
            "trigger_registry": "triggers.yaml",
            "seed_node_types": DEFAULT_SEED_NODE_TYPES,
            "max_candidates": 14,
            "candidate_kinds": DEFAULT_CANDIDATE_KINDS,
            "routing_rules": DEFAULT_ROUTING_RULES,
        },
    )
    _write_yaml(
        bundle_root / "materials.yaml",
        {
            "source_id": source_id,
            "materials": [
                {
                    "source_id": source_id,
                    "kind": "markdown_document" if len(source_file_map) == 1 else "markdown_collection",
                    "original_path": str(source_chunks_doc.get("source_file")),
                    "bundle_path": copied_source_root,
                    "file_count": len(source_file_map),
                    "source_chunks_path": "ingestion/source-chunks-v0.1.json",
                    "chunk_count": len(source_chunks_doc.get("chunks", [])),
                }
            ],
        },
    )
    _write_yaml(
        bundle_root / "triggers.yaml",
        _build_trigger_registry(skill_seed_specs),
    )
    return bundle_root


def _hydrate_graph_with_skill_seeds(
    *,
    bundle_root: Path,
    graph_doc: dict[str, Any],
) -> list[dict[str, Any]]:
    node_map = {
        node["id"]: node
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    adjacency = _build_adjacency(graph_doc.get("edges", []))
    seed_specs: list[dict[str, Any]] = []

    for node in graph_doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("type") not in DEFAULT_SEED_NODE_TYPES:
            continue
        candidate_id = _derive_candidate_id(node)
        title = _humanize_title(candidate_id)
        descriptors = _collect_descriptors(
            bundle_root=bundle_root,
            node=node,
            node_map=node_map,
            adjacency=adjacency,
            candidate_id=candidate_id,
        )
        contract = _build_seed_contract(
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
        )
        trace_ref = _write_trace_doc(
            bundle_root=bundle_root,
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
        )
        eval_summary = _write_eval_docs(
            bundle_root=bundle_root,
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
            contract=contract,
        )
        usage_notes = _build_usage_notes(
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
        )
        scenario_families = _build_scenario_families(
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
        )
        skill_seed = _compose_skill_seed(
            candidate_id=candidate_id,
            title=title,
            contract=contract,
            descriptors=descriptors,
            trace_ref=trace_ref,
            usage_notes=usage_notes,
            scenario_families=scenario_families,
            eval_summary=eval_summary,
        )
        additional_candidates = _build_additional_candidate_specs(
            bundle_root=bundle_root,
            candidate_id=candidate_id,
            descriptors=descriptors,
        )
        if additional_candidates:
            skill_seed["additional_candidates"] = additional_candidates
            companion_ids = [
                item["candidate_id"]
                for item in additional_candidates
                if isinstance(item.get("candidate_id"), str) and item.get("candidate_id")
            ]
            if companion_ids:
                skill_seed["relations"]["depends_on"] = sorted(set(companion_ids))
        node["candidate_id"] = candidate_id
        node["skill_seed"] = skill_seed
        seed_specs.append(
            {
                "candidate_id": candidate_id,
                "title": title,
                "contract": contract,
            }
        )
        for additional in additional_candidates:
            additional_seed = additional.get("skill_seed", {})
            additional_contract = (
                additional_seed.get("contract", {})
                if isinstance(additional_seed, dict)
                else {}
            )
            if not additional_contract:
                continue
            seed_specs.append(
                {
                    "candidate_id": additional["candidate_id"],
                    "title": additional_seed.get(
                        "title",
                        _humanize_title(additional["candidate_id"]),
                    ),
                    "contract": additional_contract,
                }
            )
    return seed_specs


def _rewrite_graph_source_paths(
    *,
    graph_doc: dict[str, Any],
    source_snapshot: str,
    source_file_map: dict[str, str],
) -> dict[str, Any]:
    rewritten = dict(graph_doc)
    rewritten["source_snapshot"] = source_snapshot
    rewritten["nodes"] = [
        _rewrite_source_file(entity=node, source_file_map=source_file_map)
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict)
    ]
    rewritten["edges"] = [
        _rewrite_source_file(entity=edge, source_file_map=source_file_map)
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict)
    ]
    rewritten["communities"] = [
        dict(community)
        for community in graph_doc.get("communities", [])
        if isinstance(community, dict)
    ]
    rewritten.pop("graph_hash", None)
    return rewritten


def _compose_skill_seed(
    *,
    candidate_id: str,
    title: str,
    contract: dict[str, Any],
    descriptors: list[dict[str, str]],
    trace_ref: str,
    usage_notes: list[str],
    scenario_families: dict[str, Any],
    eval_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "title": title,
        "contract": contract,
        "relations": {
            "depends_on": [],
            "delegates_to": [],
            "constrained_by": [],
            "complements": [],
            "contradicts": [],
        },
        "rationale": _build_seed_rationale(
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
            contract=contract,
        ),
        "evidence_summary": _build_seed_evidence_summary(
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
        ),
        "trace_refs": [trace_ref],
        "usage_notes": usage_notes,
        "scenario_families": scenario_families,
        "eval_summary": eval_summary,
        "revision_seed": _build_revision_seed(
            candidate_id=candidate_id,
            title=title,
        ),
    }


def _build_additional_candidate_specs(
    *,
    bundle_root: Path,
    candidate_id: str,
    descriptors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    semantic_family = identify_semantic_family(candidate_id)
    if semantic_family == "margin-of-safety-sizing":
        value_candidate_id = _derive_related_candidate_id(
            base_candidate_id=candidate_id,
            semantic_root="value-assessment",
        )
        value_title = _humanize_title(value_candidate_id)
        value_contract = _build_seed_contract(
            candidate_id=value_candidate_id,
            title=value_title,
            descriptors=descriptors,
        )
        value_trace_ref = _write_trace_doc(
            bundle_root=bundle_root,
            candidate_id=value_candidate_id,
            title=value_title,
            descriptors=descriptors,
        )
        value_eval_summary = _write_eval_docs(
            bundle_root=bundle_root,
            candidate_id=value_candidate_id,
            title=value_title,
            descriptors=descriptors,
            contract=value_contract,
        )
        value_usage_notes = _build_usage_notes(
            candidate_id=value_candidate_id,
            title=value_title,
            descriptors=descriptors,
        )
        value_scenario_families = _build_scenario_families(
            candidate_id=value_candidate_id,
            title=value_title,
            descriptors=descriptors,
        )
        value_skill_seed = _compose_skill_seed(
            candidate_id=value_candidate_id,
            title=value_title,
            contract=value_contract,
            descriptors=descriptors,
            trace_ref=value_trace_ref,
            usage_notes=value_usage_notes,
            scenario_families=value_scenario_families,
            eval_summary=value_eval_summary,
        )
        value_skill_seed["relations"]["delegates_to"] = [candidate_id]
        return [
            {
                "candidate_id": value_candidate_id,
                "candidate_kind": "general_agentic",
                "skill_seed": value_skill_seed,
            }
        ]

    return _build_requirements_agentic_candidate_specs(
        bundle_root=bundle_root,
        source_candidate_id=candidate_id,
        descriptors=descriptors,
    )


def _build_requirements_agentic_candidate_specs(
    *,
    bundle_root: Path,
    source_candidate_id: str,
    descriptors: list[dict[str, str]],
) -> list[dict[str, Any]]:
    requirement_specs = {
        "2-日常需求分析": {
            "candidate_id": "solution-to-problem-reframing",
            "title": "Solution To Problem Reframing",
            "trigger_patterns": [
                "solution_level_request_with_unclear_problem",
                "stakeholder_requests_feature_but_business_impact_unknown",
                "implementation_cost_debate_before_problem_recovery",
            ],
            "trigger_exclusions": [
                "workflow_execution_request_only",
                "problem_already_validated_and_solution_selected",
                "concept_query_only",
            ],
            "intake": [
                ("proposed_solution", "string", "用户或客户已经提出的功能、页面、报表或实现方案。"),
                ("requester_and_user", "structured", "区分需求提出者、真实使用者、受影响者是否一致。"),
                ("business_impact_if_absent", "list[string]", "如果不做该方案，业务问题、风险或机会损失是什么。"),
                ("current_workaround", "string", "当前临时解决方式及其代价。"),
                ("disconfirming_evidence", "list[string]", "能证明该方案只是表层表达、问题尚未澄清或价值不足的证据。"),
            ],
            "schema": {
                "verdict": "enum[reframe_to_problem|accept_solution_with_constraints|defer]",
                "problem_level_need": "string",
                "solution_risk": "list[string]",
                "evidence_to_check": "list[string]",
                "next_question": "string",
                "decline_reason": "string",
                "confidence": "enum[low|medium|high]",
            },
            "fails_when": [
                "problem_level_need_cannot_be_recovered",
                "requester_and_real_user_conflict_unresolved",
            ],
            "do_not_fire_when": [
                "workflow_execution_request_only",
                "problem_already_validated_and_solution_selected",
            ],
            "rationale_tail": (
                "This candidate is intentionally not a workflow wrapper. It fires when the input requires reconstructing the real problem behind a proposed solution, judging whether the requester's wording is reliable, and deciding whether to reframe, accept with constraints, or defer. The underlying chapter still provides deterministic restore/complement/evaluate workflows, but this skill handles the judgment boundary before those workflows are chosen."
            ),
            "usage_notes": [
                "当用户拿着一个明确方案来问要不要做时，先恢复问题级需求，而不是直接细化 How。",
                "输出必须区分 proposed_solution、problem_level_need、solution_risk 和 next_question。",
                "如果问题已验证且只是要执行固定模板，应路由到 workflow_candidates/2-日常需求分析，而不是触发本 skill。",
                "如果真实用户与需求提出者不一致，必须显式标出需要补访谈或补证据。",
            ],
            "scenarios": {
                "should_trigger": [
                    {
                        "scenario_id": "feature-request-before-problem",
                        "summary": "客户要求加一个具体功能，但业务影响、真实使用者和替代方案都不清楚。",
                        "prompt_signals": ["客户说必须加这个按钮", "先别问为什么，赶紧实现", "开发说成本很高"],
                        "boundary_reason": "这需要判断方案级表达背后的问题级需求，不能只执行固定清单。",
                        "next_action_shape": "输出 reframe_to_problem、problem_level_need、solution_risk、next_question。",
                    }
                ],
                "should_not_trigger": [
                    {
                        "scenario_id": "routine-template-fill",
                        "summary": "用户已经确认 Who/Why/How，只要求按模板整理一条日常需求。",
                        "prompt_signals": ["按变更需求模板整理", "字段都齐了"],
                        "boundary_reason": "这是高 workflow certainty + 高 context certainty，应进入 workflow_candidates/。",
                    }
                ],
                "edge_case": [
                    {
                        "scenario_id": "requester-not-real-user",
                        "summary": "需求提出者和真实使用者不一致，需要判断当前方案是否误代表真实问题。",
                        "prompt_signals": ["领导提的需求", "一线用户没参与", "不知道谁真正用"],
                        "boundary_reason": "需要 agentic 判断并补上下文，而不是直接选择流程。",
                        "next_action_shape": "列出缺失访谈对象和最小验证问题。",
                    }
                ],
                "refusal": [
                    {
                        "scenario_id": "solution-already-validated",
                        "summary": "业务问题、用户和约束都已验证，只剩下执行拆解。",
                        "prompt_signals": ["目标和用户都确认了", "只要拆任务"],
                        "boundary_reason": "不应把确定性执行伪装成厚 skill。",
                    }
                ],
            },
            "revision_summary": "Initial requirements-agentic extraction added because solution-level requests require judgment before deterministic daily-requirements workflows can safely run.",
        },
        "5-干系人分析": {
            "candidate_id": "stakeholder-resistance-tradeoff",
            "title": "Stakeholder Resistance Tradeoff",
            "trigger_patterns": [
                "stakeholder_attention_and_resistance_conflict",
                "important_stakeholder_missing_from_requirement",
                "scope_choice_depends_on_power_interest_tradeoff",
            ],
            "trigger_exclusions": [
                "stakeholder_list_is_only_being_filled",
                "single_stakeholder_no_conflict",
                "concept_query_only",
            ],
            "intake": [
                ("stakeholders", "list[structured]", "关键干系人、角色、权力、受影响程度和使用关系。"),
                ("attention_points", "list[string]", "各干系人的关注点、成功标准或收益。"),
                ("resistance_points", "list[string]", "各干系人的担心、阻力点、损失或反对理由。"),
                ("decision_scope", "string", "当前要决定的需求范围、优先级或沟通策略。"),
                ("disconfirming_evidence", "list[string]", "证明某个干系人被漏掉、权力判断错误或阻力被低估的证据。"),
            ],
            "schema": {
                "verdict": "enum[prioritize_resistance|prioritize_attention|ask_for_missing_stakeholder|defer]",
                "critical_stakeholders": "list[string]",
                "tradeoff_reason": "string",
                "risk_if_ignored": "list[string]",
                "evidence_to_check": "list[string]",
                "next_action": "string",
                "confidence": "enum[low|medium|high]",
            },
            "fails_when": [
                "critical_stakeholder_identity_uncertain",
                "resistance_point_is_asserted_without_evidence",
            ],
            "do_not_fire_when": [
                "stakeholder_list_is_only_being_filled",
                "single_stakeholder_no_conflict",
            ],
            "rationale_tail": (
                "This candidate exists because stakeholder analysis becomes agentic when the work is no longer listing roles but judging whose concern, resistance, or missing voice should change scope and next action. The deterministic stakeholder workflow remains the right artifact for inventory building; this skill handles conflict-sensitive boundary arbitration."
            ),
            "usage_notes": [
                "当关注点和阻力点冲突时，输出关键干系人、取舍理由和忽略风险。",
                "如果只是补干系人列表，应路由到 workflow_candidates/4-干系人识别 或 5-干系人分析。",
                "必须显式检查遗漏干系人和被低估阻力，不能只给沟通建议。",
                "当关键干系人身份不确定时，先 ask_for_missing_stakeholder。",
            ],
            "scenarios": {
                "should_trigger": [
                    {
                        "scenario_id": "resistance-changes-scope",
                        "summary": "业务方关注效率，审计或运营方担心风险，需求范围需要在冲突中取舍。",
                        "prompt_signals": ["一方要快", "另一方担心风险", "到底听谁的"],
                        "boundary_reason": "这里需要判断关注点和阻力点的权重，不是填写干系人表。",
                        "next_action_shape": "输出 prioritize_resistance/prioritize_attention、critical_stakeholders、risk_if_ignored。",
                    }
                ],
                "should_not_trigger": [
                    {
                        "scenario_id": "stakeholder-inventory-only",
                        "summary": "用户只要求列出项目干系人和基本职责。",
                        "prompt_signals": ["帮我列干系人", "整理角色列表"],
                        "boundary_reason": "这是确定性识别流程，应保留在 workflow_candidates/。",
                    }
                ],
                "edge_case": [
                    {
                        "scenario_id": "missing-real-user",
                        "summary": "发起人明确，但真实使用者或受影响群体没有被访谈。",
                        "prompt_signals": ["领导提的", "一线没人参与", "不知道谁会反对"],
                        "boundary_reason": "需要判断缺失干系人是否足以阻断结论。",
                        "next_action_shape": "输出 ask_for_missing_stakeholder 和最小补访谈列表。",
                    }
                ],
                "refusal": [
                    {
                        "scenario_id": "single-stakeholder-no-conflict",
                        "summary": "只有一个明确使用者且无冲突，只需继续执行固定分析模板。",
                        "prompt_signals": ["只有一个使用部门", "没有争议"],
                        "boundary_reason": "不应为无冲突场景制造 agentic 判断。",
                    }
                ],
            },
            "revision_summary": "Initial requirements-agentic extraction added to separate conflict-sensitive stakeholder tradeoff from deterministic stakeholder inventory workflows.",
        },
    }
    spec = requirement_specs.get(source_candidate_id)
    if not spec:
        return []
    candidate_id = spec["candidate_id"]
    title = spec["title"]
    contract = _build_requirements_agentic_contract(spec)
    trace_ref = _write_trace_doc(
        bundle_root=bundle_root,
        candidate_id=candidate_id,
        title=title,
        descriptors=descriptors,
    )
    eval_summary = _write_eval_docs(
        bundle_root=bundle_root,
        candidate_id=candidate_id,
        title=title,
        descriptors=descriptors,
        contract=contract,
    )
    scenario_families = _with_anchor_refs(spec["scenarios"], descriptors)
    skill_seed = _compose_skill_seed(
        candidate_id=candidate_id,
        title=title,
        contract=contract,
        descriptors=descriptors,
        trace_ref=trace_ref,
        usage_notes=spec["usage_notes"],
        scenario_families=scenario_families,
        eval_summary=eval_summary,
    )
    skill_seed["relations"]["depends_on"] = spec.get("depends_on", [])
    skill_seed["relations"]["complements"] = spec.get("complements", [])
    skill_seed["rationale"] = _build_requirements_agentic_rationale(
        title=title,
        descriptors=descriptors,
        tail=spec["rationale_tail"],
    )
    skill_seed["evidence_summary"] = _build_requirements_agentic_evidence_summary(
        title=title,
        descriptors=descriptors,
    )
    skill_seed["revision_seed"] = {
        "summary": spec["revision_summary"],
        "evidence_changes": [
            "Preserved deterministic requirement-analysis workflows under workflow_candidates/.",
            "Added a separate llm_agentic candidate only for judgment-rich arbitration.",
            "Bound the candidate to graph/source double anchors and smoke evaluation cases.",
        ],
        "open_gaps": [
            "Replace generated smoke cases with real project review logs.",
            "Verify the skill against mixed stakeholder and scope-trimming cases before broad publication.",
        ],
    }
    return [
        {
            "candidate_id": candidate_id,
            "candidate_kind": "general_agentic",
            "agentic_priority": 8,
            "skill_seed": skill_seed,
        }
    ]


def _build_requirements_agentic_contract(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "trigger": {
            "patterns": spec["trigger_patterns"],
            "exclusions": spec["trigger_exclusions"],
        },
        "intake": {
            "required": [
                {"name": name, "type": kind, "description": description}
                for name, kind, description in spec["intake"]
            ]
        },
        "judgment_schema": {
            "output": {
                "type": "structured",
                "schema": spec["schema"],
            },
            "reasoning_chain_required": True,
        },
        "boundary": {
            "fails_when": spec["fails_when"],
            "do_not_fire_when": spec["do_not_fire_when"],
        },
    }


def _with_anchor_refs(
    scenario_families: dict[str, Any],
    descriptors: list[dict[str, str]],
) -> dict[str, Any]:
    anchor_refs = [item["anchor_id"] for item in descriptors[:3]]
    enriched: dict[str, Any] = {}
    for family, cases in scenario_families.items():
        enriched_cases = []
        for case in cases:
            case_doc = dict(case)
            case_doc.setdefault("anchor_refs", anchor_refs)
            enriched_cases.append(case_doc)
        enriched[family] = enriched_cases
    return enriched


def _build_requirements_agentic_rationale(
    *,
    title: str,
    descriptors: list[dict[str, str]],
    tail: str,
) -> str:
    primary = descriptors[0]
    support = " ".join(
        f"`{item['label']}` adds source context through \"{item['snippet']}\"[^anchor:{item['anchor_id']}]."
        for item in descriptors[1:3]
    )
    return (
        f"`{title}` is anchored in \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
        f"{support} "
        f"{tail} The output must name the evidence it checked, the boundary reason, and a concrete next action; otherwise it should defer or route back to workflow_candidates/."
    ).strip()


def _build_requirements_agentic_evidence_summary(
    *,
    title: str,
    descriptors: list[dict[str, str]],
) -> str:
    lines = [
        f"`{title}` is grounded in \"{descriptors[0]['snippet']}\"[^anchor:{descriptors[0]['anchor_id']}]."
    ]
    for item in descriptors[1:3]:
        lines.append(
            f"`{item['label']}` supplies neighboring source evidence: \"{item['snippet']}\"[^anchor:{item['anchor_id']}]."
        )
    lines.append(
        "These anchors justify an llm_agentic candidate only where the user needs interpretation, conflict arbitration, or missing-context judgment; deterministic execution remains in workflow_candidates/."
    )
    return "\n\n".join(lines)


def _derive_related_candidate_id(*, base_candidate_id: str, semantic_root: str) -> str:
    if str(base_candidate_id).endswith("-source-note"):
        return f"{semantic_root}-source-note"
    return semantic_root


def _rewrite_source_chunks_doc(
    *,
    source_chunks_doc: dict[str, Any],
    source_file_map: dict[str, str],
    copied_source_root: str,
) -> dict[str, Any]:
    rewritten = dict(source_chunks_doc)
    rewritten["source_file"] = _rewrite_source_file_value(
        str(source_chunks_doc.get("source_file", "")),
        source_file_map=source_file_map,
        default=copied_source_root,
    )
    if isinstance(source_chunks_doc.get("source_files"), list):
        rewritten["source_files"] = [
            _rewrite_source_file_value(str(item), source_file_map=source_file_map)
            for item in source_chunks_doc["source_files"]
            if isinstance(item, str) and item
        ]
    rewritten["section_map"] = []
    for entry in source_chunks_doc.get("section_map", []):
        if not isinstance(entry, dict):
            continue
        section_doc = dict(entry)
        if isinstance(section_doc.get("source_file"), str):
            section_doc["source_file"] = _rewrite_source_file_value(
                section_doc["source_file"],
                source_file_map=source_file_map,
            )
        rewritten["section_map"].append(section_doc)
    rewritten["chunks"] = []
    for chunk in source_chunks_doc.get("chunks", []):
        if not isinstance(chunk, dict):
            continue
        chunk_doc = dict(chunk)
        chunk_doc["source_file"] = _rewrite_source_file_value(
            str(chunk.get("source_file", "")),
            source_file_map=source_file_map,
        )
        rewritten["chunks"].append(chunk_doc)
    return rewritten


def _rewrite_source_file(
    *,
    entity: dict[str, Any],
    source_file_map: dict[str, str],
) -> dict[str, Any]:
    rewritten = dict(entity)
    if isinstance(rewritten.get("source_file"), str):
        rewritten["source_file"] = _rewrite_source_file_value(
            rewritten["source_file"],
            source_file_map=source_file_map,
        )
    return rewritten


def _build_trigger_registry(skill_seed_specs: list[dict[str, Any]]) -> dict[str, Any]:
    trigger_entries = []
    seen_symbols: set[str] = set()
    for spec in skill_seed_specs:
        title = spec["title"]
        trigger = spec["contract"]["trigger"]
        boundary = spec["contract"]["boundary"]
        definitions = {}
        for symbol in trigger.get("patterns", []):
            definitions[symbol] = f"Use {title} when the scenario contains a live decision that this principle can materially improve."
        for symbol in trigger.get("exclusions", []):
            if symbol == "concept_query_only":
                definitions[symbol] = f"Do not use {title} when the user is only asking for a concept explanation rather than making a decision."
            else:
                definitions[symbol] = f"Do not use {title} when the scenario is clearly outside its operating boundary."
        for symbol in boundary.get("fails_when", []):
            if symbol == "disconfirming_evidence_present":
                definitions[symbol] = f"Abort {title} when concrete evidence appears that directly weakens the principle in this scenario."
            else:
                definitions[symbol] = f"Abort {title} when source evidence for the scenario conflicts with the principle."
        for symbol in boundary.get("do_not_fire_when", []):
            if symbol == "scenario_missing_decision_context":
                definitions[symbol] = f"Do not fire {title} when the scenario lacks a concrete decision, tradeoff, or next action."
            else:
                definitions[symbol] = f"Do not fire {title} when the scenario boundary is still unclear or underspecified."
        for symbol, definition in definitions.items():
            if symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)
            trigger_entries.append(
                {
                    "symbol": symbol,
                    "definition": definition,
                    "positive_examples": [definition],
                    "negative_examples": [f"Scenario does not satisfy `{symbol}`."],
                }
            )
    return {"triggers": trigger_entries}


def _collect_descriptors(
    *,
    bundle_root: Path,
    node: dict[str, Any],
    node_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    candidate_id: str,
) -> list[dict[str, str]]:
    descriptors = [_descriptor_from_node(bundle_root=bundle_root, node=node, candidate_id=candidate_id)]
    evidence_nodes = []
    context_nodes = []
    for edge in adjacency.get(node["id"], []):
        other_id = edge["to"] if edge["from"] == node["id"] else edge["from"]
        other = node_map.get(other_id)
        if not other:
            continue
        if other.get("type") == "chunk_evidence":
            evidence_nodes.append(other)
        elif other.get("type") in {"framework_signal", "source_section"}:
            context_nodes.append(other)
    for index, support_node in enumerate([*evidence_nodes, *context_nodes][:3], start=1):
        descriptor = _descriptor_from_node(
            bundle_root=bundle_root,
            node=support_node,
            candidate_id=candidate_id,
        )
        descriptor["rank"] = str(index)
        descriptors.append(descriptor)
    return descriptors


def _descriptor_from_node(
    *,
    bundle_root: Path,
    node: dict[str, Any],
    candidate_id: str,
) -> dict[str, str]:
    relative_path = str(node.get("source_file", ""))
    source_location = node.get("source_location", {}) or {}
    line_start = int(source_location.get("line_start", 1) or 1)
    line_end = int(source_location.get("line_end", line_start) or line_start)
    snippet = _read_snippet(
        bundle_root=bundle_root,
        relative_path=relative_path,
        line_start=line_start,
        line_end=line_end,
    )
    return {
        "anchor_id": f"{candidate_id}-{node['id']}",
        "node_id": node["id"],
        "label": str(node.get("label", node["id"])),
        "snippet": snippet or str(node.get("label", node["id"])),
        "path": relative_path,
        "line_start": str(line_start),
        "line_end": str(line_end),
    }


def _build_seed_contract(
    *,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
) -> dict[str, Any]:
    primary_snippet = descriptors[0]["snippet"] if descriptors else ""
    return build_semantic_contract(
        candidate_id=candidate_id,
        title=title,
        primary_snippet=primary_snippet,
    )


def _build_seed_rationale(
    *,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
    contract: dict[str, Any],
) -> str:
    primary = descriptors[0]
    supporting = descriptors[1:]
    semantic_family = identify_semantic_family(candidate_id)
    support_text = " ".join(
        (
            f"`{item['label']}` adds operational context through "
            f"\"{item['snippet']}\"[^anchor:{item['anchor_id']}]."
        )
        for item in supporting[:2]
    )
    if _is_borrowed_value_family(semantic_family):
        profile = _borrowed_value_profile(semantic_family)
        return (
            f"`{title}` is a borrowed-value judgment skill anchored in "
            f"\"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
            f"It should fire when {profile['trigger']}. "
            "The skill must not summarize, translate, introduce a person, answer a pure fact lookup, or comment on the author's stance as its main job; those remain source/retrieval tasks. "
            f"Instead it maps the source pattern `{profile['source_pattern']}` into a current decision only after checking transfer_conditions and anti_conditions. "
            f"{support_text} "
            f"The output must use `{profile['verdicts']}` and include {profile['output']}. "
            "It must explicitly detect `single_case_overreach` or `context_transfer_abuse` when the user tries to copy a book, historical case, competitor, large-company process, or past success without context fit."
        ).strip()
    if semantic_family == "historical-case-consequence-judgment":
        return (
            f"`{title}` is anchored in multiple historical episodes, starting from \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
            "It should fire when the user is not merely asking what happened in history, but wants to use historical cases to judge a current choice, policy, strategy, or organizational tradeoff. "
            "The skill must extract a case-consequence pattern, then state where the analogy transfers and where it breaks. "
            "This is intentionally agentic: it requires comparing actors, incentives, constraints, timing, and consequences across cases before deciding whether the pattern applies. "
            f"{support_text} "
            "The output should be `apply_pattern / partial_apply / do_not_apply`, with a named case pattern, transfer limits, a decision warning, and a concrete next action. "
            "It must refuse pure history summaries, fact lookup, or single anecdote arguments that lack a live decision boundary."
        ).strip()
    if semantic_family == "role-boundary-before-action":
        return (
            f"`{title}` is anchored in role, mandate, and consequence evidence beginning with "
            f"\"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
            "It should fire when the user has a live action under a role, mandate, delegation, or organizational position and must decide whether acting now would exceed authority, damage trust, or create a bad precedent. "
            f"{support_text} "
            "The skill should not merely warn generically; it must name the role boundary, authority gap, order cost, and safe next action. "
            "It must refuse pure role-definition questions, meeting templates, and cases requiring legal/compliance final judgment rather than agentic boundary arbitration."
        ).strip()
    if semantic_family == "circle-of-competence":
        return (
            f"`{title}` anchored in \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}] should fire "
            "when the user is about to enter an unfamiliar domain, says things like "
            "“我可以学”“应该差不多”“大家都说这是好机会”“我好像懂了但说不清楚”, "
            "or is tempted by scenarios like “朋友拉我投餐饮连锁, 我虽然没做过但应该能搞明白”. "
            "and is still preparing to make a real commitment. "
            "The draft should force a demonstrated-understanding test rather than reward familiarity. "
            "It needs a real target, real background, real capital-at-risk context, and concrete "
            "disconfirming evidence before it can say the decision is inside or outside the circle. "
            "Edge handling matters here: the skill should separate transferable general ability from missing domain knowledge, "
            "for example 软件工程经验 versus 机器学习专业能力, or product-method skill versus an unfamiliar industry. "
            "In cases like “虽然没做过机器学习, 但感觉跟之前的软件工程差不多”, the output should explicitly区分可迁移能力与专业能力边界, "
            "评估核心风险点是否在能力圈内, and give a 圈内 / 边界 / 圈外 classification instead of a generic caution. "
            "The same refusal logic should apply to career pivots like “想全职做自媒体, 好像懂内容但说不清怎么变现”: "
            "说不清变现逻辑等于还不在圈内, so the draft should first列出真正理解和不理解的部分, then give an action plan. "
            "It should also explicitly refuse to hijack pure comparison requests like “Python 和 Go 哪个更适合做微服务”, "
            "because objective technology selection is not the same thing as asking whether the operator is outside the circle. "
            f"{support_text} "
            "The expected output is not a vague humility reminder but "
            "`in_circle / edge_of_circle / outside_circle`, followed by missing knowledge and a concrete "
            "`proceed / study_more / decline` action."
        ).strip()
    if semantic_family == "invert-the-problem":
        return (
            f"`{title}` anchored in \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}] should fire "
            "when the user says the plan feels too optimistic, asks what could make it fail, "
            "or wants a pre-mortem before acting, such as a product launch, market entry, or investment that could bloodily fail. "
            "The draft should invert the objective into failure conditions, surface ruin paths, "
            "and systematically list failure factors instead of a decorative checklist. "
            "It should be comfortable with prompts like “这个产品发布会怎么彻底失败”“进入东南亚市场最坏会怎样”, "
            "but refuse to drift into generic 创意方向头脑风暴. "
            "When a team says “我们只看到了机会没看到威胁”, the output should explicitly treat that as a red-team / 找茬 trigger: "
            "systematically列出潜在威胁和失败模式, then turn them into 找茬清单 and pre-mortem preventive actions instead of继续扩创意广度. "
            "For创业场景 such as “明年做在线教育, 有没有没想到的风险”, it should name concrete failure paths like 资金断裂、获客成本失控、政策风险、交付质量崩塌, "
            "and turn them into a 避坑清单 rather than abstractly saying 'consider risks'. "
            "For投资场景 such as “什么情况下这笔投资会血本无归”, it should list 致命风险因素 and build a 失败前置检查清单, "
            "not stop at a general warning that the investment has risks. "
            "Edge handling must stay explicit: for跳槽这类职业决策, only activate when the user wants to系统性评估跳槽风险和失败模式; "
            "if the user is merely比较两个选项的优劣, route it to general decision support instead of forcing inversion. "
            "For健身计划这类个人日常目标, the method can still fire when the user主动要求从失败角度设计, but it should stay lightweight: "
            "give a 轻量 pre-mortem or partial_review, not a重大决策级别的重型风险框架. "
            f"{support_text} "
            "The output should include concrete failure modes, a first preventive action, and "
            "`full_inversion / partial_review / defer` so edge cases do not collapse into over-application."
        ).strip()
    if semantic_family == "bias-self-audit":
        return (
            f"`{title}` anchored in \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}] should fire "
            "when the user already has a strong thesis, is under commitment pressure, says "
            "“我觉得这肯定是对的”“不可能错”“反面意见我都不想听了”, "
            "or is leaning on group consensus instead of active counter-evidence. "
            "This includes cases like “大家都同意这个方案, 明天就拍板”, or “我已经收集了很多支持我观点的数据”. "
            "The draft should name the active distortion, require the strongest disconfirming evidence, "
            "and produce mitigation actions rather than generic advice about staying objective. "
            "It must also refuse to overreach into cases like “服务器突然宕机了先判断数据库还是网络” or “先帮我收集新能源行业数据”, "
            "because those are urgent incident triage or early research, not live bias-audit windows. "
            f"{support_text} "
            "The output should identify triggered biases, severity, mitigation actions, and whether the case "
            "deserves a `full_audit`, only a `partial_review`, or an explicit `defer`."
        ).strip()
    if semantic_family == "value-assessment":
        return (
            f"`{title}` anchored in \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}] should fire "
            "when the user is trying to judge whether price is justified by value, whether panic created mispricing, "
            "or whether a private-business / angel valuation has any defensible value anchor at all. "
            "It should also fire when the user asks why a great business is fundamentally better than an ordinary one, "
            "especially if the real question is about 护城河、定价权、尚未利用的提价能力, and long-run value creation rather than mere size comparison. "
            "It should handle prompts like “这家公司品牌很强但价格不便宜, 到底值不值这个价”, "
            "“市场恐慌是不是把好公司错杀了”, “这种公司和其他公司到底差在哪”, and “这个天使轮估值到底有没有道理”, "
            "without immediately jumping to final position size. "
            "The draft should first build a value view from moat, pricing power, capital intensity, management quality, "
            "circle of competence, and the quality of the underlying business economics; only after that should it decide "
            "whether the current price looks undervalued, fair, overvalued, or lacks a stable value anchor entirely. "
            "For创业项目、加盟店、私有生意或天使轮, the output should test whether the user actually understands the business model, "
            "cash-generation logic, and downside asymmetry before treating the quoted valuation as meaningful, and it should explicitly mark these as `partial_applicability` cases until the value anchor is defensible. "
            "For比特币或类似没有稳定内在价值锚点的投机场景, it should explicitly call out that speculation is being presented as value "
            "and return `no_value_anchor` plus `refuse` / decline language rather than forcing a fake valuation conclusion. "
            "It should refuse short-term trading requests like “MACD 和 KDJ 哪个更适合日内交易”, "
            "and refuse pure scale-comparison prompts like “8000 人、200 亿营收算不算大公司”, because neither is a live price-vs-value judgment. "
            f"{support_text} "
            "The output should produce `undervalued / fairly_priced / overvalued / no_value_anchor`, name the key value drivers and boundary warnings, "
            "and explicitly decide whether to use `full_valuation`, `partial_applicability`, or `refuse`, plus whether to `delegate_to_sizing`, `monitor_only`, or `decline`."
        ).strip()
    if semantic_family == "margin-of-safety-sizing":
        return (
            f"`{title}` anchored in \"{primary['snippet']}\"[^anchor:{primary['anchor_id']}] should fire "
            "when the user asks whether a price is reasonable, whether the safety margin is enough, "
            "or how large a real capital commitment should be under uncertainty. "
            "That includes prompts like “市盈率 25 倍不算便宜但品牌很强, 这个价格合理吗”, "
            "“市场大跌是不是把好公司错杀了”, and “朋友推荐天使轮, 这笔钱值不值得投”. "
            "The draft should start from moat, margin of safety, pricing power, management quality, and circle of competence, "
            "then turn that value-assessment language into downside range, liquidity, irreversibility, and position-size constraints "
            "instead of stopping at “this looks like a good business”. "
            "For stock-like questions, the output should从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估, not just say the company looks good. "
            "For创业项目或天使轮, it should first做能力圈检验, ask whether the user truly understands the business, and only then评估护城河、安全边际、流动性与 check size. "
            "For比特币或类似高波动但无稳定内在价值的投机标的, it should explicitly say 安全边际不适用于赌博, "
            "and return `refuse` or a strong warning instead of pretending normal sizing logic still applies. "
            "It should also recognize panic-market opportunity language, “品牌很强但不便宜”, "
            "and “尚未利用的提价能力” as signals that valuation and sizing need to be connected rather than separated. "
            "At the same time it should refuse short-term trading prompts like “MACD 和 KDJ 哪个更适合日内交易”, "
            "and refuse pure scale-comparison questions like “8000 人、200 亿营收算不算大公司”, because neither contains a live sizing decision. "
            f"{support_text} "
            "The output should produce a sizing band, explicit constraints, and "
            "`full_sizing / partial_applicability / refuse` so non-stock edge cases and speculative assets "
            "do not get normal sizing advice by accident."
        ).strip()
    return (
        f"`{title}` is distilled from the source excerpt "
        f"\"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
        "The draft treats this as a decision-facing principle rather than a thematic summary: "
        "the contract asks for a concrete scenario, a clear decision goal, and explicit constraints "
        "so the skill can judge whether the principle should actively fire, be deferred, or stay out of scope. "
        f"{support_text} "
        f"The boundary remains narrow by design: if `{contract['boundary']['fails_when'][0]}` or "
        f"`{contract['boundary']['do_not_fire_when'][0]}` is true, the skill should not over-claim."
    ).strip()


def _build_seed_evidence_summary(
    *,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
) -> str:
    primary = descriptors[0]
    supporting = descriptors[1:]
    semantic_family = identify_semantic_family(candidate_id)
    if _is_borrowed_value_family(semantic_family):
        profile = _borrowed_value_profile(semantic_family)
        return "\n\n".join(
            [
                (
                    f"`{title}` is grounded in borrowed-value evidence beginning with "
                    f"\"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]."
                ),
                *[
                    (
                        f"`{item['label']}` preserves another source anchor for mechanism transfer: "
                        f"\"{item['snippet']}\"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                (
                    "The graph/source layer may extract summaries, chronology, facts, biography cues, positions, and source text broadly, "
                    "but this skill consumes that evidence only for current decision transfer. "
                    f"Required transfer_conditions: {', '.join(profile['transfer_conditions'])}. "
                    f"Blocking anti_conditions: {', '.join(profile['anti_conditions'])}. "
                    "Pure summary, translation, fact lookup, biography introduction, author-position query, and stance commentary without user decision should not trigger the judgment skill."
                ),
            ]
        )
    if semantic_family == "historical-case-consequence-judgment":
        return "\n\n".join(
            [
                (
                    f"`{title}` is anchored to historical case evidence beginning with \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}]."
                ),
                *[
                    (
                        f"`{item['label']}` supplies an additional case or consequence anchor: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These excerpts justify a judgment skill only when a user has a current decision and needs to compare historical case patterns, consequences, incentives, and transfer limits. They do not justify treating history as a deterministic recipe or using one anecdote as proof.",
            ]
        )
    if semantic_family == "role-boundary-before-action":
        return "\n\n".join(
            [
                (
                    f"`{title}` is grounded in role-boundary evidence beginning with \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}]."
                ),
                *[
                    (
                        f"`{item['label']}` supplies another authority, mandate, or consequence anchor: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These anchors support a boundary-arbitration skill only when a user is deciding whether to act under uncertain authorization. They do not support ancient-role literalism, generic hierarchy advice, or deterministic workflow execution.",
            ]
        )
    if semantic_family == "circle-of-competence":
        return "\n\n".join(
            [
                (
                    f"`{title}` is anchored to \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}], which should be used to distinguish real understanding from surface familiarity."
                ),
                *[
                    (
                        f"`{item['label']}` adds neighboring evidence: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These excerpts should support explicit circle judgments, missing-knowledge lists, and decline decisions when the user cannot explain the business clearly, claims “应该差不多能搞明白”, mistakes Python-vs-Go style technology comparison for a circle-of-competence question, or forgets that 10 years of successful backend architecture work already counts as a proven in-circle record. They should also support software-engineering-vs-machine-learning boundary mapping, core-risk evaluation, 圈内 / 边界 / 圈外 classification, and the rule that 说不清变现逻辑等于还不在圈内.",
            ]
        )
    if semantic_family == "invert-the-problem":
        return "\n\n".join(
            [
                (
                    f"`{title}` is anchored to \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}], which should be read as a failure-first planning cue rather than a generic reminder to think backwards."
                ),
                *[
                    (
                        f"`{item['label']}` preserves neighboring evidence: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These excerpts should support explicit failure modes, avoid-rules, and pre-mortem style next actions, while preserving the boundary against pure 创意方向 brainstorming. They should explicitly cover 团队只看机会没看到威胁 and 系统性找茬 scenarios, so the draft can produce 潜在威胁、失败模式、找茬清单 and 预防动作 instead of generic caution. In startup cases they should point toward 资金断裂、获客成本、政策风险等具体失败路径 and a concrete 避坑清单. In investment cases they should support 血本无归-style ruin scans and a 失败前置检查清单. They should also preserve edge handling for 跳槽风险 and 个人日常目标: 跳槽这类职业决策只有在用户明确要系统性评估失败模式时才激活, while 健身计划这类场景 should stay a 轻量 pre-mortem / partial_review rather than a heavy major-decision framework.",
            ]
        )
    if semantic_family == "bias-self-audit":
        return "\n\n".join(
            [
                (
                    f"`{title}` is anchored to \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}], which should be used to name bias, not just warn that bias exists."
                ),
                *[
                    (
                        f"`{item['label']}` preserves neighboring evidence: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These excerpts should support named distortions, counter-evidence tasks, and mitigation actions before commitment hardens, while keeping 达尔文历史/科学知识查询, early market-data collection before any thesis exists, and urgent incident response outside scope.",
            ]
        )
    if semantic_family == "value-assessment":
        return "\n\n".join(
            [
                (
                    f"`{title}` is anchored to \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}], which should be used to challenge price with value before any sizing decision is made."
                ),
                *[
                    (
                        f"`{item['label']}` preserves neighboring evidence: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These excerpts should support explicit value-anchor judgments, pricing-power analysis, 'great company vs ordinary company' comparisons, mispricing checks, and refusal when the asset lacks a stable intrinsic-value basis. They should keep short-term trading and pure scale comparison outside scope, while covering public equities, private businesses, franchise economics, and angel-style valuations where the real question is whether current price can be defended by business value at all.",
            ]
        )
    if semantic_family == "margin-of-safety-sizing":
        return "\n\n".join(
            [
                (
                    f"`{title}` is anchored to \"{primary['snippet']}\""
                    f"[^anchor:{primary['anchor_id']}], which should be used to translate quality and valuation into survival-first sizing constraints."
                ),
                *[
                    (
                        f"`{item['label']}` preserves neighboring evidence: \"{item['snippet']}\""
                        f"[^anchor:{item['anchor_id']}]."
                    )
                    for item in supporting[:2]
                ],
                "These excerpts should support concrete sizing bands, downside checks, and refusal when the setup lacks margin-of-safety math, especially in cases framed as “价格合理吗”“安全边际够不够” or “市场恐慌是不是错杀”, while excluding 规模和竞争格局比较 and short-term trading questions. They should also support five-dimension value assessment, the sequence '先做能力圈检验, 再评估护城河和安全边际' for angel-style investments, and the rule that 比特币这类高波动但无内在价值的投机标的不适用安全边际.",
            ]
        )
    lines = [
        (
            f"`{title}` is primarily anchored to \"{primary['snippet']}\""
            f"[^anchor:{primary['anchor_id']}]."
        ),
    ]
    for item in supporting[:2]:
        lines.append(
            (
                f"`{item['label']}` preserves neighboring evidence: \"{item['snippet']}\""
                f"[^anchor:{item['anchor_id']}]."
            )
        )
    lines.append(
        "These excerpts remain bound to both `anchors.yaml` and the source-backed graph snapshot."
    )
    return "\n\n".join(lines)


def _build_usage_notes(
    *,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
) -> list[str]:
    primary = descriptors[0]
    semantic_family = identify_semantic_family(candidate_id)
    if _is_borrowed_value_family(semantic_family):
        profile = _borrowed_value_profile(semantic_family)
        return [
            f"Use this skill when {profile['trigger']}; the live current_decision must be explicit before the source pattern is transferred.",
            "Keep source extraction broad, but keep skill firing narrow: summary, translation, fact lookup, biography introduction, author-position query, and stance commentary without user decision belong outside this judgment skill.",
            "Before applying the pattern, list transfer_conditions and anti_conditions; if either side is missing, ask for more context or decline.",
            "Treat single_case_overreach and context_transfer_abuse as first-class abuse checks, especially when the user wants to copy a book, historical case, competitor, large-company process, or past success.",
            f"Positive trigger signals include: {', '.join(profile['positive_signals'])}.",
            f"Negative trigger signals include: {', '.join(profile['negative_signals'])}.",
            f"Output {profile['output']} with a `{profile['verdicts']}` verdict.",
        ]
    if semantic_family == "historical-case-consequence-judgment":
        return [
            "Use this skill when the user wants to apply historical cases to a live decision, not when they only ask for a summary of what happened.",
            "Ask for the current decision, candidate historical analogies, relevant differences, and the boundary of transfer before giving advice; if the user asks `司马迁是哪一年出生的？`, answer as a fact lookup outside this skill.",
            "Output a named case pattern, the consequences it highlights, transfer limits, and a concrete next action.",
            "Use `partial_apply` when the case pattern is suggestive but actor incentives, institutional context, or time horizon differ materially.",
            "Use `do_not_apply` when the user is cherry-picking one story, asking for fact lookup such as birth year/biography, asking to translate classical Chinese into modern Chinese, or ignoring decisive differences between the historical case and the current situation.",
        ]
    if semantic_family == "role-boundary-before-action":
        return [
            "Use this skill when the user asks whether they should act, intervene, decide, escalate, or refuse under a specific role, mandate, delegation, or organizational responsibility.",
            "Ask for actor_role, proposed_action, authority_boundary, stakeholders, urgency, and order_cost before giving a verdict.",
            "Output `act / act_with_boundary / ask_or_delegate / refuse`, with role_boundary, authority_gap, order_cost, and safe_next_action.",
            "Use `ask_or_delegate` when the action may be useful but the mandate is ambiguous or the decision properly belongs to another role.",
            "Use `refuse` when the user requests a template, role definition, legal final opinion, or action with unknown authorization facts.",
        ]
    if semantic_family == "circle-of-competence":
        return [
            "Use this skill when the user is about to commit in an unfamiliar domain and says things like “我可以学”“应该差不多” or “大家都说这是好机会”.",
            "Representative trigger cases include “朋友拉我投资餐饮连锁, 我之前没做过餐饮但觉得应该能搞明白” and “读了几本价值投资书就想开始实盘”.",
            "When the scenario is “软件工程经验 vs 机器学习专业能力”, explicitly区分可迁移能力与专业能力边界, 评估核心风险点是否在能力圈内, 并给出圈内 / 边界 / 圈外的分类判断。",
            "When the user says “大家都说 Web3 是好机会”, explicitly treat this as 用他人观点替代独立判断, and require the user to explain the 核心运作逻辑 before allowing any proceed recommendation.",
            "When the user says “好像懂内容但说不清怎么变现”, treat 说不清变现逻辑 as a hard warning signal, list真正理解和不理解的部分, and refuse to call the move in-circle just because the user understands content creation superficially.",
            "Use edge handling when the user has transferable general skill but missing domain knowledge, such as software engineering vs machine learning or product management vs a new industry.",
            "Do not fire on concept-only questions, experienced operators already inside their proven domain, or objective comparison requests such as “Python 和 Go 哪个更适合做微服务开发”.",
            "Output `in_circle / edge_of_circle / outside_circle`, list missing knowledge, name core risk points, and end with `proceed / study_more / decline`.",
        ]
    if semantic_family == "invert-the-problem":
        return [
            "Use this skill when the user asks what could make a plan fail, says the plan feels too optimistic, or wants a pre-mortem before committing.",
            "Representative trigger cases include “产品上市计划有什么漏洞”, “进入东南亚市场最坏会怎样”, and “怎么才能让这笔投资不失败”.",
            "When the team says “只看到了机会没看到威胁”, treat it as a system-level red-team / 找茬 request: 列出潜在威胁、失败模式、找茬清单 and the first preventive action, not more ideation.",
            "For创业场景 such as 在线教育、市场进入、重大投资, output should list 资金断裂、获客成本、政策风险、执行崩盘等失败路径, then turn them into a 避坑清单 and first preventive action.",
            "For投资场景 such as “什么情况下会血本无归”, output should list 致命风险因素 and build a 失败前置检查清单 rather than stopping at '注意风险'.",
            "For跳槽这类职业决策, only use inversion when the user wants to系统性评估跳槽风险和失败模式; if the user is just比较两个选项的优劣, a general decision aid is a better fit.",
            "For健身计划这类个人日常目标, the method can fire only as a 轻量 pre-mortem: weight it lower, keep it to partial_review, and avoid major-decision-grade overengineering.",
            "Do not fire on concept-only questions, pure brainstorming such as “给我几个新产品创意方向”, or decisions that are already locked and only want post-hoc decoration.",
            "Output failure modes, avoid-rules, a first preventive action, and `full_inversion / partial_review / defer` for edge cases.",
        ]
    if semantic_family == "bias-self-audit":
        return [
            "Use this skill when the user already has a strong view, resists counter-evidence, or is moving under commitment, identity, social proof, or incentive pressure.",
            "Typical triggers include “大家都同意这个方案, 明天就拍板”, “我已经收集了很多支持数据”, and “反面意见我都不想听了”.",
            "Do not fire on history or concept queries, market-data collection requests such as “先帮我收集新能源行业数据”, urgent incident handling such as “服务器突然宕机了”, or cases where the user is merely comparing options without a settled thesis. 对紧急决策场景不应激活, 因为系统性地搜索反面证据不现实。",
            "Output triggered biases, severity, mitigation actions, a concrete `next_action`, strongest counter-evidence to check, and `full_audit / partial_review / defer`.",
        ]
    if semantic_family == "value-assessment":
        return [
            "Use this skill when the user asks whether price is justified by value, whether panic created mispricing, or whether a quoted valuation has any defensible business-value anchor.",
            "Representative trigger cases include “品牌很强但价格不便宜, 到底值不值这个价”, “市场暴跌是不是把好公司错杀了”, and “这个天使轮估值到底有没有道理”.",
            "It should also trigger on “这种公司和其他公司到底差在哪” when the real question is about 护城河、定价权、尚未利用的提价能力, and why a great company deserves a structurally different valuation multiple.",
            "For public-equity style decisions, first build a value view from 护城河、定价权、资本回报、管理层和能力圈，再判断价格相对价值是低估、公允还是高估。",
            "For私有生意、加盟店或天使轮, 先做能力圈检验，再验证商业模式、现金流逻辑和理解深度，之后才判断 quoted valuation 是否站得住脚；如果理解本身站不住，就不要把估值数字当成真相。",
            "For私有生意、加盟店或天使轮这类边界案例, 默认使用 `partial_applicability`, 先做价值锚点和能力圈校验，再决定是否继续。",
            "For比特币或类似没有稳定内在价值锚点的投机标的, 明确输出 `no_value_anchor`、`refuse` 与 `decline`, 不要伪造正常估值判断。",
            "Do not fire on概念解释、短线交易问题，或只比较规模和竞争格局但没有价值判断问题的分析请求；短线交易与日内指标问题违背这个框架面向长期持有的前提。",
            "When the user only asks about规模和竞争格局, route the case to `scale-advantage-analysis` instead of pretending that every company comparison is already a value judgment.",
            "If the user also asks how大仓位、how much capital to commit, hand the case off to sizing rather than letting value judgment silently吞掉 sizing discipline.",
            "Output `undervalued / fairly_priced / overvalued / no_value_anchor`, `full_valuation / partial_applicability / refuse`, key value drivers, boundary warnings, a concrete `next_action`, and `delegate_to_sizing / monitor_only / decline`.",
        ]
    if semantic_family == "margin-of-safety-sizing":
        return [
            "Use this skill when the user asks whether the price is reasonable, whether the safety margin is enough, whether panic is creating opportunity, or how large a real capital commitment should be.",
            "Representative trigger cases include “市盈率25倍不算便宜但品牌很强, 这个价格合理吗”, “市场跌很多是不是错杀好公司”, and “朋友推荐天使轮值不值得投”.",
            "For stock-like decisions, start from 护城河、安全边际、定价权、管理层、能力圈五个维度系统评估, then convert them into price, downside, liquidity, and position-size constraints.",
            "For创业项目或天使轮, 先做能力圈检验（是否真正理解这门生意）, 再评估护城河、安全边际、流动性和 check size，不要直接被'商业模式大概能看懂'带过去。",
            "For比特币或类似高波动但无内在价值的投机标的, 明确写出安全边际不适用于赌博, 默认 `refuse` 或强烈警告, 不要假装还能给出正常估值与仓位建议。",
            "Do not fire on concept-only questions, short-term trading requests such as “MACD 和 KDJ 哪个更适合日内交易”, or pure scale-comparison analysis like “8000 人、200 亿营收算不算大公司” without a live size decision.",
            "For edge cases, use `partial_applicability` on franchise-style business investments and `refuse` on crypto-style speculative assets with no stable value anchor.",
            "Output a sizing band, hard constraints, downside checks, a concrete `next_action`, and `full_sizing / partial_applicability / refuse` for edge cases.",
        ]
    return [
        f"Use `{title}` when the scenario materially resembles the decision pattern in `{primary['label']}`.",
        "Do not fire on concept-only questions; confirm there is a live decision with in-scope boundary context.",
        "Verify the scenario already includes enough concrete context and disconfirming evidence to test the boundary before firing.",
    ]


def _build_scenario_families(
    *,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
) -> dict[str, Any]:
    semantic_family = identify_semantic_family(candidate_id)
    anchor_refs = [item["anchor_id"] for item in descriptors[:2] if item.get("anchor_id")]

    if _is_borrowed_value_family(semantic_family):
        profile = _borrowed_value_profile(semantic_family)
        return {
            "should_trigger": [
                {
                    "scenario_id": "borrow-source-pattern-for-live-decision",
                    "summary": f"{title} fires when {profile['trigger']}.",
                    "prompt_signals": profile["positive_signals"],
                    "boundary_reason": "There is a live current_decision and the user needs transferable judgment, not source explanation.",
                    "transfer_conditions": profile["transfer_conditions"],
                    "anti_conditions": profile["anti_conditions"],
                    "abuse_check": "clear",
                    "next_action_shape": f"Return {profile['output']} with verdict {profile['verdicts']}.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "source-understanding-only",
                    "summary": "Do not fire when the user only asks for summary, translation, fact lookup, biography introduction, author-position query, or stance commentary without a current decision.",
                    "prompt_signals": profile["negative_signals"],
                    "boundary_reason": "These are source/retrieval/QA tasks. The graph layer may extract them, but the judgment skill should not answer them as if they were transfer decisions.",
                    "transfer_conditions": [],
                    "anti_conditions": ["pure_summary_request", "pure_translation_request", "fact_lookup_request", "biography_intro_request", "author_position_query", "stance_commentary_without_user_decision"],
                    "abuse_check": "insufficient_context",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "partial-transfer-with-material-differences",
                    "summary": "Use partial transfer when the source pattern is useful but actor incentives, constraints, time horizon, institution, or resource conditions differ materially.",
                    "prompt_signals": ["有点像", "但时代不同", "能借鉴多少", "机制像但条件不一样"],
                    "boundary_reason": "Borrow the mechanism only after naming both fit and non-fit conditions.",
                    "transfer_conditions": profile["transfer_conditions"],
                    "anti_conditions": ["material_differences_not_named", *profile["anti_conditions"]],
                    "abuse_check": "insufficient_context",
                    "next_action_shape": "Name fit conditions, non-fit conditions, and a reversible next action before applying the source pattern.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "context-transfer-abuse",
                    "summary": "Refuse when the user wants to copy the book, historical case, competitor, big-company process, or past success without checking context fit.",
                    "prompt_signals": ["书里这么做成功了", "大公司都这么做", "竞品这样做我们也照搬", "过去成功所以继续照做", "不用看差异"],
                    "boundary_reason": "This is context_transfer_abuse: source material is being used as permission to bypass current-context judgment.",
                    "transfer_conditions": [],
                    "anti_conditions": ["context_transfer_abuse", *profile["anti_conditions"]],
                    "abuse_check": "context_transfer_abuse",
                    "next_action_shape": "Decline direct transfer and ask for current_decision, source_pattern, fit conditions, non-fit conditions, and disconfirming evidence.",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "single-case-overreach",
                    "summary": "Refuse when one attractive story or case is treated as enough proof for a current decision.",
                    "prompt_signals": ["只凭这个案例", "历史上有人成功", "一个故事就说明", "不用找反例"],
                    "boundary_reason": "This is single_case_overreach: one case cannot carry a transferable decision without mechanism and counterexample checks.",
                    "transfer_conditions": [],
                    "anti_conditions": ["single_case_overreach", *profile["anti_conditions"]],
                    "abuse_check": "single_case_overreach",
                    "next_action_shape": "Decline broad transfer; require at least mechanism mapping, current context fit, and counter-case search.",
                    "anchor_refs": anchor_refs,
                },
            ],
        }

    if semantic_family == "historical-case-consequence-judgment":
        return {
            "should_trigger": [
                {
                    "scenario_id": "historical-analogy-for-current-decision",
                    "summary": "The user wants to use one or more historical cases, such as 项羽和刘邦, to judge a current strategy, governance, investment, or 商业决策 where short-term strength may become long-term distrust.",
                    "prompt_signals": ["这个历史案例能不能类比", "项羽和刘邦", "商业决策", "历史类比", "哪个机制真的像我的处境"],
                    "boundary_reason": "There is a live decision and the user needs analogy transfer, not a history summary; the skill must compare mechanism, consequence, and transfer limit.",
                    "next_action_shape": "列出 case_pattern、机制链、transfer_limits、decision_warning 和 next_action。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "short-gain-long-cost-stress-test",
                    "summary": "The user sees a short-term gain but worries that the choice will create long-term retaliation, distrust, precedent, or second-order cost.",
                    "prompt_signals": ["短期强势但长期失信", "眼前收益很大", "以后会反噬", "短期赢一时", "长期代价", "连锁副作用"],
                    "boundary_reason": "The prompt is asking for a consequence chain, not a heroic-character judgment.",
                    "next_action_shape": "Build a choice -> constraint shift -> trust/retaliation/order-cost chain before recommending continue, pause, or narrow scope.",
                    "anchor_refs": anchor_refs,
                },
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "history-summary-only",
                    "summary": "Do not fire when the user only asks what happened, who someone was, when someone was born, or how to translate/explain a historical passage.",
                    "prompt_signals": ["讲讲这段历史", "这个人是谁", "司马迁是哪一年出生", "史实查询", "百科查询", "翻译一下", "古文翻译成现代汉语", "编年", "人物评价", "观点摘要"],
                    "boundary_reason": "史实查询、百科查询、翻译任务、编年、人物评价 and viewpoint summaries do not require decision-facing analogy judgment; 不应激活本 skill.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "suggestive-but-different-context",
                    "summary": "Use partial_apply when the historical pattern is suggestive but institutions, incentives, technology, or time horizon differ.",
                    "prompt_signals": ["有点像", "但时代不一样", "能借鉴多少", "关键角色的激励可能不同", "机制相似但条件不同"],
                    "boundary_reason": "The analogy may help but cannot decide the case by itself.",
                    "next_action_shape": "先列出相似点、关键差异和不可迁移部分，再给 partial_apply。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "single-anecdote-proof",
                    "summary": "Refuse when the user tries to prove a current decision only by citing one attractive historical anecdote.",
                    "prompt_signals": ["只记得一个史记故事", "历史上有人这么做成功了", "所以我们也照做", "不用再看差异"],
                    "boundary_reason": "One anecdote without transfer-limit analysis is unsafe evidence.",
                    "next_action_shape": "要求补充 current_decision、case_analogs、relevant_differences；证据不足时输出 do_not_apply。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "workflow-or-template-request",
                    "summary": "Refuse when the user asks for a meeting note, checklist, template, or mechanical workflow rather than historical consequence judgment.",
                    "prompt_signals": ["会议纪要模板", "流程清单", "表格模板", "帮我生成模板"],
                    "boundary_reason": "Template generation is a workflow or writing task, not a historical-case consequence decision.",
                    "next_action_shape": "不激活本 skill；route to workflow/template assistance if appropriate.",
                    "anchor_refs": anchor_refs,
                },
            ],
        }
    if semantic_family == "role-boundary-before-action":
        return {
            "should_trigger": [
                {
                    "scenario_id": "act-under-ambiguous-mandate",
                    "summary": "The user is considering an intervention, decision, escalation, or refusal under a role where authorization, cross-team responsibility boundaries, and long-term order costs are unclear.",
                    "prompt_signals": ["我有权限推动", "越过其他团队", "职责边界", "老板让我直接处理", "跨部门冲突", "我该不该介入", "这件事短期做了有效", "破坏长期秩序", "这算不算越界"],
                    "boundary_reason": "There is a live action and the user needs role-boundary arbitration, not a role definition; check authority, responsibility, stakeholders, and long-term order cost.",
                    "next_action_shape": "列出 role_boundary、authority_gap、order_cost，并给 act_with_boundary / ask_or_delegate / refuse。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "role-definition-or-template-only",
                    "summary": "Do not fire when the user only asks for a concept explanation, meeting template, or mechanical checklist.",
                    "prompt_signals": ["解释一下职责", "生成会议纪要模板", "给我一个流程清单"],
                    "boundary_reason": "No current action under uncertain authorization is being judged.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "urgent-but-authorization-unknown",
                    "summary": "Use ask_or_delegate when urgency is real but authorization facts are missing or the mandate belongs to another owner.",
                    "prompt_signals": ["事情很急", "不知道有没有授权", "可能要先斩后奏"],
                    "boundary_reason": "Urgency can justify a bounded temporary action but not silent overreach.",
                    "next_action_shape": "先给 low-regret bounded action，再要求补授权或升级给 owner。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "legal-or-ethics-final-opinion",
                    "summary": "Refuse to provide final legal, compliance, or ethics authorization when the facts require a responsible authority.",
                    "prompt_signals": ["这合法吗", "能不能规避合规", "不用告诉负责人"],
                    "boundary_reason": "The skill can structure the boundary question but cannot replace accountable review.",
                    "next_action_shape": "说明不能最终授权，列出需提交给合规/负责人确认的问题。",
                    "anchor_refs": anchor_refs,
                }
            ],
        }
    if semantic_family == "circle-of-competence":
        return {
            "should_trigger": [
                {
                    "scenario_id": "domain-transfer-boundary",
                    "summary": f"{title} fires when the user wants to enter a new domain and says things like “应该差不多能搞明白” or “我可以学”.",
                    "prompt_signals": ["我可以学", "应该差不多", "没做过但想试试"],
                    "boundary_reason": "This is a live ability-boundary decision, not a concept query or objective comparison.",
                    "next_action_shape": "区分可迁移能力与缺失的专业知识边界，给出圈内 / 边界 / 圈外判断。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "fomo-outside-circle",
                    "summary": "Use this family when the user leans on social proof like “大家都说这是好机会” instead of demonstrated understanding.",
                    "prompt_signals": ["大家都说这是好机会", "想投一点试试", "搞不太懂但能赚钱"],
                    "boundary_reason": "The skill should test independent understanding before any real commitment.",
                    "next_action_shape": "要求用户解释核心运作逻辑和失败路径，再决定 proceed / study_more / decline。",
                    "anchor_refs": anchor_refs,
                },
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "concept-or-comparison-query",
                    "summary": "Do not fire when the user only asks what circle of competence means or asks for an objective comparison such as Python vs Go.",
                    "prompt_signals": ["能力圈是什么概念", "Python 和 Go 哪个更适合"],
                    "boundary_reason": "These are concept learning or comparison tasks, not ability-boundary judgments.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "transferable-skill-vs-industry-gap",
                    "summary": "Use edge handling when the user has transferable general skill but lacks industry-specific experience.",
                    "prompt_signals": ["做了5年产品经理", "完全不同行业", "怕自己搞不定"],
                    "boundary_reason": "Part of the capability may transfer, but the industry-specific risk is still outside the circle.",
                    "next_action_shape": "拆出哪些能力在圈内、哪些行业知识在圈外，再决定是否先小规模试错。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "cannot-explain-business-clearly",
                    "summary": "Refuse an in-circle judgment when the user says “好像懂了，但说不清楚怎么变现”.",
                    "prompt_signals": ["说不清楚", "好像懂了", "怎么变现"],
                    "boundary_reason": "Cannot explain the business model clearly means the circle is not yet proven.",
                    "next_action_shape": "列出真正理解和不理解的部分，先 study_more 再决定是否投入。",
                    "anchor_refs": anchor_refs,
                }
            ],
        }
    if semantic_family == "invert-the-problem":
        return {
            "should_trigger": [
                {
                    "scenario_id": "failure-first-planning",
                    "summary": f"{title} fires when the user asks what could make a real plan fail or says the plan feels too optimistic.",
                    "prompt_signals": ["太乐观了", "最坏的情况是什么", "有什么漏洞"],
                    "boundary_reason": "The user is actively scanning failure paths before commitment.",
                    "next_action_shape": "列出失败模式、找茬清单和 first preventive action。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "team-red-team-review",
                    "summary": "Use this family when the team only sees opportunity but not threat and asks for a systematic red-team review.",
                    "prompt_signals": ["只看到了机会没看到威胁", "系统性找找茬"],
                    "boundary_reason": "This is failure-first challenge, not more ideation.",
                    "next_action_shape": "输出潜在威胁、失败模式、找茬清单和预防动作。",
                    "anchor_refs": anchor_refs,
                },
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "creative-brainstorming-only",
                    "summary": "Do not fire when the user needs creative ideation rather than risk avoidance.",
                    "prompt_signals": ["头脑风暴", "创意方向", "新点子"],
                    "boundary_reason": "Inversion is conservative and defensive; it is not the right tool for pure ideation.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "medium-stakes-personal-decision",
                    "summary": "Use partial_review when the user may need inversion, but only if they want to scan hidden failure modes rather than compare options.",
                    "prompt_signals": ["跳槽", "纠结", "有没有没看到的风险"],
                    "boundary_reason": "Personal decisions can fit inversion only when the failure-scan signal is explicit.",
                    "next_action_shape": "先确认是不是在做 failure scan，再决定 full_inversion / partial_review / defer。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "post-hoc-decoration",
                    "summary": "Refuse when the plan is already decided and the user only wants post-hoc decoration.",
                    "prompt_signals": ["已经决定了", "只是想再确认一下"],
                    "boundary_reason": "Inversion should change the decision path, not decorate a locked conclusion.",
                    "anchor_refs": anchor_refs,
                }
            ],
        }
    if semantic_family == "bias-self-audit":
        return {
            "should_trigger": [
                {
                    "scenario_id": "high-conviction-under-commitment",
                    "summary": f"{title} fires when the user already has a thesis and resists counterevidence under commitment pressure.",
                    "prompt_signals": ["反面意见我都不想听了", "这个逻辑不可能错", "明天就拍板"],
                    "boundary_reason": "A formed thesis exists and now needs counterevidence pressure-testing.",
                    "next_action_shape": "指出触发的偏误，要求最强反证和具体 mitigation step。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "supportive-evidence-only",
                    "summary": "Use this family when the user has only collected supportive evidence and wants to know whether the case is still rigorous.",
                    "prompt_signals": ["收集了很多支持我观点的数据", "有没有反面证据"],
                    "boundary_reason": "The user needs a deliberate search for disconfirming evidence before commitment hardens.",
                    "next_action_shape": "生成 strongest counter-evidence checklist 和下一步审计动作。",
                    "anchor_refs": anchor_refs,
                },
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "research-or-incident-mode",
                    "summary": "Do not fire on raw information collection or urgent incident triage.",
                    "prompt_signals": ["先帮我收集数据", "服务器突然宕机了"],
                    "boundary_reason": "There is no stable thesis to audit, or the situation is too urgent for reflective bias review.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "option-comparison-without-thesis",
                    "summary": "Use edge handling when the user has compared options but has not yet hardened into a single thesis.",
                    "prompt_signals": ["列了优缺点", "就是拿不定主意"],
                    "boundary_reason": "This may need partial bias review, but not a full audit unless a thesis already exists.",
                    "next_action_shape": "先确认 thesis 是否已形成，再决定 full_audit / partial_review / defer。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "historical-explanation-only",
                    "summary": "Refuse when the user only asks for Darwin or history explanations rather than auditing a live judgment.",
                    "prompt_signals": ["达尔文", "科学贡献", "历史故事"],
                    "boundary_reason": "This is knowledge inquiry, not an active anti-bias intervention.",
                    "anchor_refs": anchor_refs,
                }
            ],
        }
    if semantic_family == "role-boundary-before-action":
        return {
            "summary": (
                f"Initial extraction-backed draft for {title} now separates role-boundary arbitration from generic history analogy and workflow templates. "
                "It should trigger on prompts like “我有权限但担心越界”, “老板让我直接处理跨部门冲突”, and “不知道有没有授权但事情很急”, "
                "while refusing role-definition questions, meeting templates, and legal/compliance final opinions."
            ),
            "evidence_changes": [
                "Bound the draft to multi-file narrative role/authority anchors.",
                "Added scenario families for ambiguous mandate, template-only refusal, urgent authorization gaps, and legal/compliance refusal.",
            ],
            "open_gaps": [
                "Add real organizational cases that distinguish bounded temporary action from silent overreach.",
                "Validate whether ancient role-order evidence transfers safely to modern teams without literal hierarchy drift.",
            ],
        }
    if semantic_family == "value-assessment":
        return {
            "should_trigger": [
                {
                    "scenario_id": "price-vs-value-judgment",
                    "summary": f"{title} fires when the user asks whether the current price is justified by underlying business value.",
                    "prompt_signals": ["值不值这个价", "价格合理吗", "是不是高估了"],
                    "boundary_reason": "This is a live price-vs-value judgment, not a pure business-quality comparison.",
                    "next_action_shape": "先建立价值锚点与关键驱动，再判断低估 / 公允 / 高估，并决定是否交给 sizing。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "great-company-vs-ordinary-company",
                    "summary": "Use this family when the user asks why a great company is different from an ordinary one and the real answer depends on moat, pricing power, and unused pricing power.",
                    "prompt_signals": ["护城河", "提价客户不会跑", "和其他公司差在哪"],
                    "boundary_reason": "This is still value assessment because the user is probing the drivers that justify superior value, not merely comparing raw scale.",
                    "next_action_shape": "解释护城河、定价权、尚未利用的提价能力如何支撑更高质量的价值判断。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "panic-created-mispricing",
                    "summary": "Use this family when the market is panicking and the user asks whether a good business is now mispriced.",
                    "prompt_signals": ["市场恐慌", "是不是错杀", "现在是不是低估"],
                    "boundary_reason": "The decision hinges on whether price detached from value under temporary stress.",
                    "next_action_shape": "检查价值锚点是否稳定、当前价格是否失真，再决定 delegate_to_sizing / monitor_only。",
                    "anchor_refs": anchor_refs,
                },
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "short-term-trading-or-scale-comparison",
                    "summary": "Do not fire on short-term trading prompts or pure scale comparison without a live price judgment.",
                    "prompt_signals": ["日内交易", "MACD", "员工多少算大公司"],
                    "boundary_reason": "These prompts do not require value assessment anchored in intrinsic economics; short-term trading violates the long-term holding posture, and pure规模问题应转给 scale-advantage-analysis.",
                    "anchor_refs": anchor_refs,
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "private-or-angel-valuation",
                    "summary": "Use edge handling when the user evaluates a private business, franchise, or angel round where value logic partly applies but market benchmarks are weaker.",
                    "prompt_signals": ["加盟店", "天使轮", "这个估值有没有道理", "商业模式我大概能看懂", "值不值得投"],
                    "boundary_reason": "The user needs a defensible value anchor and an explicit 能力圈检验 before any sizing judgment can begin.",
                    "next_action_shape": "先做 `partial_applicability` 判断，验证商业模式、现金流、能力圈和回本逻辑，再决定是公允、偏贵还是根本没有价值锚点。",
                    "anchor_refs": anchor_refs,
                }
            ],
            "refusal": [
                {
                    "scenario_id": "speculative-asset-without-value-anchor",
                    "summary": "Refuse normal valuation language when the asset lacks a stable intrinsic-value anchor.",
                    "prompt_signals": ["比特币", "memecoin", "最近涨很多"],
                    "boundary_reason": "Speculation cannot be silently relabeled as intrinsic value.",
                    "next_action_shape": "明确输出 no_value_anchor、refuse 和 decline，不要伪造正常估值结论。",
                    "anchor_refs": anchor_refs,
                }
            ],
        }
    if semantic_family == "margin-of-safety-sizing":
        return {
            "should_trigger": [
                {
                    "scenario_id": "live-price-vs-value-decision",
                    "summary": f"{title} fires when the user asks whether the current price is reasonable and whether the safety margin is enough.",
                    "prompt_signals": ["价格合理吗", "安全边际够不够", "值不值得买"],
                    "boundary_reason": "This is a live price-vs-value decision under uncertainty.",
                    "next_action_shape": "从护城河、安全边际、定价权、管理层、能力圈五维评估，再转成 sizing constraints。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "panic-mispricing-check",
                    "summary": "Use this family when the market is panicking and the user asks whether good companies are being mispriced.",
                    "prompt_signals": ["市场跌了很多", "好公司可能被错杀了", "现在是不是机会"],
                    "boundary_reason": "The user is testing value against price in a live market dislocation.",
                    "next_action_shape": "检查内在价值与价格差距，再落到 downside / liquidity / position-size constraints。",
                    "anchor_refs": anchor_refs,
                },
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "short-term-trading-request",
                    "summary": "Do not fire on short-term trading prompts such as MACD or KDJ selection.",
                    "prompt_signals": ["日内交易", "MACD", "KDJ"],
                    "boundary_reason": "Margin-of-safety sizing is for long-horizon value decisions, not short-term trading setups.",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "pure-scale-comparison",
                    "summary": "Do not fire on business scale comparison without a live price or capital decision.",
                    "prompt_signals": ["员工8000人", "营收200亿", "比竞争对手强在哪"],
                    "boundary_reason": "This is comparative business analysis, not a live sizing or value decision.",
                    "anchor_refs": anchor_refs,
                },
            ],
            "edge_case": [
                {
                    "scenario_id": "private-business-check",
                    "summary": "Use partial applicability on franchise or private-business checks where value logic applies but the asset is not a public equity.",
                    "prompt_signals": ["加盟品牌", "加盟费不便宜", "花200万开店"],
                    "boundary_reason": "The framework partially applies, but the asset type and liquidity differ from a stock-like decision.",
                    "next_action_shape": "先判断是否真正理解生意，再检查回本周期、流动性和 check size。",
                    "anchor_refs": anchor_refs,
                },
                {
                    "scenario_id": "angel-check-under-uncertainty",
                    "summary": "Use partial applicability when the user considers an angel or startup check and only vaguely understands the business.",
                    "prompt_signals": ["天使轮", "商业模式我大概能看懂", "值不值得投"],
                    "boundary_reason": "The decision is real, but understanding and downside math may still be shallow.",
                    "next_action_shape": "先做能力圈检验，再评估护城河、安全边际、流动性和 sizing band。",
                    "anchor_refs": anchor_refs,
                },
            ],
            "refusal": [
                {
                    "scenario_id": "speculative-asset-without-value-anchor",
                    "summary": "Refuse normal sizing advice for speculative assets such as Bitcoin that lack a stable value anchor.",
                    "prompt_signals": ["比特币", "最近涨了很多", "值不值得买"],
                    "boundary_reason": "Safety margin does not apply cleanly to gambling-like setups without stable intrinsic value.",
                    "next_action_shape": "输出强烈警告或 refuse，而不是假装可以给正常估值和仓位建议。",
                    "anchor_refs": anchor_refs,
                }
            ],
        }
    return {
        "should_trigger": [
            {
                "scenario_id": "live-decision-window",
                "summary": f"{title} fires when the scenario contains a live decision this principle can materially improve.",
                "prompt_signals": ["需要做决定", "如何判断", "下一步怎么做"],
                "boundary_reason": "The scenario already contains a concrete decision boundary.",
                "next_action_shape": "输出与该原则相匹配的具体 next action。",
                "anchor_refs": anchor_refs,
            }
        ],
        "should_not_trigger": [
            {
                "scenario_id": "concept-query-only",
                "summary": "Do not fire on concept-only questions without a live decision.",
                "prompt_signals": ["是什么概念", "怎么定义", "解释一下"],
                "boundary_reason": "The user is learning a concept, not applying a decision principle.",
                "anchor_refs": anchor_refs,
            }
        ],
        "edge_case": [
            {
                "scenario_id": "partial-fit-boundary",
                "summary": "Use edge handling when the principle partially fits but the boundary is still ambiguous.",
                "prompt_signals": ["有点像", "不确定是否适用"],
                "boundary_reason": "The decision pattern overlaps, but important context is still missing.",
                "next_action_shape": "先补关键上下文，再决定 full_apply / partial_review / defer。",
                "anchor_refs": anchor_refs,
            }
        ],
        "refusal": [
            {
                "scenario_id": "missing-decision-context",
                "summary": "Refuse when the scenario lacks enough decision context or disconfirming evidence.",
                "prompt_signals": ["信息还不够", "只是先了解一下"],
                "boundary_reason": "The principle should not fire without a stable decision boundary.",
                "anchor_refs": anchor_refs,
            }
        ],
    }


def _write_trace_doc(
    *,
    bundle_root: Path,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
) -> str:
    trace_id = f"{candidate_id}-source-smoke"
    trace_path = Path("traces") / "canonical" / f"{trace_id}.yaml"
    primary = descriptors[0]
    trace_doc = {
        "trace_id": trace_id,
        "title": f"{title} Smoke Trace",
        "summary": primary["snippet"],
        "scenario_excerpt": primary["snippet"],
        "evidence_anchor_ids": [item["anchor_id"] for item in descriptors[:3]],
        "related_skills": [candidate_id],
    }
    _write_yaml(bundle_root / trace_path, trace_doc)
    return trace_path.as_posix()


def _build_revision_seed(*, candidate_id: str, title: str) -> dict[str, Any]:
    semantic_family = identify_semantic_family(candidate_id)
    if _is_borrowed_value_family(semantic_family):
        return {
            "summary": (
                f"Initial borrowed-value draft for {title} created from graph/source evidence. "
                "The revision scope is deliberately not summary quality; it checks whether a source pattern can improve a live decision without context-transfer abuse."
            ),
            "evidence_changes": [
                "Added source-shape detection for biography/history/case/argument-heavy materials.",
                "Bound transfer_conditions and anti_conditions into contract and usage scenario families.",
                "Added refusal coverage for summary, translation, fact lookup, biography introduction, author-position query, stance commentary, single_case_overreach, and context_transfer_abuse.",
            ],
            "open_gaps": [
                "Replace smoke cases with external human-written borrowing scenarios for stronger usage evidence.",
                "Add more cross-domain counter-cases before using the pattern in high-stakes contexts.",
            ],
        }
    if semantic_family == "circle-of-competence":
        return {
            "summary": (
                f"Initial extraction-backed draft for {title} now distinguishes real circle-of-competence judgments from pure comparison requests: "
                "“朋友拉我投餐饮连锁, 我应该差不多能搞明白” should trigger, but “Python 和 Go 哪个更适合做微服务开发” and already-in-circle senior architecture work should not. "
                "对纯客观技术比较不应激活本 skill, 因为那不是在判断自己是否处于能力圈外."
            ),
            "evidence_changes": [
                "Bound the draft to graph/source double anchoring.",
                "Attached one canonical smoke trace and one smoke case per evaluation subset.",
            ],
            "open_gaps": [
                "Add more real cases that separate transferable product skill from missing industry knowledge.",
                "Validate refusal language on cross-industry career moves and first-time real-money investing.",
            ],
        }
    if semantic_family == "invert-the-problem":
        return {
            "summary": (
                f"Initial extraction-backed draft for {title} now distinguishes failure-first planning from pure ideation: "
                "“产品上市计划怎么彻底失败” and “进入东南亚市场最坏会怎样” should trigger, but “给我几个新产品创意方向” should not. "
                "“团队只看到了机会没看到威胁, 能不能系统性地找找方案的茬” should also trigger and produce 找茬清单与预防动作. "
                "跳槽这类职业决策只有在用户明确要系统性评估跳槽风险和失败模式时才应激活；如果只是比较两个选项优劣, 更适合一般决策辅助。 "
                "健身计划这类个人日常目标可以做轻量 pre-mortem, 但不应被展开成重大决策级别的重型风险框架。 "
                "对纯创意发散不应激活本 skill, 因为那不是失败分析或风险规避；逆向思维天然偏向保守和防御, 不适合创意场景, 需要创意发散时不适用."
            ),
            "evidence_changes": [
                "Bound the draft to graph/source double anchoring.",
                "Attached one canonical smoke trace and one smoke case per evaluation subset.",
            ],
            "open_gaps": [
                "Add more cases covering investment pre-mortems, team red-team reviews, and low-stakes personal plans.",
                "Verify edge handling when the user has a decision but is still only比较选项优劣 rather than scanning for failure modes.",
            ],
        }
    if semantic_family == "bias-self-audit":
        return {
            "summary": (
                f"Initial extraction-backed draft for {title} now separates live bias-audit windows from adjacent but out-of-scope requests: "
                "“大家都同意明天就拍板” and “只收集了支持观点的数据” should trigger, while “收集行业数据”, “达尔文历史贡献解释”, and “服务器突然宕机了先排障” should not. "
                "对紧急故障处置不应激活本 skill, 因为这时不适合先做偏误审计."
            ),
            "evidence_changes": [
                "Bound the draft to graph/source double anchoring.",
                "Attached one canonical smoke trace and one smoke case per evaluation subset.",
            ],
            "open_gaps": [
                "Add more real cases that distinguish formed thesis review from undecided option comparison.",
                "Verify that every audit output ends with a concrete next action rather than generic caution.",
            ],
        }
    if semantic_family == "value-assessment":
        return {
            "summary": (
                f"Initial extraction-backed draft for {title} now separates value judgment from final sizing: "
                "“品牌很强但价格不便宜, 值不值这个价”, “市场恐慌是不是错杀好公司”, “这种公司和其他公司到底差在哪”, and “这个天使轮估值到底有没有道理” should trigger, "
                "while “MACD 和 KDJ 哪个更适合日内交易”, pure safety-margin definitions, and pure规模比较 should not. "
                "加盟店和天使轮默认只到 `partial_applicability`, 先做能力圈检验；而比特币这类没有稳定内在价值锚点的标的应直接 `refuse`. "
                "纯规模和竞争格局问题应转给 `scale-advantage-analysis`, 而不是冒充成价值判断；短线交易也不适用, 因为这套框架面向长期持有."
            ),
            "evidence_changes": [
                "Bound the draft to graph/source double anchoring.",
                "Attached one canonical smoke trace and one smoke case per evaluation subset.",
            ],
            "open_gaps": [
                "Add more real cases covering franchise economics, private-business valuations, and panic-market dislocations.",
                "Verify that every valuation output names a defensible value anchor before handing off to sizing.",
            ],
        }
    if semantic_family == "margin-of-safety-sizing":
        return {
            "summary": (
                f"Initial extraction-backed draft for {title} now ties valuation language to live sizing decisions: "
                "“市盈率25倍不算便宜但品牌很强, 这个价格合理吗” and “市场恐慌是不是把好公司错杀了” should trigger, "
                "while “MACD 和 KDJ 哪个更适合日内交易”, “8000 人和 200 亿营收算不算大公司”, and pure safety-margin definitions should not."
            ),
            "evidence_changes": [
                "Bound the draft to graph/source double anchoring.",
                "Attached one canonical smoke trace and one smoke case per evaluation subset.",
            ],
            "open_gaps": [
                "Add more real cases covering private-business checks, franchise economics, and angel-round uncertainty.",
                "Verify that every sizing output connects price, downside, liquidity, and position-size constraints in one recommendation.",
            ],
        }
    return {
        "summary": (
            f"Initial extraction-backed draft for {title} created from provenance-rich graph evidence."
        ),
        "evidence_changes": [
            "Bound the draft to graph/source double anchoring.",
            "Attached one canonical smoke trace and one smoke case per evaluation subset.",
        ],
        "open_gaps": [
            "Confirm whether the current trigger symbols are specific enough for production use.",
            "Replace smoke evaluation with real domain cases before publication.",
        ],
    }


def _write_eval_docs(
    *,
    bundle_root: Path,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    primary = descriptors[0]
    semantic_family = identify_semantic_family(candidate_id)
    subsets = {}
    for subset_name, scenario_suffix in (
        ("real_decisions", "real_decision_smoke"),
        ("synthetic_adversarial", "adversarial_smoke"),
        ("out_of_distribution", "ood_smoke"),
    ):
        case_id = f"{candidate_id}-{scenario_suffix}"
        relative_path = Path("evaluation") / subset_name / f"{case_id}.yaml"
        case_doc = {
            "case_id": case_id,
            "skill_id": candidate_id,
            "title": f"{title} {subset_name} smoke case",
            "input_scenario": {
                "scenario": primary["snippet"],
                "decision_goal": f"Decide whether `{title}` should fire.",
                "current_constraints": [
                    f"Confirm `{contract['trigger']['patterns'][0]}` is truly present.",
                ],
            },
            "expected_behavior": {
                "verdict": "apply",
                "minimum_confidence": "medium",
            },
            "evidence_anchor_ids": [item["anchor_id"] for item in descriptors[:3]],
            "evaluation_mode": "auto_smoke_prefill",
        }
        _write_yaml(bundle_root / relative_path, case_doc)
        subsets[subset_name] = {
            "cases": [relative_path.as_posix()],
            "passed": 1,
            "total": 1,
            "threshold": 1.0,
            "status": "under_evaluation",
        }
    key_failure_modes = [
        f"If `{contract['boundary']['do_not_fire_when'][0]}` remains true, defer the skill instead of firing.",
        f"If `{contract['boundary']['fails_when'][0]}` is observed, treat the evidence as conflicting.",
    ]
    if _is_borrowed_value_family(semantic_family):
        key_failure_modes = [
            "Do not fire on pure summary, translation, fact lookup, biography introduction, author-position query, or stance commentary without a user decision; route those to source/retrieval paths.",
            "Do not let source admiration become context_transfer_abuse: copying a book, historical case, competitor, big-company process, or past success without current fit must be refused.",
            "Do not accept single_case_overreach; require mechanism mapping, transfer_conditions, anti_conditions, and counter-case or disconfirming evidence before transfer.",
        ]
    elif semantic_family == "circle-of-competence":
        key_failure_modes = [
            "Do not confuse product familiarity, title prestige, or transferable general ability with demonstrated domain understanding.",
            "Do not fire on concept-only questions, proven in-circle operators with长期成功记录 in the same domain, or objective technology-comparison requests like “Python 和 Go 哪个更适合做微服务开发”.",
        ]
    elif semantic_family == "invert-the-problem":
        key_failure_modes = [
            "Do not let inversion collapse into generic brainstorming; it must surface concrete failure factors, 潜在威胁, 找茬清单, and avoid-rules when the team says it only sees opportunity but not threat.",
            "Do not fire on concept-only requests, pure idea-generation sessions, or 跳槽这类只是在比较两个选项优劣的场景 where the user is not actually asking for failure analysis.",
            "For健身计划等个人日常目标, use a lightweight pre-mortem / partial_review posture instead of a重大决策级别的重型风险框架.",
        ]
    elif semantic_family == "bias-self-audit":
        key_failure_modes = [
            "Do not treat 达尔文历史/科学知识查询, market-data collection like “先帮我收集新能源行业数据”, or urgent incident response like “服务器突然宕机了” as if they already contain a formed thesis to audit.",
            "When the user says everyone agrees, plans to拍板 tomorrow, or has only collected supportive evidence, force explicit counter-evidence, mitigation steps, and a concrete next action; if the user has not formed any thesis yet, do not start证伪. 对紧急决策场景不应激活, 因为系统性地搜索反面证据不现实。",
        ]
    elif semantic_family == "role-boundary-before-action":
        key_failure_modes = [
            "Do not fire on role definitions, meeting templates, or mechanical checklist requests; the skill requires a live proposed action under uncertain authorization.",
            "Do not give a final legal, compliance, or ethics authorization; structure the boundary question and route to accountable review.",
            "Do not let urgency justify silent overreach; if authorization facts are missing, use ask_or_delegate or a bounded temporary action.",
        ]
    elif semantic_family == "value-assessment":
        key_failure_modes = [
            "Do not let value assessment collapse into vague praise about quality; name the actual value anchor and test whether price is justified by it.",
            "Do not fire on short-term trading, pure scale-comparison analysis, or speculative assets that lack a stable intrinsic-value basis.",
            "When the case includes a real capital-allocation question, hand off to sizing explicitly instead of pretending valuation alone answered the position-size decision; for加盟店、私有生意、天使轮等边界案例, mark `partial_applicability` before continuing.",
        ]
    elif semantic_family == "margin-of-safety-sizing":
        key_failure_modes = [
            "Do not stop at value language like moat, pricing power, or quality; convert prompts like “价格合理吗”“安全边际够不够” into downside, liquidity, and position-size constraints.",
            "Do not fire on short-term trading like “MACD 和 KDJ 哪个更好用”, pure scale-comparison analysis focused on 规模和竞争格局 rather than value, or speculative assets with no stable value anchor.",
        ]

    return {
        "kiu_test": {
            "trigger_test": "pass",
            "fire_test": "pending",
            "boundary_test": "pass",
        },
        "subsets": subsets,
        "key_failure_modes": key_failure_modes,
        "references": {
            "evaluation_root": "../../../evaluation",
            "prefill_mode": "extraction_smoke",
        },
    }


def _build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if not edge.get("from") or not edge.get("to"):
            continue
        adjacency.setdefault(edge["from"], []).append(edge)
        adjacency.setdefault(edge["to"], []).append(edge)
    return adjacency


def _copy_source_files(
    *,
    source_chunks_doc: dict[str, Any],
    source_chunks_path: Path,
    bundle_root: Path,
    source_id: str,
) -> tuple[dict[str, str], str]:
    source_file_values = _collect_source_file_values(source_chunks_doc)
    source_root_value = str(source_chunks_doc.get("source_file", ""))
    source_root_path = _resolve_source_file(
        source_file=source_root_value,
        source_chunks_path=source_chunks_path,
    )
    source_file_map: dict[str, str] = {}
    multiple_files = len(source_file_values) > 1 or source_root_path.is_dir()

    for source_file_value in source_file_values:
        source_path = _resolve_source_file(
            source_file=source_file_value,
            source_chunks_path=source_chunks_path,
        )
        if source_path.is_dir():
            continue
        if multiple_files:
            try:
                relative_under_root = source_path.resolve().relative_to(source_root_path.resolve())
            except ValueError:
                relative_under_root = Path(source_path.name)
            copied_relpath = Path("sources") / source_id / relative_under_root
        else:
            copied_relpath = Path("sources") / source_path.name
        destination = bundle_root / copied_relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        _register_source_file_mapping(
            source_file_map=source_file_map,
            original_value=source_file_value,
            resolved_path=source_path,
            copied_relpath=copied_relpath.as_posix(),
        )

    copied_source_root = (Path("sources") / source_id).as_posix() if multiple_files else next(iter(source_file_map.values()))
    if source_root_path.is_dir():
        _register_source_file_mapping(
            source_file_map=source_file_map,
            original_value=source_root_value,
            resolved_path=source_root_path,
            copied_relpath=copied_source_root,
        )
    return source_file_map, copied_source_root


def _collect_source_file_values(source_chunks_doc: dict[str, Any]) -> list[str]:
    values: list[str] = []
    if isinstance(source_chunks_doc.get("source_files"), list):
        values.extend(
            item for item in source_chunks_doc["source_files"] if isinstance(item, str) and item
        )
    for chunk in source_chunks_doc.get("chunks", []):
        if isinstance(chunk, dict) and isinstance(chunk.get("source_file"), str):
            values.append(chunk["source_file"])
    if not values and isinstance(source_chunks_doc.get("source_file"), str):
        values.append(source_chunks_doc["source_file"])
    return sorted(set(values))


def _register_source_file_mapping(
    *,
    source_file_map: dict[str, str],
    original_value: str,
    resolved_path: Path,
    copied_relpath: str,
) -> None:
    source_file_map[original_value] = copied_relpath
    source_file_map[resolved_path.as_posix()] = copied_relpath
    try:
        source_file_map[resolved_path.resolve().relative_to(REPO_ROOT).as_posix()] = copied_relpath
    except ValueError:
        pass


def _rewrite_source_file_value(
    source_file: str,
    *,
    source_file_map: dict[str, str],
    default: str | None = None,
) -> str:
    if source_file in source_file_map:
        return source_file_map[source_file]
    resolved = Path(source_file)
    if resolved.as_posix() in source_file_map:
        return source_file_map[resolved.as_posix()]
    try:
        resolved_value = resolved.resolve().as_posix()
    except OSError:
        resolved_value = resolved.as_posix()
    if resolved_value in source_file_map:
        return source_file_map[resolved_value]
    return default or source_file


def _resolve_source_file(
    *,
    source_file: str,
    source_chunks_path: Path,
) -> Path:
    candidate = Path(source_file)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    sibling_candidate = source_chunks_path.parent / candidate
    if sibling_candidate.exists():
        return sibling_candidate
    raise FileNotFoundError(f"unable to resolve source file for extraction bundle: {source_file}")


def _read_snippet(
    *,
    bundle_root: Path,
    relative_path: str,
    line_start: int,
    line_end: int,
) -> str:
    path = bundle_root / relative_path
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = " ".join(
        line.strip()
        for line in lines[line_start - 1 : line_end]
        if line.strip()
    )
    return excerpt[:220] if len(excerpt) > 220 else excerpt


def _derive_candidate_id(node: dict[str, Any]) -> str:
    node_type = str(node.get("type", ""))
    if node_type == "counter_example_signal":
        section_title = str(node.get("section_title") or "").strip()
        if section_title:
            return _slugify(f"{section_title}-counter-example")
    return _slugify(str(node.get("label", node["id"])))


def _slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text).strip("-").lower()
    normalized = normalized.replace("--", "-")
    return normalized or "extraction-candidate"


def _humanize_title(raw: str) -> str:
    text = raw.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in text.split()) or raw


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
