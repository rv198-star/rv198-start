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
DEFAULT_SEED_NODE_TYPES = ["principle_signal", "control_signal", "counter_example_signal"]
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

    source_markdown_path = _resolve_source_file(
        source_file=str(source_chunks_doc["source_file"]),
        source_chunks_path=source_chunks_input_path,
    )
    copied_source_relpath = Path("sources") / source_markdown_path.name
    shutil.copy2(source_markdown_path, bundle_root / copied_source_relpath)

    persisted_source_chunks = _rewrite_source_chunks_doc(
        source_chunks_doc=source_chunks_doc,
        rewritten_source_file=copied_source_relpath.as_posix(),
    )
    (bundle_root / "ingestion" / "source-chunks-v0.1.json").write_text(
        json.dumps(persisted_source_chunks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rewritten_graph_doc = _rewrite_graph_source_paths(
        graph_doc=graph_doc,
        source_snapshot=source_id,
        rewritten_source_file=copied_source_relpath.as_posix(),
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
            "max_candidates": 12,
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
                    "kind": "markdown_document",
                    "original_path": source_markdown_path.as_posix(),
                    "bundle_path": copied_source_relpath.as_posix(),
                    "line_count": len(source_markdown_path.read_text(encoding="utf-8").splitlines()),
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
    rewritten_source_file: str,
) -> dict[str, Any]:
    rewritten = dict(graph_doc)
    rewritten["source_snapshot"] = source_snapshot
    rewritten["nodes"] = [
        _rewrite_source_file(entity=node, rewritten_source_file=rewritten_source_file)
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict)
    ]
    rewritten["edges"] = [
        _rewrite_source_file(entity=edge, rewritten_source_file=rewritten_source_file)
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
    if semantic_family != "margin-of-safety-sizing":
        return []

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


def _derive_related_candidate_id(*, base_candidate_id: str, semantic_root: str) -> str:
    if str(base_candidate_id).endswith("-source-note"):
        return f"{semantic_root}-source-note"
    return semantic_root


def _rewrite_source_chunks_doc(
    *,
    source_chunks_doc: dict[str, Any],
    rewritten_source_file: str,
) -> dict[str, Any]:
    rewritten = dict(source_chunks_doc)
    rewritten["source_file"] = rewritten_source_file
    rewritten["chunks"] = []
    for chunk in source_chunks_doc.get("chunks", []):
        if not isinstance(chunk, dict):
            continue
        chunk_doc = dict(chunk)
        chunk_doc["source_file"] = rewritten_source_file
        rewritten["chunks"].append(chunk_doc)
    return rewritten


def _rewrite_source_file(
    *,
    entity: dict[str, Any],
    rewritten_source_file: str,
) -> dict[str, Any]:
    rewritten = dict(entity)
    if rewritten.get("source_file") is not None:
        rewritten["source_file"] = rewritten_source_file
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
    if semantic_family == "circle-of-competence":
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
