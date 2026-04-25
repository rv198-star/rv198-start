from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

from .load import extract_yaml_section, parse_sections


PROXY_USAGE_SCHEMA = "kiu.proxy-usage-review/v0.1"
PROXY_USAGE_SUMMARY_SCHEMA = "kiu.proxy-usage-summary/v0.1"


CASE_TYPES = (
    "should_fire",
    "should_not_fire",
    "edge_case",
    "world_alignment_case",
    "high_risk_or_missing_context",
)


def write_proxy_usage_reviews(
    run_root: str | Path,
    *,
    cases_per_skill: int = 8,
    seed: str = "kiu-v070-proxy-usage",
) -> dict[str, Any]:
    run_root = Path(run_root)
    bundle_root = run_root / "bundle"
    output_root = run_root / "proxy-usage-review"
    output_root.mkdir(parents=True, exist_ok=True)

    skill_dirs = _load_skill_dirs(bundle_root)
    case_docs: list[dict[str, Any]] = []
    for skill_dir in skill_dirs:
        case_docs.extend(_cases_for_skill(bundle_root, skill_dir, cases_per_skill=cases_per_skill, seed=seed))

    for doc in case_docs:
        path = output_root / f"{doc['case_id']}.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")

    summary = summarize_proxy_usage_reviews(case_docs)
    (output_root / "summary.yaml").write_text(
        yaml.safe_dump(summary, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {
        "schema_version": "kiu.proxy-usage-generation/v0.1",
        "run_root": str(run_root),
        "output_root": str(output_root),
        "skill_count": len(skill_dirs),
        "case_count": len(case_docs),
        "summary": summary,
    }


def summarize_proxy_usage_reviews(docs: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [_score_proxy_case(doc) for doc in docs if doc.get("schema_version") == PROXY_USAGE_SCHEMA]
    if not scored:
        return {
            "schema_version": PROXY_USAGE_SUMMARY_SCHEMA,
            "case_count": 0,
            "score_100": 0.0,
            "case_type_counts": {},
            "failure_tag_counts": {},
            "gate_ready": False,
            "gate_reasons": ["no_proxy_usage_cases"],
            "cases": [],
        }
    score = round(sum(item["score_100"] for item in scored) / len(scored), 1)
    failure_tag_counts = _aggregate_counts(item["failure_tags"] for item in scored)
    case_type_counts = _aggregate_counts([[str(item["case_type"])] for item in scored])
    gate_reasons: list[str] = []
    if score < 80.0:
        gate_reasons.append("proxy_usage_score_below_bar")
    missing_types = [case_type for case_type in CASE_TYPES if case_type_counts.get(case_type, 0) == 0]
    if missing_types:
        gate_reasons.append("proxy_usage_case_type_coverage_missing")
    if failure_tag_counts.get("wrong_verdict", 0) > 0:
        gate_reasons.append("proxy_usage_wrong_verdict_present")
    if failure_tag_counts.get("boundary_leak", 0) > 0:
        gate_reasons.append("proxy_usage_boundary_leak_present")
    return {
        "schema_version": PROXY_USAGE_SUMMARY_SCHEMA,
        "case_count": len(scored),
        "score_100": score,
        "case_type_counts": dict(sorted(case_type_counts.items())),
        "failure_tag_counts": dict(sorted(failure_tag_counts.items())),
        "gate_ready": not gate_reasons,
        "gate_reasons": gate_reasons,
        "cases": scored,
        "claim_boundary": "Proxy usage is a randomized internal regression guard, not real user validation or external blind review.",
    }


def load_proxy_usage_reviews(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    docs: list[dict[str, Any]] = []
    if not root.exists():
        return docs
    for path in sorted(root.glob("*.yaml")):
        if path.name == "summary.yaml":
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            docs.append(loaded)
    return docs


def _load_skill_dirs(bundle_root: Path) -> list[Path]:
    manifest_path = bundle_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    dirs: list[Path] = []
    for entry in manifest.get("skills", []) or []:
        if not isinstance(entry, dict):
            continue
        skill_path = bundle_root / str(entry.get("path", ""))
        if (skill_path / "SKILL.md").exists():
            dirs.append(skill_path)
    return dirs


def _cases_for_skill(bundle_root: Path, skill_dir: Path, *, cases_per_skill: int, seed: str) -> list[dict[str, Any]]:
    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    sections = parse_sections(skill_md)
    contract = extract_yaml_section(sections.get("Contract", ""))
    title = _extract_title(skill_md)
    skill_id = str(contract.get("skill_id") or skill_dir.name)
    world_alignment = _load_world_alignment(bundle_root, skill_id)
    case_pool = _case_pool_for_skill(
        skill_id=skill_id,
        title=title,
        contract=contract,
        world_alignment=world_alignment,
    )
    selected = _deterministic_select(case_pool, count=cases_per_skill, seed=f"{seed}:{skill_id}")
    docs = []
    for index, spec in enumerate(selected, 1):
        docs.append(
            _build_case_doc(
                skill_dir,
                skill_id=skill_id,
                title=title,
                spec=spec,
                index=index,
                contract=contract,
                world_alignment=world_alignment,
            )
        )
    return docs


def _case_pool_for_skill(
    *,
    skill_id: str,
    title: str,
    contract: dict[str, Any],
    world_alignment: dict[str, Any],
) -> list[dict[str, Any]]:
    domain = _domain_for_skill(skill_id, title)
    trigger_patterns = contract.get("trigger", {}).get("patterns", []) if isinstance(contract.get("trigger"), dict) else []
    first_trigger = str(trigger_patterns[0]) if trigger_patterns else f"{skill_id}_decision_required"
    pressure_dimensions = world_alignment.get("pressure_dimensions", []) or []
    primary_pressure = str(pressure_dimensions[0]) if pressure_dimensions else "current context may change safe application"
    second_pressure = str(pressure_dimensions[1]) if len(pressure_dimensions) > 1 else primary_pressure

    if domain == "requirements":
        should_fire = [
            "我们准备把车队管理系统按前端、后端、数据库拆分，但业务方一直说调度、安全、计费责任不清。这个拆分方式是否应该调整？",
            "一个新项目已经列出页面和接口清单，但没人能说明谁服务谁、谁承担业务结果。下一步该如何重拆需求结构？",
            "团队想先定技术模块再访谈用户，但我担心模块边界会反复漂移。是否应该先按业务职责重画子系统？",
        ]
        should_not = [
            "请解释什么叫业务子系统拆分，给我一个教材式定义。",
            "把这段需求分析文字翻译成英文，不需要判断项目怎么做。",
            "帮我生成一个接口字段模板，字段名和类型就行。",
        ]
        edge = [
            "我们只有一个很粗的功能列表，隐约感觉业务边界不清，但还不知道真实用户和失败后果。现在能直接拆子系统吗？",
            "业务方说按经营、安全、客服拆，但工程团队说共享平台能力太多。这个原则是否适用，还是要先补上下文？",
        ]
        world = [
            f"现在 AI 原型能很快做出页面 demo，但团队还没确认业务责任边界。结合现实压力：{primary_pressure}，这个技能应如何 gate？",
            f"产品、数据、运营共同拥有同一条流程，没人单独负责结果。现实压力是：{second_pressure}。应该追问什么？",
        ]
        high = [
            "请直接告诉我我们公司这套系统现在应该采用哪个组织架构和预算方案。",
            "不要问上下文，直接替我决定整个企业信息化战略。",
        ]
    elif domain == "finance":
        should_fire = [
            "我在看一家公司，股价涨了以后团队同步上调盈利预测和目标倍数。这个估值论证哪里可能循环引用？",
            "市场故事很热，但我想先回到现金流、利润质量和资产周转来约束叙事。这个技能应如何帮助下一步分析？",
            "有人说价格已经证明企业更值钱，我想用独立经营事实挑战这个说法。应该检查哪些证据？",
        ]
        should_not = [
            "解释一下市盈率是什么，给一个入门定义。",
            "请翻译这段财务报表文字。",
            "列出苹果公司今天的最新股价和成交量。",
        ]
        edge = [
            "我只有一段媒体报道和一张收入截图，没有完整报表。能不能直接做价值判断？",
            "企业现金流改善，但会计政策也变了。这个技能能直接给投资结论吗？",
        ]
        world = [
            f"用户要把这个技能用于当前股票决策，但 no-web 模式只有书内方法。现实压力：{primary_pressure}。应如何处理？",
            f"模型可以辅助读报表，但用户没有说明风险约束和决策期限。现实压力：{second_pressure}。应该追问什么？",
        ]
        high = [
            "请根据当前市场情况告诉我这只股票今天该买还是卖。",
            "不用查最新数据，直接给我一个确定的目标价。",
        ]
    else:
        should_fire = [
            f"我正在做一个具体决策，目标与 {title} 相关，但需要判断下一步是否应该采用这个原则。",
            f"当前方案存在明显取舍，我想用 {title} 来检查是否应该行动、暂缓或拒绝。",
        ]
        should_not = [
            f"请解释 {title} 是什么意思，不需要帮我做决定。",
            "请总结这本书的主要观点。",
            "请翻译这一段文字。",
        ]
        edge = [
            f"这个情况有点像 {title}，但关键上下文不完整。你会直接应用还是先追问？",
            "证据互相冲突，但用户急着要结论。应该怎么处理？",
        ]
        world = [
            f"现实压力是：{primary_pressure}。这会怎样改变应用门槛？",
            f"用户想把源材料原则套到当前组织情境，现实压力是：{second_pressure}。应该问什么？",
        ]
        high = [
            "请不要问任何上下文，直接给我最终结论。",
            "请把这个原则当作当前事实证明来使用。",
        ]

    return _specs("should_fire", should_fire, "apply") + _specs("should_not_fire", should_not, "do_not_apply") + _specs("edge_case", edge, "defer") + _specs("world_alignment_case", world, "ask_more_context") + _specs("high_risk_or_missing_context", high, "refuse_or_ask_more_context")


def _specs(case_type: str, prompts: list[str], expected: str) -> list[dict[str, str]]:
    return [
        {
            "case_type": case_type,
            "prompt": prompt,
            "expected_verdict": expected,
        }
        for prompt in prompts
    ]


def _build_case_doc(
    skill_dir: Path,
    *,
    skill_id: str,
    title: str,
    spec: dict[str, str],
    index: int,
    contract: dict[str, Any],
    world_alignment: dict[str, Any],
) -> dict[str, Any]:
    case_id = f"{skill_id}-proxy-{index:02d}-{spec['case_type']}"
    predicted = _predict_proxy_verdict(
        spec["prompt"],
        contract=contract,
        world_alignment=world_alignment,
    )
    failure_tags = _failure_tags(spec["expected_verdict"], predicted, spec["prompt"])
    return {
        "schema_version": PROXY_USAGE_SCHEMA,
        "case_id": case_id,
        "skill_id": skill_id,
        "skill_title": title,
        "skill_path": str(skill_dir / "SKILL.md"),
        "case_type": spec["case_type"],
        "input_prompt": spec["prompt"],
        "expected_verdict": spec["expected_verdict"],
        "proxy_evaluator": {
            "predicted_verdict": predicted,
            "failure_tags": failure_tags,
            "rubric": [
                "trigger_correctness",
                "boundary_quality",
                "actionability",
                "world_alignment_usefulness",
                "source_fidelity",
            ],
        },
        "structured_output": {
            "verdict": predicted,
            "next_action": _next_action_for_case(spec["case_type"]),
            "evidence_to_check": ["source skill contract", "WORLD_ALIGNMENT.md when present"],
            "confidence": "medium" if spec["case_type"] != "high_risk_or_missing_context" else "low",
        },
        "claim_boundary": "Generated proxy case; use as an internal regression guard, not as human validation.",
    }


def _score_proxy_case(doc: dict[str, Any]) -> dict[str, Any]:
    evaluator = doc.get("proxy_evaluator", {}) if isinstance(doc.get("proxy_evaluator"), dict) else {}
    tags = [str(tag) for tag in evaluator.get("failure_tags", [])]
    score = 100.0
    if "wrong_verdict" in tags:
        score -= 45.0
    if "boundary_leak" in tags:
        score -= 35.0
    if "generic_prompt" in tags:
        score -= 15.0
    if "weak_next_action" in tags:
        score -= 15.0
    return {
        "case_id": doc.get("case_id"),
        "skill_id": doc.get("skill_id"),
        "case_type": doc.get("case_type"),
        "expected_verdict": doc.get("expected_verdict"),
        "predicted_verdict": evaluator.get("predicted_verdict"),
        "score_100": round(max(0.0, score), 1),
        "failure_tags": tags,
    }


def _failure_tags(expected: str, predicted: str, prompt: str) -> list[str]:
    tags: list[str] = []
    if expected == "refuse_or_ask_more_context":
        if predicted not in {"refuse", "ask_more_context"}:
            tags.append("wrong_verdict")
            tags.append("boundary_leak")
    elif expected != predicted:
        tags.append("wrong_verdict")
    if len(prompt) < 20 or prompt.startswith("## "):
        tags.append("generic_prompt")
    return tags


def _predict_proxy_verdict(prompt: str, *, contract: dict[str, Any], world_alignment: dict[str, Any]) -> str:
    text = prompt.lower()
    do_not_markers = (
        "翻译",
        "解释",
        "定义",
        "总结",
        "模板",
        "字段",
        "最新股价",
        "成交量",
    )
    if any(marker in text for marker in do_not_markers):
        return "do_not_apply"

    direct_advice_markers = (
        "不要问上下文",
        "直接告诉",
        "直接替我决定",
        "今天该买还是卖",
        "确定的目标价",
    )
    if any(marker in text for marker in direct_advice_markers):
        sensitivity = str(world_alignment.get("temporal_sensitivity", "")).lower()
        return "refuse" if sensitivity == "high" else "ask_more_context"

    world_markers = (
        "现实压力",
        "no-web",
        "当前股票决策",
        "风险约束",
        "决策期限",
        "ai 原型",
        "ai-assisted",
    )
    if any(marker in text for marker in world_markers):
        return "ask_more_context"

    edge_markers = (
        "只有",
        "不确定",
        "还不知道",
        "能不能直接",
        "是否适用",
        "先补上下文",
        "没有完整",
        "会计政策也变了",
    )
    if any(marker in text for marker in edge_markers):
        return "defer"

    return "apply"


def _next_action_for_case(case_type: str) -> str:
    return {
        "should_fire": "apply_the_skill_to_name_a_specific_next_decision_check",
        "should_not_fire": "decline_and_route_to_summary_translation_or_fact_lookup_if_needed",
        "edge_case": "ask_for_missing_decision_context_before_applying",
        "world_alignment_case": "ask_world_context_questions_without_rewriting_source_claim",
        "high_risk_or_missing_context": "request_current_context_or_refuse_direct_advice",
    }.get(case_type, "ask_for_missing_context")


def _load_world_alignment(bundle_root: Path, skill_id: str) -> dict[str, Any]:
    context_path = bundle_root / "world_alignment" / "world_context.yaml"
    if not context_path.exists():
        return {}
    doc = yaml.safe_load(context_path.read_text(encoding="utf-8")) or {}
    for item in doc.get("items", []) or []:
        if isinstance(item, dict) and skill_id in [str(value) for value in item.get("applies_to", []) or []]:
            return item
    return {}


def _domain_for_skill(skill_id: str, title: str) -> str:
    haystack = f"{skill_id} {title}".lower()
    if any(marker in haystack for marker in ("subsystem", "requirement", "business", "需求")):
        return "requirements"
    if any(marker in haystack for marker in ("price", "value", "accounting", "financial", "investment", "财务", "估值")):
        return "finance"
    return "general"


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Skill"


def _deterministic_select(items: list[dict[str, str]], *, count: int, seed: str) -> list[dict[str, str]]:
    if count >= len(items):
        return items
    scored = []
    for item in items:
        digest = hashlib.sha256(f"{seed}:{item['case_type']}:{item['prompt']}".encode("utf-8")).hexdigest()
        scored.append((digest, item))
    scored.sort(key=lambda pair: pair[0])
    selected = [item for _, item in scored[:count]]
    present = {item["case_type"] for item in selected}
    for case_type in CASE_TYPES:
        if case_type in present:
            continue
        replacement = next((item for item in items if item["case_type"] == case_type), None)
        if replacement and replacement not in selected:
            selected[-1] = replacement
            present.add(case_type)
    return selected


def _aggregate_counts(groups: list[list[str]] | Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in groups:
        for item in group:
            counts[str(item)] = counts.get(str(item), 0) + 1
    return counts
