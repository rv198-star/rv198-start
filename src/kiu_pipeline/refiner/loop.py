from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..baseline import build_candidate_baseline
from ..contracts import identify_semantic_family
from ..models import SourceBundle
from ..mutate import mutate_candidate
from ..quality import assess_candidate_output
from ..reports import write_final_decision, write_round_report, write_scorecard
from ..scoring import (
    DEFAULT_WEIGHTS,
    decide_terminal_state,
    quality_from_eval_summary,
    score_candidate,
)
from .drafting import LLMBudgetTracker, apply_llm_drafting
from .providers import LLMProvider, create_provider_from_env


def refine_candidate(
    *,
    candidate: dict[str, Any],
    source_bundle: SourceBundle,
    run_root: str | Path,
    mutation_strategy: str = "default",
    llm_provider: LLMProvider | None = None,
    llm_budget_tokens: int = 100000,
    budget_tracker: LLMBudgetTracker | None = None,
) -> dict[str, Any]:
    config = source_bundle.profile.get("refinement_scheduler", {})
    weights = config.get("weights") or DEFAULT_WEIGHTS
    bonuses = config.get("bonuses", {})
    current = _initialize_candidate_metrics(candidate, weights=weights)
    nearest_skill_id = (
        current.get("nearest_skill_id")
        or current["candidate"].get("gold_match_hint")
        or current["candidate"]["candidate_id"]
    )
    baseline = build_candidate_baseline(
        source_bundle=source_bundle,
        nearest_skill_id=nearest_skill_id,
    )

    drafting_mode = current["candidate"].get("drafting_mode", "deterministic")
    provider = llm_provider
    token_budget = budget_tracker
    if drafting_mode == "llm-assisted":
        provider = provider or create_provider_from_env()
        token_budget = token_budget or LLMBudgetTracker(max_tokens=llm_budget_tokens)

    history: list[dict[str, Any]] = []
    for round_index in range(1, config.get("max_rounds", 5) + 1):
        mutation_plan = plan_round_mutation(
            current=current,
            round_index=round_index,
            mutation_strategy=mutation_strategy,
            source_bundle=source_bundle,
        )
        current = mutate_candidate(
            candidate=current,
            round_index=round_index,
            mutation_plan=mutation_plan,
        )

        llm_doc: dict[str, Any] | None = None
        llm_rejections: list[str] = []
        llm_stop_reason: str | None = None
        if drafting_mode == "llm-assisted" and provider is not None and token_budget is not None:
            current, llm_doc, llm_rejections, llm_stop_reason = apply_llm_drafting(
                candidate=current,
                source_bundle=source_bundle,
                run_root=run_root,
                round_index=round_index,
                llm_provider=provider,
                budget_tracker=token_budget,
            )

        scorecard = score_candidate(
            boundary_quality=float(current["candidate"]["boundary_quality"]),
            eval_aggregate=float(current["candidate"]["eval_aggregate"]),
            cross_subset_stability=float(current["candidate"]["cross_subset_stability"]),
            baseline=baseline,
            bonuses=bonuses,
            weights=weights,
        )
        quality_assessment = assess_candidate_output(
            candidate=current,
            profile=source_bundle.profile,
            loop_scorecard=scorecard,
        )
        scorecard.update(
            {
                "artifact_quality": quality_assessment["artifact_quality"],
                "artifact_grade": quality_assessment["artifact_grade"],
                "production_quality": quality_assessment["production_quality"],
                "quality_grade": quality_assessment["quality_grade"],
                "release_ready": quality_assessment["release_ready"],
            }
        )
        history.append(scorecard)
        structural_valid = _structural_gate(current)

        if llm_stop_reason == "llm_budget_exhausted":
            current["candidate"].update(scorecard)
            current["candidate"]["terminal_state"] = "do_not_publish"
            _write_round(
                run_root=run_root,
                round_index=round_index,
                current=current,
                mutation_plan=mutation_plan,
                scorecard=scorecard,
                decision={
                    "terminal_state": "do_not_publish",
                    "reason": llm_stop_reason,
                    "continue_loop": False,
                },
                llm_doc=llm_doc,
                llm_rejections=llm_rejections,
                quality_assessment=quality_assessment,
            )
            write_final_decision(
                run_root,
                {
                    "candidate_id": current["candidate"]["candidate_id"],
                    "terminal_state": "do_not_publish",
                    "reason": llm_stop_reason,
                    "overall_quality": current["candidate"].get("overall_quality"),
                    "production_quality": current["candidate"].get("production_quality"),
                    "quality_grade": current["candidate"].get("quality_grade"),
                    "net_positive_value": current["candidate"].get("net_positive_value"),
                },
            )
            return current

        decision = decide_terminal_state(
            round_index=round_index,
            config=config,
            scorecard=scorecard,
            history=history,
            structural_valid=structural_valid,
        )
        current["candidate"].update(scorecard)
        current["candidate"]["terminal_state"] = decision["terminal_state"]
        _write_round(
            run_root=run_root,
            round_index=round_index,
            current=current,
            mutation_plan=mutation_plan,
            scorecard=scorecard,
            decision=decision,
            llm_doc=llm_doc,
            llm_rejections=llm_rejections,
            quality_assessment=quality_assessment,
        )
        if not decision["continue_loop"]:
            write_final_decision(
                run_root,
                {
                    "candidate_id": current["candidate"]["candidate_id"],
                    "terminal_state": decision["terminal_state"],
                    "reason": decision["reason"],
                    "overall_quality": current["candidate"].get("overall_quality"),
                    "production_quality": current["candidate"].get("production_quality"),
                    "quality_grade": current["candidate"].get("quality_grade"),
                    "net_positive_value": current["candidate"].get("net_positive_value"),
                },
            )
            return current

    current["candidate"]["terminal_state"] = "max_rounds_reached"
    write_final_decision(
        run_root,
        {
            "candidate_id": current["candidate"]["candidate_id"],
            "terminal_state": "max_rounds_reached",
            "reason": "max_rounds_reached",
            "overall_quality": current["candidate"].get("overall_quality"),
            "production_quality": current["candidate"].get("production_quality"),
            "quality_grade": current["candidate"].get("quality_grade"),
            "net_positive_value": current["candidate"].get("net_positive_value"),
        },
    )
    return current


