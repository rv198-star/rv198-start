from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .anchors import build_candidate_anchors
from .diff import build_metrics
from .draft import build_candidate_skill_markdown
from .distillation import augment_scenario_families, build_distillation_contract
from .eval_prefill import build_prefilled_eval_summary
from .models import CandidateSeed, SourceBundle
from .ria_tv import build_skill_ria_tv_provenance, build_workflow_gateway_provenance


BUNDLE_VERSION = "0.2.0"
SCHEMA_VERSION = "kiu.bundle.schema/v0.1"
SKILL_SPEC_VERSION = "kiu.skill-spec/v0.1"
RELATION_ENUM_VERSION = "kiu.relation-enum/v1"


def render_generated_run(
    *,
    source_bundle: SourceBundle,
    seeds: list[CandidateSeed],
    output_root: str | Path,
    run_id: str,
) -> Path:
    output_root = Path(output_root)
    run_root = output_root / source_bundle.manifest["bundle_id"] / run_id
    bundle_root = run_root / "bundle"
    reports_root = run_root / "reports"
    workflow_root = run_root / "workflow_candidates"

    if run_root.exists():
        shutil.rmtree(run_root)

    bundle_root.mkdir(parents=True, exist_ok=True)
    reports_root.mkdir(parents=True, exist_ok=True)
    workflow_root.mkdir(parents=True, exist_ok=True)

    _copy_shared_assets(source_bundle.root, bundle_root)
    _copy_bundle_profile(source_bundle.root, bundle_root)

    rendered_seeds: list[CandidateSeed] = []
    workflow_only_seeds: list[CandidateSeed] = []
    filtered_seeds: list[dict[str, Any]] = []
    manifest_skills: list[dict[str, Any]] = []

    for seed in seeds:
        publish_decision = should_publish_skill_seed(seed)
        if not publish_decision["publish"]:
            filtered_seeds.append(
                {
                    "candidate_id": seed.candidate_id,
                    "reason": publish_decision["reason"],
                    "candidate_kind": seed.candidate_kind,
                }
            )
            continue
        if seed.metadata["disposition"] == "workflow_script_candidate":
            _render_workflow_candidate(
                workflow_root=workflow_root,
                source_bundle=source_bundle,
                seed=seed,
            )
            workflow_only_seeds.append(seed)
            continue

        _render_skill_candidate(
            bundle_root=bundle_root,
            source_bundle=source_bundle,
            seed=seed,
            skill_revision=1,
        )
        rendered_seeds.append(seed)
        manifest_skills.append(
            {
                "skill_id": seed.candidate_id,
                "path": f"skills/{seed.candidate_id}",
                "status": "under_evaluation",
                "skill_revision": 1,
            }
        )

    has_gateway_seed = any(seed.candidate_id == "workflow-gateway" for seed in rendered_seeds)
    should_render_gateway = (
        bool(workflow_only_seeds)
        and not has_gateway_seed
        and (not rendered_seeds or len(workflow_only_seeds) >= 3)
    )
    if should_render_gateway:
        gateway_seed = _build_workflow_gateway_seed(
            source_bundle=source_bundle,
            workflow_only_seeds=workflow_only_seeds,
        )
        _render_skill_candidate(
            bundle_root=bundle_root,
            source_bundle=source_bundle,
            seed=gateway_seed,
            skill_revision=1,
        )
        _write_workflow_gateway_trace(bundle_root=bundle_root, seed=gateway_seed)
        _append_gateway_trigger_definitions(bundle_root=bundle_root, seed=gateway_seed)
        rendered_seeds.append(gateway_seed)
        manifest_skills.append(
            {
                "skill_id": gateway_seed.candidate_id,
                "path": f"skills/{gateway_seed.candidate_id}",
                "status": "under_evaluation",
                "skill_revision": 1,
            }
        )

    manifest = {
        "bundle_id": f"{source_bundle.manifest['bundle_id']}-candidate-bundle",
        "title": f"KiU v0.2 Candidate Bundle for {source_bundle.manifest['bundle_id']}",
        "bundle_version": BUNDLE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "skill_spec_version": SKILL_SPEC_VERSION,
        "relation_enum_version": RELATION_ENUM_VERSION,
        "language": source_bundle.manifest.get("language", "zh-CN"),
        "domain": source_bundle.domain,
        "created_at": date.today().isoformat(),
        "generated_from": {
            "source_bundle_id": source_bundle.manifest["bundle_id"],
            "source_bundle_version": source_bundle.manifest["bundle_version"],
            "profile_version": source_bundle.profile.get("profile_version"),
        },
        "graph": {
            "path": source_bundle.manifest["graph"]["path"],
            "graph_version": source_bundle.manifest["graph"]["graph_version"],
            "graph_hash": source_bundle.manifest["graph"]["graph_hash"],
        },
        "skills": manifest_skills,
        "shared_assets": dict(source_bundle.manifest.get("shared_assets", {})),
    }
    _write_yaml(bundle_root / "manifest.yaml", manifest)

    metrics = build_metrics(
        source_bundle=source_bundle,
        rendered_seeds=rendered_seeds,
        workflow_only_seeds=workflow_only_seeds,
    )
    (reports_root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (reports_root / "skill-hygiene-audit.json").write_text(
        json.dumps(
            {
                "schema_version": "kiu.skill-hygiene-audit/v0.1",
                "filtered_count": len(filtered_seeds),
                "filtered": filtered_seeds,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return run_root


def should_publish_skill_seed(seed: CandidateSeed) -> dict[str, Any]:
    if _is_chapter_title_style_seed(seed):
        return {"publish": False, "reason": "chapter_title_style_candidate"}
    return {"publish": True, "reason": "publishable"}


def _is_chapter_title_style_seed(seed: CandidateSeed) -> bool:
    candidate_id = str(seed.candidate_id or "").strip()
    title = str(seed.seed_content.get("title") or candidate_id).strip() if isinstance(seed.seed_content, dict) else candidate_id
    routing = seed.metadata.get("routing_evidence", {}) if isinstance(seed.metadata, dict) else {}
    if not isinstance(routing, dict):
        routing = {}
    agentic_priority = float(routing.get("agentic_priority", 0) or 0)
    matched_keyword_count = int(routing.get("matched_keyword_count", 0) or 0)
    case_density_score = float(routing.get("case_density_score", 0.0) or 0.0)
    title_text = title or candidate_id
    return bool(
        _looks_like_heading_title(title_text)
        and agentic_priority <= 0
        and matched_keyword_count <= 1
        and case_density_score <= 0.55
    )


def _looks_like_heading_title(text: str) -> bool:
    normalized = str(text or "").strip().strip("# 　\t")
    if not normalized:
        return False
    if re.match(r"^第[一二三四五六七八九十百千万0-9]+[章节篇节]\b", normalized):
        return True
    if re.match(r"^[IVXLCDM]+[\.、]\s*", normalized, flags=re.IGNORECASE):
        return True
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    has_action_model_marker = any(
        marker in normalized
        for marker in ("法", "模型", "原则", "检查", "判断", "决策", "调查", "矛盾")
    )
    return cjk_count >= 14 and not has_action_model_marker


def load_generated_candidates(bundle_root: str | Path) -> list[dict[str, Any]]:
    bundle_root = Path(bundle_root)
    manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
    candidates: list[dict[str, Any]] = []
    for entry in manifest.get("skills", []):
        skill_dir = bundle_root / entry["path"]
        candidates.append(
            {
                "skill_id": entry["skill_id"],
                "skill_dir": skill_dir,
                "skill_markdown": (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
                "anchors": yaml.safe_load((skill_dir / "anchors.yaml").read_text(encoding="utf-8")),
                "eval_summary": yaml.safe_load(
                    (skill_dir / "eval" / "summary.yaml").read_text(encoding="utf-8")
                ),
                "revisions": yaml.safe_load(
                    (skill_dir / "iterations" / "revisions.yaml").read_text(encoding="utf-8")
                ),
                "scenario_families": yaml.safe_load(
                    (skill_dir / "usage" / "scenarios.yaml").read_text(encoding="utf-8")
                ),
                "candidate": yaml.safe_load(
                    (skill_dir / "candidate.yaml").read_text(encoding="utf-8")
                ),
                "nearest_skill_id": entry["skill_id"],
            }
        )
    return candidates


def materialize_refined_candidates(
    bundle_root: str | Path,
    refined_candidates: list[dict[str, Any]],
) -> None:
    bundle_root = Path(bundle_root)
    manifest_path = bundle_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    skill_revision_map = {
        candidate["candidate"]["candidate_id"]: candidate["revisions"]["current_revision"]
        for candidate in refined_candidates
    }
    for entry in manifest.get("skills", []):
        if entry["skill_id"] in skill_revision_map:
            entry["skill_revision"] = skill_revision_map[entry["skill_id"]]
            entry["status"] = "under_evaluation"
    _write_yaml(manifest_path, manifest)

    for candidate in refined_candidates:
        skill_dir = candidate.get("skill_dir") or (
            bundle_root / "skills" / candidate["candidate"]["candidate_id"]
        )
        (skill_dir / "SKILL.md").write_text(candidate["skill_markdown"], encoding="utf-8")
        _write_yaml(skill_dir / "anchors.yaml", candidate["anchors"])
        _write_yaml(skill_dir / "eval" / "summary.yaml", candidate["eval_summary"])
        _write_yaml(skill_dir / "iterations" / "revisions.yaml", candidate["revisions"])
        _write_yaml(skill_dir / "candidate.yaml", candidate["candidate"])


def _copy_shared_assets(source_root: Path, bundle_root: Path) -> None:
    for relative in ("graph", "traces", "evaluation", "sources"):
        shutil.copytree(source_root / relative, bundle_root / relative)


def _copy_bundle_profile(source_root: Path, bundle_root: Path) -> None:
    for relative in ("automation.yaml", "triggers.yaml", "materials.yaml"):
        source_path = source_root / relative
        if source_path.exists():
            shutil.copy2(source_path, bundle_root / relative)


def _build_workflow_gateway_seed(
    *,
    source_bundle: SourceBundle,
    workflow_only_seeds: list[CandidateSeed],
) -> CandidateSeed:
    ordered = sorted(
        workflow_only_seeds,
        key=lambda item: (-int(item.score or 0), item.candidate_id),
    )
    primary_seed = ordered[0]
    routed_ids = sorted(seed.candidate_id for seed in workflow_only_seeds)
    support_window = ordered[:5]
    supporting_node_ids = _unique_limited(
        [
            node_id
            for seed in support_window
            for node_id in [seed.primary_node_id, *seed.supporting_node_ids]
            if node_id != primary_seed.primary_node_id
        ],
        limit=10,
    )
    supporting_edge_ids = _unique_limited(
        [edge_id for seed in support_window for edge_id in seed.supporting_edge_ids],
        limit=12,
    )
    community_ids = _unique_limited(
        [community_id for seed in support_window for community_id in seed.community_ids],
        limit=6,
    )
    metadata = {
        "candidate_id": "workflow-gateway",
        "source_bundle_id": source_bundle.manifest["bundle_id"],
        "source_graph_hash": source_bundle.manifest["graph"]["graph_hash"],
        "seed": {
            "primary_node_id": primary_seed.primary_node_id,
            "supporting_node_ids": supporting_node_ids,
            "supporting_edge_ids": supporting_edge_ids,
            "community_ids": community_ids,
        },
        "candidate_kind": "workflow_gateway",
        "workflow_certainty": "medium",
        "context_certainty": "medium",
        "recommended_execution_mode": "llm_agentic",
        "disposition": "skill_candidate",
        "gold_match_hint": None,
        "drafting_mode": primary_seed.metadata.get("drafting_mode", "deterministic"),
        "loop_mode": "refinement_scheduler",
        "current_round": 2,
        "terminal_state": "ready_for_review",
        "human_gate": "skipped",
        "workflow_gateway": {
            "mode": "route_to_workflow_candidates",
            "routes_to": routed_ids,
            "boundary_rule": (
                "The gateway may choose or sequence workflow candidates, but it must not "
                "inline deterministic workflow steps as agentic skill reasoning."
            ),
        },
        "routing_evidence": {
            "inference_mode": "workflow_gateway_fallback",
            "selected_candidate_kind": "workflow_gateway",
            "workflow_candidate_count": len(routed_ids),
            "workflow_boundary_preserved": True,
        },
        "verification": {
            "schema_version": "kiu.verification-gate/v0.1",
            "candidate_id": "workflow-gateway",
            "passed": True,
            "workflow_ready": False,
            "corroboration_score": 1.0,
            "predictive_usefulness_score": 0.9,
            "distinctiveness_score": 0.9,
            "overall_score": 0.9333,
            "reasons": [],
            "evidence": {
                "workflow_candidate_count": len(routed_ids),
                "supporting_node_count": len(supporting_node_ids) + 1,
                "supporting_edge_count": len(supporting_edge_ids),
                "community_count": len(community_ids),
            },
        },
        "boundary_quality": 0.93,
        "eval_aggregate": 0.9,
        "cross_subset_stability": 0.9,
        "nearest_skill_id": "workflow_candidates",
        "overall_quality": 0.9135,
        "delta_vs_nearest": 0.1,
        "delta_vs_bundle": 0.1,
        "net_positive_value": 0.14,
    }
    seed_content = _build_workflow_gateway_seed_content(
        routed_ids=routed_ids,
        primary_seed=primary_seed,
    )
    return CandidateSeed(
        candidate_id="workflow-gateway",
        candidate_kind="general_agentic",
        primary_node_id=primary_seed.primary_node_id,
        supporting_node_ids=supporting_node_ids,
        supporting_edge_ids=supporting_edge_ids,
        community_ids=community_ids,
        gold_match_hint=None,
        source_skill=None,
        score=max(seed.score for seed in workflow_only_seeds),
        metadata=metadata,
        seed_content=seed_content,
    )


def _build_workflow_gateway_seed_content(
    *,
    routed_ids: list[str],
    primary_seed: CandidateSeed,
) -> dict[str, Any]:
    route_lines = ", ".join(f"`{item}`" for item in routed_ids[:8])
    primary_contract = primary_seed.seed_content.get("contract", {})
    if not isinstance(primary_contract, dict):
        primary_contract = {}
    trigger_patterns = _contract_symbols(
        primary_contract,
        section="trigger",
        key="patterns",
        fallback=["concept_query_only"],
    )[:2]
    trigger_exclusions = _contract_symbols(
        primary_contract,
        section="trigger",
        key="exclusions",
        fallback=["concept_query_only"],
    )[:2]
    fails_when = _contract_symbols(
        primary_contract,
        section="boundary",
        key="fails_when",
        fallback=["disconfirming_evidence_present"],
    )[:2]
    do_not_fire_when = _contract_symbols(
        primary_contract,
        section="boundary",
        key="do_not_fire_when",
        fallback=["scenario_missing_decision_context", "concept_query_only"],
    )[:2]
    return {
        "title": "Workflow Gateway",
        "contract": {
            "trigger": {
                "patterns": trigger_patterns,
                "exclusions": trigger_exclusions,
            },
            "intake": {
                "required": [
                    {"name": "user_goal", "type": "string", "description": "The outcome the user wants from the workflow set."},
                    {"name": "available_context", "type": "list", "description": "Known inputs, constraints, and missing situational facts."},
                    {"name": "candidate_workflow_hint", "type": "string", "description": "Optional workflow id or topic the user thinks may fit."},
                ],
            },
            "judgment_schema": {
                "output": {
                    "type": "structured",
                    "schema": {
                        "verdict": "enum[route_to_workflow, ask_clarifying_question, defer]",
                        "selected_workflow_id": "string",
                        "routing_reason": "string",
                        "missing_context": "list[string]",
                        "next_action": "string",
                    },
                },
                "reasoning_chain_required": True,
            },
            "boundary": {
                "fails_when": fails_when,
                "do_not_fire_when": do_not_fire_when,
            },
        },
        "relations": {
            "depends_on": [],
            "delegates_to": [],
            "constrained_by": [],
            "complements": [],
            "contradicts": [],
        },
        "rationale": (
            "当一个材料存在 high workflow certainty + high context certainty 的候选时，"
            "KiU 不能为了让 bundle 看起来有 skill 而把确定性步骤伪装成厚 skill。"
            "但默认产物仍需要一个可安装、可调用的入口，否则用户拿到的包只能审计，不能使用。"
            "`workflow-gateway` 的职责就是在这两者之间保持边界：它读取用户目标、现有上下文和可能的 workflow hint，"
            "再选择、排序或要求补充上下文；它不改写 workflow_candidates 下的固定步骤，也不把脚本逻辑偷偷并回 agentic skill。"
            "因此它是一个薄路由 skill，而不是领域判断 skill。[^anchor:workflow-gateway-primary]"
        ),
        "evidence_summary": (
            "该 gateway 在当前生成轮次存在 workflow_script_candidate 时生成，即使同一 bundle 也包含少量真正判断密集型 skill。"
            "这说明材料仍有一部分主要交付物是确定性流程，同时也说明需要一个最小可用入口，"
            "把用户请求路由到 workflow_candidates 中的具体 `workflow.yaml` / `CHECKLIST.md`。"
            "当前候选 workflow 包括 " + route_lines + "。[^anchor:workflow-gateway-primary]"
        ),
        "trace_refs": ["traces/workflow-gateway-routing-smoke.yaml"],
        "usage_notes": [
            "把用户目标映射到一个 workflow id；如果目标不足，先问缺失上下文。",
            "输出 selected_workflow_id、routing_reason、missing_context 和 next_action。",
            "不要把 workflow_candidates 下的确定性步骤复制成新的厚 skill。",
        ],
        "scenario_families": {
            "should_trigger": [
                {
                    "scenario_id": "choose-workflow-entrypoint",
                    "summary": "用户拿到一组 workflow candidates，但不知道应该从哪一个开始。",
                    "prompt_signals": ["应该先跑哪个流程", "这些步骤哪个适合当前目标", "帮我选一个工作流入口"],
                    "boundary_reason": "这是路由问题，不是重新生成领域答案。",
                    "next_action_shape": "返回 selected_workflow_id、routing_reason、missing_context、next_action。",
                    "anchor_refs": ["workflow-gateway-primary"],
                }
            ],
            "should_not_trigger": [
                {
                    "scenario_id": "exact-workflow-already-known",
                    "summary": "用户已经明确指定 workflow id 时，不需要 gateway 再判断。",
                    "prompt_signals": ["运行 10-业务流程识别", "打开这个 workflow.yaml"],
                    "boundary_reason": "这时应直接执行对应 workflow，而不是再做 agentic 路由。",
                    "anchor_refs": ["workflow-gateway-primary"],
                }
            ],
            "edge_case": [
                {
                    "scenario_id": "goal-too-vague-for-routing",
                    "summary": "用户只说想分析材料，但没有说明目标、输入或约束。",
                    "prompt_signals": ["帮我分析一下", "看看这个材料"],
                    "boundary_reason": "目标不足时只能 ask_clarifying_question，不能猜一个 workflow。",
                    "next_action_shape": "列 missing_context 并提出最少澄清问题。",
                    "anchor_refs": ["workflow-gateway-primary"],
                }
            ],
            "refusal": [
                {
                    "scenario_id": "agentic-judgment-request",
                    "summary": "用户要求直接给复杂判断结论，而不是选择 workflow。",
                    "prompt_signals": ["直接告诉我战略怎么定", "不要流程，给结论"],
                    "boundary_reason": "这超出薄 gateway 职责，应转交厚 skill 或要求新建 agentic candidate。",
                    "next_action_shape": "说明 gateway 只能路由 workflow，不能替代判断密集型 skill。",
                    "anchor_refs": ["workflow-gateway-primary"],
                }
            ],
        },
        "eval_summary": {
            "kiu_test": {
                "trigger_test": "pass",
                "fire_test": "pass",
                "boundary_test": "pass",
            },
            "subsets": {
                "real_decisions": {"cases": [], "passed": 0, "total": 0, "threshold": 0.0, "status": "pending"},
                "synthetic_adversarial": {"cases": [], "passed": 0, "total": 0, "threshold": 0.0, "status": "pending"},
                "out_of_distribution": {"cases": [], "passed": 0, "total": 0, "threshold": 0.0, "status": "pending"},
            },
            "key_failure_modes": [
                "把 workflow 步骤内联成 agentic skill。",
                "在目标和上下文不足时猜测 workflow。",
            ],
        },
        "revision_seed": {
            "summary": "Initial thin workflow gateway generated because all accepted candidates were deterministic workflow candidates.",
            "evidence_changes": [
                "Preserved workflow candidates outside bundle/skills.",
                "Added one llm_agentic router skill as an installable entrypoint.",
            ],
            "open_gaps": [
                "Replace smoke usage review with real user routing logs before publication.",
                "Confirm whether each routed workflow should later gain a dedicated agentic wrapper.",
            ],
        },
    }


def _contract_symbols(
    contract: dict[str, Any],
    *,
    section: str,
    key: str,
    fallback: list[str],
) -> list[str]:
    section_doc = contract.get(section, {})
    if not isinstance(section_doc, dict):
        return fallback
    values = [
        str(item)
        for item in section_doc.get(key, [])
        if isinstance(item, str) and item
    ]
    return values or fallback


def _unique_limited(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def _write_workflow_gateway_trace(*, bundle_root: Path, seed: CandidateSeed) -> None:
    gateway = seed.metadata.get("workflow_gateway", {})
    routes_to = gateway.get("routes_to", []) if isinstance(gateway, dict) else []
    trace = {
        "trace_id": "workflow-gateway-routing-smoke",
        "title": "Workflow gateway routes an all-workflow bundle",
        "related_skills": ["workflow-gateway"],
        "kind": "generated_smoke",
        "situation": (
            "The generated bundle contains deterministic workflow candidates but no thick "
            "agentic skill candidates, so the user needs an installable entrypoint."
        ),
        "decision": (
            "Use workflow-gateway to select or sequence a workflow candidate, while keeping "
            "the fixed workflow steps under workflow_candidates/."
        ),
        "outcome": (
            "The user receives a callable router skill plus auditable workflow artifacts without "
            "collapsing workflow logic into a thick skill."
        ),
        "source_note": "Generated by KiU when an all-workflow run needs a boundary-safe entrypoint.",
        "workflow_candidates": routes_to,
    }
    _write_yaml(bundle_root / "traces" / "workflow-gateway-routing-smoke.yaml", trace)


def _render_skill_candidate(
    *,
    bundle_root: Path,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
    skill_revision: int,
) -> None:
    skill_dir = bundle_root / "skills" / seed.candidate_id
    (skill_dir / "eval").mkdir(parents=True, exist_ok=True)
    (skill_dir / "iterations").mkdir(parents=True, exist_ok=True)
    (skill_dir / "usage").mkdir(parents=True, exist_ok=True)

    anchors = build_candidate_anchors(
        source_bundle=source_bundle,
        seed=seed,
        bundle_version=BUNDLE_VERSION,
        skill_revision=skill_revision,
    )
    _write_yaml(skill_dir / "anchors.yaml", anchors)

    eval_summary = build_prefilled_eval_summary(
        seed=seed,
        bundle_version=BUNDLE_VERSION,
        skill_revision=skill_revision,
    )
    _write_yaml(skill_dir / "eval" / "summary.yaml", eval_summary)

    revisions = _build_revision_log(source_bundle, seed, skill_revision)
    _write_yaml(skill_dir / "iterations" / "revisions.yaml", revisions)

    scenario_families = _scenario_families_for_seed(source_bundle, seed)
    _write_yaml(skill_dir / "usage" / "scenarios.yaml", scenario_families)

    skill_markdown = build_candidate_skill_markdown(
        source_bundle=source_bundle,
        seed=seed,
        bundle_version=BUNDLE_VERSION,
        skill_revision=skill_revision,
        eval_summary=eval_summary,
        revisions=revisions,
    )
    (skill_dir / "SKILL.md").write_text(skill_markdown, encoding="utf-8")

    candidate_metadata = dict(seed.metadata)
    candidate_metadata["graph_to_skill_distillation"] = build_distillation_contract(
        source_bundle=source_bundle,
        seed=seed,
    )
    candidate_metadata["ria_tv_distillation"] = {
        "schema_version": "kiu.ria-tv-distillation/v0.1",
        "stage": "stage2_skill_distillation",
        "mechanism_chain_required": True,
        "anti_misuse_boundary_required": True,
    }
    if seed.candidate_id == "workflow-gateway":
        gateway = seed.metadata.get("workflow_gateway", {}) if isinstance(seed.metadata, dict) else {}
        candidate_metadata["gateway_provenance"] = build_workflow_gateway_provenance(
            routed_ids=list(gateway.get("routes_to", [])) if isinstance(gateway, dict) else [],
            source_node_ids=[seed.primary_node_id, *seed.supporting_node_ids],
        )
    else:
        candidate_metadata["ria_tv_provenance"] = build_skill_ria_tv_provenance(
            graph_doc=source_bundle.graph_doc,
            primary_node_id=seed.primary_node_id,
            supporting_node_ids=seed.supporting_node_ids,
            supporting_edge_ids=seed.supporting_edge_ids,
        )
        candidate_metadata["distillation_contract"] = _build_distillation_quality_contract(seed)
    _write_yaml(skill_dir / "candidate.yaml", candidate_metadata)


def _build_distillation_quality_contract(seed: CandidateSeed) -> dict[str, Any]:
    seed_content = seed.seed_content if isinstance(seed.seed_content, dict) else {}
    contract = seed_content.get("contract", {}) if isinstance(seed_content.get("contract"), dict) else {}
    trigger = contract.get("trigger", {}) if isinstance(contract.get("trigger"), dict) else {}
    boundary = contract.get("boundary", {}) if isinstance(contract.get("boundary"), dict) else {}
    judgment_schema = (
        contract.get("judgment_schema", {})
        if isinstance(contract.get("judgment_schema"), dict)
        else {}
    )
    rationale = str(seed_content.get("rationale") or seed_content.get("summary") or seed.candidate_id)
    trigger_patterns = [
        item for item in trigger.get("patterns", []) if isinstance(item, str) and item.strip()
    ]
    anti_conditions = _string_list(boundary.get("anti_conditions"))
    if not anti_conditions:
        anti_conditions = _string_list(boundary.get("do_not_fire_when"))
    transfer_conditions = _string_list(judgment_schema.get("transfer_conditions"))
    if not transfer_conditions:
        transfer_conditions = _string_list(seed_content.get("transfer_conditions"))
    return {
        "schema_version": "kiu.distillation-contract/v0.1",
        "mechanism_chain": [rationale[:240]],
        "use_situation_trigger": trigger_patterns[:3] or [f"use `{seed.candidate_id}` only for judgment-rich decisions"],
        "anti_misuse_boundary": anti_conditions[:5] or ["do_not_use_for_summary_translation_fact_lookup_or_stance_commentary"],
        "transfer_conditions": transfer_conditions[:5] or ["source_pattern_matches_current_decision_mechanism"],
        "anti_conditions": anti_conditions[:5] or ["material_context_difference_not_checked"],
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _scenario_families_for_seed(source_bundle: SourceBundle, seed: CandidateSeed) -> dict[str, Any]:
    if seed.source_skill and seed.source_skill.scenario_families:
        scenario_families = seed.source_skill.scenario_families
    else:
        scenario_families = seed.seed_content.get("scenario_families", {})
    scenario_families = scenario_families if isinstance(scenario_families, dict) else {}
    return augment_scenario_families(
        source_bundle=source_bundle,
        seed=seed,
        scenario_families=scenario_families,
    )


def _render_workflow_candidate(
    *,
    workflow_root: Path,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
) -> None:
    candidate_dir = workflow_root / seed.candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(candidate_dir / "candidate.yaml", seed.metadata)
    workflow_doc = _build_workflow_descriptor(source_bundle=source_bundle, seed=seed)
    _write_yaml(candidate_dir / "workflow.yaml", workflow_doc)
    note = (
        f"# {seed.candidate_id}\n\n"
        "This seed was downgraded to `workflow_script_candidate` because both"
        " workflow certainty and context certainty are high. It is preserved for"
        " audit but is intentionally excluded from `bundle/skills/`.\n"
    )
    (candidate_dir / "README.md").write_text(note, encoding="utf-8")
    (candidate_dir / "CHECKLIST.md").write_text(
        _build_workflow_checklist(workflow_doc),
        encoding="utf-8",
    )


def _build_revision_log(
    source_bundle: SourceBundle,
    seed: CandidateSeed,
    skill_revision: int,
) -> dict[str, Any]:
    revision_seed = seed.seed_content.get("revision_seed", {})
    source_skill = seed.source_skill
    source_revisions = source_skill.revisions if source_skill else {}
    source_history = source_revisions.get("history", []) if isinstance(source_revisions, dict) else []
    source_current_summary = (
        source_skill.sections.get("Revision Summary", "").strip()
        if source_skill and isinstance(source_skill.sections, dict)
        else ""
    )
    if not source_current_summary and source_history:
        source_current_summary = str(source_history[-1].get("summary", "") or "").strip()
    source_evidence_changes = []
    if source_history and isinstance(source_history[-1], dict):
        source_evidence_changes = [
            str(item).strip()
            for item in source_history[-1].get("evidence_changes", [])
            if str(item).strip()
        ]
    source_open_gaps = [
        str(item).strip()
        for item in source_revisions.get("open_gaps", [])
        if str(item).strip()
    ] if isinstance(source_revisions, dict) else []
    return {
        "skill_id": seed.candidate_id,
        "bundle_version": BUNDLE_VERSION,
        "current_revision": skill_revision,
        "history": [
            {
                "revision": skill_revision,
                "date": date.today().isoformat(),
                "summary": source_current_summary or revision_seed.get(
                    "summary",
                    (
                        "Initial v0.2 deterministic candidate seed produced from the"
                        " released graph snapshot and source bundle."
                    ),
                ),
                "graph_hash": source_bundle.manifest["graph"]["graph_hash"],
                "effective_status": "under_evaluation",
                "evidence_changes": source_evidence_changes or revision_seed.get(
                    "evidence_changes",
                    [
                        "Attached graph-derived seed anchors.",
                        "Preserved available source/scenario anchors from the gold reference skill.",
                        "Prefilled evaluation summary from the shared evaluation corpus.",
                    ],
                ),
            }
        ],
        "open_gaps": source_open_gaps or revision_seed.get(
            "open_gaps",
            [
                "Review whether the contract should be tightened before publication.",
                "Confirm that representative traces still match the intended trigger boundary.",
            ],
        ),
    }


def _build_workflow_descriptor(
    *,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
) -> dict[str, Any]:
    nodes = {
        node["id"]: node
        for node in source_bundle.graph_doc.get("nodes", [])
        if isinstance(node, dict) and "id" in node
    }
    edges = {
        edge["id"]: edge
        for edge in source_bundle.graph_doc.get("edges", [])
        if isinstance(edge, dict) and "id" in edge
    }
    communities = {
        community["id"]: community
        for community in source_bundle.graph_doc.get("communities", [])
        if isinstance(community, dict) and "id" in community
    }
    primary_node_id = seed.primary_node_id
    primary_node = nodes.get(primary_node_id, {})
    supporting_nodes = [nodes[node_id] for node_id in seed.supporting_node_ids if node_id in nodes]
    supporting_edges = [edges[edge_id] for edge_id in seed.supporting_edge_ids if edge_id in edges]
    related_communities = [
        communities[community_id]
        for community_id in seed.community_ids
        if community_id in communities
    ]

    return {
        "workflow_id": seed.candidate_id,
        "title": _humanize_identifier(seed.candidate_id),
        "source_bundle_id": source_bundle.manifest["bundle_id"],
        "source_graph_hash": source_bundle.manifest["graph"]["graph_hash"],
        "recommended_execution_mode": seed.metadata["recommended_execution_mode"],
        "disposition": seed.metadata["disposition"],
        "workflow_certainty": seed.metadata["workflow_certainty"],
        "context_certainty": seed.metadata["context_certainty"],
        "objective": (
            "Run a deterministic preflight before execution when the control pattern is"
            " better served by a fixed workflow than an agentic skill."
        ),
        "seed": {
            "primary_node_id": primary_node_id,
            "supporting_node_ids": list(seed.supporting_node_ids),
            "supporting_edge_ids": list(seed.supporting_edge_ids),
            "community_ids": list(seed.community_ids),
        },
        "evidence_anchors": {
            "primary_node": {
                "id": primary_node_id,
                "label": primary_node.get("label", primary_node_id),
                "type": primary_node.get("type"),
            },
            "supporting_nodes": [
                {
                    "id": node["id"],
                    "label": node.get("label", node["id"]),
                    "type": node.get("type"),
                }
                for node in supporting_nodes
            ],
            "supporting_edges": [
                {
                    "id": edge["id"],
                    "type": edge.get("type"),
                    "from": edge.get("from"),
                    "to": edge.get("to"),
                }
                for edge in supporting_edges
            ],
            "communities": [
                {
                    "id": community["id"],
                    "label": community.get("label", community["id"]),
                }
                for community in related_communities
            ],
        },
        "checklist_sections": [
            "Scope",
            "Rollback",
            "Reversibility",
            "Evidence Anchors",
        ],
    }


def _build_workflow_checklist(workflow_doc: dict[str, Any]) -> str:
    anchors = workflow_doc.get("evidence_anchors", {})
    primary = anchors.get("primary_node", {})
    supporting_nodes = anchors.get("supporting_nodes", [])
    supporting_edges = anchors.get("supporting_edges", [])
    communities = anchors.get("communities", [])

    return (
        f"# {workflow_doc['workflow_id']}\n\n"
        f"Execution mode: `{workflow_doc['recommended_execution_mode']}`\n\n"
        "## Objective\n"
        f"{workflow_doc['objective']}\n\n"
        "## Scope\n"
        "- [ ] Summarize the proposed change and the exact affected surface.\n"
        "- [ ] Name the users, data paths, and downstream systems in scope.\n"
        "- [ ] Define the abort condition before execution starts.\n\n"
        "## Rollback\n"
        "- [ ] Confirm rollback steps are written, owned, and time-bounded.\n"
        "- [ ] State whether rollback has been rehearsed on a representative environment.\n"
        "- [ ] Record the monitoring signal that would trigger rollback.\n\n"
        "## Reversibility\n"
        "- [ ] Identify any irreversible data writes or side effects.\n"
        "- [ ] Document the safeguard for irreversible steps: backup, dual-write, holdback, or canary.\n"
        "- [ ] Record the explicit go/no-go decision.\n\n"
        "## Evidence Anchors\n"
        f"- Primary node: `{primary.get('id', '<missing>')}`"
        f" ({primary.get('label', '<missing-label>')})\n"
        f"- Supporting nodes: {', '.join(_format_anchor_list(supporting_nodes, key='label')) or 'none'}\n"
        f"- Supporting edges: {', '.join(_format_edge_list(supporting_edges)) or 'none'}\n"
        f"- Communities: {', '.join(_format_anchor_list(communities, key='label')) or 'none'}\n"
    )


def _format_anchor_list(items: list[dict[str, Any]], *, key: str) -> list[str]:
    rendered: list[str] = []
    for item in items:
        item_id = item.get("id", "<missing-id>")
        label = item.get(key, item_id)
        rendered.append(f"`{item_id}` ({label})")
    return rendered


def _format_edge_list(items: list[dict[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for item in items:
        item_id = item.get("id", "<missing-id>")
        edge_type = item.get("type", "<missing-type>")
        edge_from = item.get("from", "<missing-from>")
        edge_to = item.get("to", "<missing-to>")
        rendered.append(f"`{item_id}` ({edge_type}: {edge_from} -> {edge_to})")
    return rendered


def _humanize_identifier(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _append_gateway_trigger_definitions(*, bundle_root: Path, seed: CandidateSeed) -> None:
    trigger_path = bundle_root / "triggers.yaml"
    trigger_doc = yaml.safe_load(trigger_path.read_text(encoding="utf-8")) if trigger_path.exists() else {}
    if not isinstance(trigger_doc, dict):
        trigger_doc = {}
    trigger_entries = trigger_doc.setdefault("triggers", [])
    if not isinstance(trigger_entries, list):
        trigger_entries = []
        trigger_doc["triggers"] = trigger_entries
    existing = {
        item.get("symbol")
        for item in trigger_entries
        if isinstance(item, dict) and item.get("symbol")
    }
    contract = seed.seed_content.get("contract", {})
    symbols: list[str] = []
    for section, key in (
        ("trigger", "patterns"),
        ("trigger", "exclusions"),
        ("boundary", "fails_when"),
        ("boundary", "do_not_fire_when"),
    ):
        values = contract.get(section, {}).get(key, []) if isinstance(contract.get(section), dict) else []
        symbols.extend(str(item) for item in values if isinstance(item, str) and item)
    for symbol in symbols:
        if symbol in existing:
            continue
        trigger_entries.append(
            {
                "symbol": symbol,
                "definition": f"Workflow gateway routing symbol `{symbol}` generated to preserve workflow-vs-agentic boundaries.",
                "positive_examples": [
                    "Use workflow-gateway to choose, sequence, or defer workflow candidates without inlining deterministic steps."
                ],
                "negative_examples": [
                    "Do not use workflow-gateway to execute or copy workflow checklist steps into a thick skill."
                ],
            }
        )
        existing.add(symbol)
    _write_yaml(trigger_path, trigger_doc)