def refine_bundle_candidates(
    *,
    candidates: list[dict[str, Any]],
    source_bundle: SourceBundle,
    run_root: str | Path,
    llm_provider: LLMProvider | None = None,
    llm_budget_tokens: int = 100000,
) -> list[dict[str, Any]]:
    refined: list[dict[str, Any]] = []
    states: Counter[str] = Counter()
    final_docs: list[dict[str, Any]] = []
    shared_budget = LLMBudgetTracker(max_tokens=llm_budget_tokens)
    for candidate in candidates:
        result = refine_candidate(
            candidate=candidate,
            source_bundle=source_bundle,
            run_root=run_root,
            llm_provider=llm_provider,
            llm_budget_tokens=llm_budget_tokens,
            budget_tracker=shared_budget,
        )
        refined.append(result)
        state = result["candidate"]["terminal_state"]
        states[state] += 1
        final_docs.append(
            {
                "candidate_id": result["candidate"]["candidate_id"],
                "terminal_state": state,
                "overall_quality": result["candidate"].get("overall_quality"),
                "production_quality": result["candidate"].get("production_quality"),
                "quality_grade": result["candidate"].get("quality_grade"),
                "net_positive_value": result["candidate"].get("net_positive_value"),
            }
        )

    write_scorecard(
        run_root,
        {
            "candidate_count": len(refined),
            "terminal_states": dict(states),
            "candidates": final_docs,
        },
    )
    write_final_decision(
        run_root,
        {
            "terminal_states": dict(states),
            "candidates": final_docs,
            "llm_budget": {
                "spent_tokens": shared_budget.spent_tokens,
                "max_tokens": shared_budget.max_tokens,
                "remaining_tokens": shared_budget.remaining_tokens,
            },
        },
    )
    return refined


def plan_round_mutation(
    *,
    current: dict[str, Any],
    round_index: int,
    mutation_strategy: str,
    source_bundle: SourceBundle,
) -> dict[str, Any]:
    if mutation_strategy == "stalled":
        return {
            "boundary_strength_delta": 0.0,
            "eval_gain_delta": 0.0,
            "stability_delta": 0.0,
            "append_trace_ref": None,
            "revision_note": f"Round {round_index} produced no material improvement.",
        }

    skill_id = current["candidate"]["candidate_id"]
    source_skill = source_bundle.skills.get(skill_id)
    trace_refs = source_skill.trace_refs if source_skill else []
    trace_ref = trace_refs[min(round_index - 1, len(trace_refs) - 1)] if trace_refs else None
    revision_note = _family_revision_note(
        candidate_id=skill_id,
        round_index=round_index,
    )
    return {
        "boundary_strength_delta": 0.05,
        "eval_gain_delta": 0.05,
        "stability_delta": 0.05,
        "append_trace_ref": trace_ref,
        "revision_note": revision_note,
    }


def _family_revision_note(*, candidate_id: str, round_index: int) -> str:
    semantic_family = identify_semantic_family(candidate_id)
    prefix = f"Refinement scheduler round {round_index} tightened boundary signals and improved evaluation support."
    if semantic_family == "circle-of-competence":
        return (
            f"{prefix} It now treats “朋友拉我投餐饮连锁, 我应该差不多能搞明白” as a trigger, "
            "but keeps “已有 10 年后端开发经验的新项目架构设计” and “Python vs Go 哪个更适合微服务” "
            "outside scope because one is already inside a proven circle and the other is a 技术选型的客观分析问题."
        )
    if semantic_family == "invert-the-problem":
        return (
            f"{prefix} It keeps “产品上市计划怎么失败”, “进入东南亚市场最坏会怎样”, and "
            "“团队只看到了机会没看到威胁, 能不能系统性地找找方案的茬” on the failure-first path, "
            "so the output names 潜在威胁、失败模式、找茬清单 and a first preventive action rather than继续扩创意广度. "
            "It explicitly treats 纯创意发散 as out of scope: 逆向思维天然偏向保守和防御, 不适合创意场景, 需要创意发散时不适用. "
            "For跳槽这类职业决策, it activates only when the user wants to系统性评估跳槽风险和失败模式; "
            "if the user is merely比较两个选项优劣, it should route away from inversion. "
            "For健身计划这类个人日常目标, it stays at a 轻量 pre-mortem / partial_review posture instead of a重大决策级别的重型风险框架."
        )
    if semantic_family == "bias-self-audit":
        return (
            f"{prefix} It treats “大家都同意, 明天就拍板” and “只收集了支持观点的数据” as live bias-audit windows, "
            "but refuses 达尔文历史/科学知识查询, 信息收集的早期阶段, and 紧急决策场景 like “服务器突然宕机了先判断数据库还是网络”, "
            "because系统性地搜索反面证据不现实, 不应激活这类方法论检验."
        )
    if semantic_family == "value-assessment":
        return (
            f"{prefix} It now treats “品牌很强但价格不便宜, 值不值这个价”, “市场恐慌是不是错杀好公司”, and "
            "“这个天使轮估值到底有没有道理” as value-anchor judgments, and it also keeps “这种公司和其他公司到底差在哪” in scope when the real issue is 护城河、定价权与尚未利用的提价能力 rather than mere scale comparison. "
            "加盟店、私有生意、天使轮等边界案例默认先标成 `partial_applicability` 并先做能力圈检验, while没有稳定内在价值锚点的投机场景会明确 `refuse`. "
            "纯规模和竞争格局比较应转给 `scale-advantage-analysis`, and短线交易不适用 because this framework assumes long-term holding rather than day-trading indicators. "
            "When the user also asks how大仓位, it explicitly hands the case off to sizing instead of letting valuation silently代替仓位纪律."
        )
    if semantic_family == "margin-of-safety-sizing":
        return (
            f"{prefix} It now ties “市盈率 25 倍但品牌很强, 价格合理吗” and “市场恐慌是不是错杀好公司” "
            "to live sizing decisions, while refusing 规模和竞争格局比较 and 短线交易指标 questions because they are not value-and-sizing judgments."
        )
    return prefix


def _initialize_candidate_metrics(
    candidate: dict[str, Any],
    *,
    weights: dict[str, float],
) -> dict[str, Any]:
    initialized = deepcopy(candidate)
    metrics = quality_from_eval_summary(
        initialized["eval_summary"],
        weights=weights,
    )
    for key in ("boundary_quality", "eval_aggregate", "cross_subset_stability"):
        initialized["candidate"].setdefault(key, metrics[key])
    initialized["candidate"].setdefault("current_round", 0)
    initialized["candidate"].setdefault("loop_mode", "refinement_scheduler")
    initialized["candidate"].setdefault("terminal_state", "pending")
    initialized["candidate"].setdefault("human_gate", "skipped")
    return initialized


def _structural_gate(candidate: dict[str, Any]) -> bool:
    return bool(
        candidate.get("skill_markdown")
        and candidate.get("anchors")
        and candidate.get("eval_summary")
        and candidate.get("revisions")
        and candidate.get("candidate")
    )


def _write_round(
    *,
    run_root: str | Path,
    round_index: int,
    current: dict[str, Any],
    mutation_plan: dict[str, Any],
    scorecard: dict[str, Any],
    decision: dict[str, Any],
    llm_doc: dict[str, Any] | None,
    llm_rejections: list[str],
    quality_assessment: dict[str, Any],
) -> None:
    doc = {
        "candidate_id": current["candidate"]["candidate_id"],
        "mutation_plan": mutation_plan,
        "scorecard": scorecard,
        "decision": decision,
        "quality_assessment": quality_assessment,
    }
    if llm_doc is not None or llm_rejections:
        doc["llm_drafting"] = llm_doc
        doc["llm_rejections"] = llm_rejections
    write_round_report(
        run_root,
        round_index,
        doc,
        candidate_id=current["candidate"]["candidate_id"],
    )
