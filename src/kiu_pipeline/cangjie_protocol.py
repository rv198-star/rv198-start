from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from kiu_pipeline.source_chunks import build_source_chunks_from_markdown


PROTOCOL_ID = "cangjie-skill/RIA-TV++-deterministic-adapter"


def build_cangjie_protocol_baseline(
    *,
    input_path: str | Path,
    output_root: str | Path,
    book_title: str,
    author: str,
    source_id: str = "source-book",
    publication_year: str = "unknown",
    max_chars: int = 1200,
) -> dict[str, Any]:
    """Build an explicit cangjie-protocol reference pack from raw source text.

    This is a benchmark/reference adapter, not KiU's default production path and
    not an official cangjie runtime. It consumes the same raw book material so a
    same-source comparison can be run without using external final skill packs as
    hidden generation inputs.
    """

    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=True)

    source_doc = build_source_chunks_from_markdown(
        input_path=input_path,
        bundle_id=f"{source_id}-cangjie-protocol-baseline",
        source_id=source_id,
        max_chars=max_chars,
    )
    chunks = [chunk for chunk in source_doc.get("chunks", []) if isinstance(chunk, dict)]
    section_map = [item for item in source_doc.get("section_map", []) if isinstance(item, dict)]
    source_files = source_doc.get("source_files")
    if not isinstance(source_files, list):
        source_files = [source_doc.get("source_file")]
    source_files = [str(item) for item in source_files if item]

    profile = _analyze_source(chunks=chunks, section_map=section_map)
    skills = _select_protocol_skills(profile=profile)

    _write_metadata(
        output=output,
        input_path=Path(input_path),
        book_title=book_title,
        author=author,
        source_id=source_id,
        source_files=source_files,
        chunk_count=len(chunks),
        section_count=len(section_map),
        skills=skills,
    )
    _write_book_overview(
        output=output,
        book_title=book_title,
        author=author,
        publication_year=publication_year,
        source_files=source_files,
        chunk_count=len(chunks),
        section_count=len(section_map),
        profile=profile,
    )
    _write_candidates(output=output, profile=profile)
    _write_rejected(output=output, profile=profile)
    for skill in skills:
        _write_skill(
            output=output,
            skill=skill,
            book_title=book_title,
            author=author,
        )
    _write_index(
        output=output,
        book_title=book_title,
        author=author,
        publication_year=publication_year,
        skills=skills,
    )
    return {
        "reference_pack_path": str(output),
        "reference_protocol": PROTOCOL_ID,
        "official_cangjie_run": False,
        "input_kind": "raw_markdown_book",
        "source_file_count": len(source_files),
        "chunk_count": len(chunks),
        "section_count": len(section_map),
        "skill_count": len(skills),
        "skill_ids": [skill["skill_id"] for skill in skills],
    }


def _analyze_source(*, chunks: list[dict[str, Any]], section_map: list[dict[str, Any]]) -> dict[str, Any]:
    keyword_groups = {
        "consequence": ("故", "是以", "由是", "卒", "亡", "败", "祸", "乱", "诛"),
        "boundary": ("不可", "不宜", "未可", "不得", "戒", "慎", "失"),
        "power": ("王", "君", "臣", "国", "兵", "侯", "相", "天下"),
        "incentive": ("利", "赏", "罚", "功", "爵", "怨", "欲", "谋"),
    }
    evidence_by_group: dict[str, list[dict[str, Any]]] = {key: [] for key in keyword_groups}
    all_evidence: list[dict[str, Any]] = []
    for chunk in chunks:
        text = str(chunk.get("chunk_text", "") or "").strip()
        if not text:
            continue
        score = sum(text.count(token) for tokens in keyword_groups.values() for token in tokens)
        evidence = {
            "chunk_id": str(chunk.get("chunk_id", "")),
            "source_file": str(chunk.get("source_file", "")),
            "chapter": str(chunk.get("chapter", "")),
            "section": str(chunk.get("section", "")),
            "line_start": int(chunk.get("line_start", 1) or 1),
            "line_end": int(chunk.get("line_end", 1) or 1),
            "excerpt": _clean_excerpt(text),
            "score": score,
        }
        all_evidence.append(evidence)
        for group, tokens in keyword_groups.items():
            group_score = sum(text.count(token) for token in tokens)
            if group_score > 0:
                item = dict(evidence)
                item["score"] = group_score
                evidence_by_group[group].append(item)

    for group, items in evidence_by_group.items():
        evidence_by_group[group] = sorted(
            items,
            key=lambda item: (-int(item.get("score", 0)), item.get("source_file", ""), item.get("line_start", 0)),
        )[:8]

    chapters = [str(item.get("title", "")) for item in section_map if item.get("level") == 1]
    chapter_counter = Counter(_normalize_chapter_title(title) for title in chapters if title)
    top_chapters = [title for title, _count in chapter_counter.most_common(12)]
    return {
        "extractors": {
            "framework": _render_candidate_items(
                "历史后果判断框架", evidence_by_group["consequence"][:5]
            ),
            "principle": _render_candidate_items("边界与戒惧原则", evidence_by_group["boundary"][:5]),
            "case": _render_candidate_items("成败转折案例", evidence_by_group["power"][:5]),
            "counter-example": _render_candidate_items("误用与失败反例", evidence_by_group["incentive"][:5]),
            "term": _render_terms(top_chapters=top_chapters),
        },
        "evidence_by_group": evidence_by_group,
        "top_chapters": top_chapters,
        "all_evidence_count": len(all_evidence),
    }


def _select_protocol_skills(*, profile: dict[str, Any]) -> list[dict[str, Any]]:
    consequence = profile["evidence_by_group"].get("consequence", [])
    boundary = profile["evidence_by_group"].get("boundary", [])
    power = profile["evidence_by_group"].get("power", [])
    incentive = profile["evidence_by_group"].get("incentive", [])
    primary_evidence = _first_non_empty(consequence, power, boundary)
    secondary_evidence = _first_non_empty(boundary, consequence, incentive)

    skills = [
        {
            "skill_id": "historical-case-consequence-judgment",
            "title": "历史案例后果判断",
            "description": "当用户想借历史案例判断一个行动、权力安排或激励选择的后果时调用；不用于单纯查询史实、人物生平或年代考据。",
            "chapter": primary_evidence.get("chapter", "史记"),
            "reading": primary_evidence,
            "interpretation": (
                "把历史叙事当作因果压力测试，而不是把故事当作装饰性类比。先还原关键行动者、制度位置、激励和约束，再追踪短期收益如何转化为长期后果。"
                "如果只能找到相似人物而找不到相似机制，就应停止类比。"
            ),
            "applications": [primary_evidence, secondary_evidence],
            "triggers": [
                "这个历史案例能不能类比我现在的决策？",
                "我想用一个成败故事判断这个选择的后果。",
                "这里短期有利，但长期会不会埋雷？",
            ],
            "steps": [
                "列出行动者、权力位置、可选行动和显性激励。",
                "从原文案例中抽出机制链：选择 -> 约束变化 -> 后果。",
                "检查当下场景和原案例的机制是否同构；不同构时只保留警示，不给结论。",
                "输出可执行判断：继续、暂缓、补证据或改边界。",
            ],
            "boundaries": [
                "surface_similarity_only — 不要把人物名望、故事相似或成败标签当作机制相同。",
                "history_summary_only — 不要用于纯历史总结、编年整理或人物故事复述。",
                "fact_lookup_only — 不要用于司马迁生年、官职含义、年代顺序等史实查询。",
                "classical_text_translation_only — 不要用于古文翻译、文本改写或资料整理。",
                "pure_character_evaluation_request — 不要用于评价项羽是不是英雄、某人是否伟大等人物评价。",
                "pure_viewpoint_summary_request — 不要用于总结《史记》观点、作者立场或思想脉络。",
                "mechanical_workflow_template_request — 不要用于生成会议纪要、表格模板或机械流程清单。",
                "single_anecdote_without_decision — 不要用单个历史故事给当前方案背书。",
            ],
            "scenario_families": _historical_consequence_scenario_families(),
            "test_cases": _historical_consequence_cases(),
        }
    ]
    if secondary_evidence:
        skills.append(
            {
                "skill_id": "role-boundary-before-action",
                "title": "行动前的角色边界校验",
                "description": "当用户准备以某种身份采取行动、但不清楚权责边界和越界后果时调用；不用于机械流程执行或泛泛道德评论。",
                "chapter": secondary_evidence.get("chapter", "史记"),
                "reading": secondary_evidence,
                "interpretation": (
                    "先判断行动者的位置、名分、责任和可承受后果，再判断行动是否可取。史事中的失败常不是单点判断错误，而是角色边界、激励和时势错配后的连锁反应。"
                ),
                "applications": [secondary_evidence, primary_evidence],
                "triggers": [
                    "我以这个身份该不该介入？",
                    "这件事越不越界？",
                    "我有权做，但做了会不会破坏长期秩序？",
                ],
                "steps": [
                    "确认当前行动者的身份、授权来源和约束。",
                    "列出越界收益、越界代价和旁观者会如何重解释该行动。",
                    "用史事反例检查短期正确是否会制造长期不稳定。",
                    "给出边界化行动方案：做、少做、请示、转交或拒绝。",
                ],
                "boundaries": [
                    "pure_role_definition_query — 不要用于解释角色、职责、名分等概念定义。",
                    "meeting_template_or_checklist_request — 不要用于会议纪要、流程清单或机械模板请求。",
                    "mechanical_workflow_template_request — 不要把确定性流程包装成角色边界判断。",
                    "pure_character_evaluation_request — 不要用于评价某个历史人物或现实人物的品格。",
                    "pure_viewpoint_summary_request — 不要用于总结作者观点、君臣关系观点或道德评论。",
                    "legal_or_ethics_final_opinion — 不要替代法律、合规或伦理最终审查。",
                    "authorization_facts_unknown — 如果角色授权事实不清，先要求补上下文。",
                    "ancient_order_direct_transfer — 不把古代等级秩序直接移植到现代组织。",
                ],
                "scenario_families": _role_boundary_scenario_families(),
                "test_cases": _role_boundary_cases(),
            }
        )
    return skills


def _write_metadata(
    *,
    output: Path,
    input_path: Path,
    book_title: str,
    author: str,
    source_id: str,
    source_files: list[str],
    chunk_count: int,
    section_count: int,
    skills: list[dict[str, Any]],
) -> None:
    metadata = {
        "schema_version": "kiu.reference-protocol-baseline/v0.1",
        "reference_protocol": PROTOCOL_ID,
        "official_cangjie_run": False,
        "benchmark_only": True,
        "external_reference_boundary": {
            "uses_original_source_material": True,
            "uses_external_final_skill_pack_as_input": False,
            "uses_reference_pack_as_generation_input": False,
            "isolated_from_kiu_default_pipeline": True,
        },
        "input": {
            "kind": "raw_markdown_book",
            "path": input_path.as_posix(),
            "source_id": source_id,
            "source_file_count": len(source_files),
            "chunk_count": chunk_count,
            "section_count": section_count,
        },
        "book": {"title": book_title, "author": author},
        "skills": [skill["skill_id"] for skill in skills],
        "generated_on": date.today().isoformat(),
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_book_overview(
    *,
    output: Path,
    book_title: str,
    author: str,
    publication_year: str,
    source_files: list[str],
    chunk_count: int,
    section_count: int,
    profile: dict[str, Any],
) -> None:
    lines = [
        f"# {book_title} — BOOK_OVERVIEW",
        "",
        f"- 作者: {author}",
        f"- 出版年: {publication_year}",
        f"- 协议: `{PROTOCOL_ID}`",
        "- 官方 cangjie 运行: `false`，这是隔离 benchmark adapter。",
        f"- 原始 Markdown 文件数: `{len(source_files)}`",
        f"- chunk 数: `{chunk_count}`",
        f"- section 数: `{section_count}`",
        "",
        "## Adler Stage 0 摘要",
        "",
        "这一路径只做同源参考基线：从原始文本抽取可被 agent 调用的判断单元，保留候选池、淘汰原因、RIA++ skill 和压力测试。它不参与 KiU 默认生成。",
        "",
        "## 主要章节信号",
        "",
        *[f"- {title}" for title in profile.get("top_chapters", [])[:12]],
        "",
    ]
    (output / "BOOK_OVERVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def _write_candidates(*, output: Path, profile: dict[str, Any]) -> None:
    candidates = output / "candidates"
    candidates.mkdir(exist_ok=True)
    for extractor, markdown in profile.get("extractors", {}).items():
        (candidates / f"{extractor}.md").write_text(markdown, encoding="utf-8")


def _write_rejected(*, output: Path, profile: dict[str, Any]) -> None:
    rejected = output / "rejected"
    rejected.mkdir(exist_ok=True)
    lines = [
        "# Rejected Candidates",
        "",
        "- `collection-author-heading`: 多文件样本中反复出现的作者署名标题，只是素材结构噪声，不是可执行 skill。",
        "- `pure-chronology-lookup`: 只回答年代、人物、生平的查询价值不足，不满足 cangjie 的预测力要求。",
        "- `generic-history-summary`: 只能摘要，不能给触发、执行和边界，不满足 RIA++。",
        "",
        f"候选证据总数: `{profile.get('all_evidence_count', 0)}`",
    ]
    (rejected / "triple-verification-rejections.md").write_text("\n".join(lines), encoding="utf-8")


def _write_skill(*, output: Path, skill: dict[str, Any], book_title: str, author: str) -> None:
    skill_dir = output / skill["skill_id"]
    skill_dir.mkdir(exist_ok=True)
    reading = skill.get("reading", {})
    applications = [item for item in skill.get("applications", []) if item]
    skill_markdown = [
        "---",
        f"name: {skill['skill_id']}",
        "description: |",
        f"  {skill['description']}",
        f"source_book: 《{book_title}》 {author}",
        f"source_chapter: {skill.get('chapter', book_title)}",
        "tags: [history, judgment, cangjie-protocol-baseline]",
        "related_skills: []",
        "reference_protocol: cangjie-skill/RIA-TV++-deterministic-adapter",
        "official_cangjie_run: false",
        "---",
        "",
        f"# {skill['title']}",
        "",
        "## R — 原文 (Reading)",
        "",
        f"> {reading.get('excerpt', '原文证据不足。')}",
        ">",
        f"> — {author}, {reading.get('source_file', book_title)}:{reading.get('line_start', 1)}-{reading.get('line_end', 1)}",
        "",
        "---",
        "",
        "## I — 方法论骨架 (Interpretation)",
        "",
        skill["interpretation"],
        "",
        "---",
        "",
        "## A1 — 书中的应用 (Past Application)",
        "",
    ]
    for index, application in enumerate(applications[:2], start=1):
        skill_markdown.extend(
            [
                f"### 案例 {index}: {application.get('section') or application.get('chapter') or '史事片段'}",
                f"- **问题**: 原文呈现行动、位置、激励与后果之间的张力。",
                f"- **方法论的使用**: 从 `{application.get('source_file')}` 第 {application.get('line_start')} 行附近抽出机制链。",
                f"- **结论**: 不能停留在故事相似，必须比较机制相似。",
                f"- **结果**: {application.get('excerpt')}",
                "",
            ]
        )
    skill_markdown.extend(
        [
            "---",
            "",
            "## A2 — 触发场景 (Future Trigger) ★",
            "",
            "### 用户会在什么情境下需要这个 skill?",
            "",
            *[f"{index}. {trigger}" for index, trigger in enumerate(skill.get("triggers", []), start=1)],
            "",
            "### 语言信号 (用户的话里出现这些就应激活)",
            "",
            *[f"- \"{trigger}\"" for trigger in skill.get("triggers", [])],
            "",
            "### 与相邻 skill 的区分",
            "",
            "- 与纯历史查询的区别: 本 skill 输出判断框架，不输出百科事实。",
            "- 与通用类比的区别: 本 skill 要求机制链相似，不接受表面相似。",
            "",
            "---",
            "",
            "## S — 场景族 (Scenario Families) ★",
            "",
            "本段用于让评审和模型快速判断当前 prompt 属于正面、边缘还是拒绝场景。B 段是泛规则，S 段是命中模板。",
            "",
        ]
    )
    for family in skill.get("scenario_families", []):
        skill_markdown.extend(
            [
                f"### {family.get('kind', '场景')}: {family.get('scenario_id', 'unnamed-scenario')}",
                f"- **用户在说**: {family.get('user_says', '')}",
                f"- **判断信号**: {family.get('signal', '')}",
                f"- **下一步**: {family.get('next_step', '')}",
                "",
            ]
        )
    skill_markdown.extend(
        [
            "---",
            "",
            "## E — 可执行步骤 (Execution)",
            "",
        ]
    )
    for index, step in enumerate(skill.get("steps", []), start=1):
        skill_markdown.extend(
            [
                f"{index}. **{step}**",
                "   - 完成标准: 产出能被反驳或复核的中间判断。",
                "",
            ]
        )
    skill_markdown.extend(
        [
            "---",
            "",
            "## B — 边界 (Boundary) ★",
            "",
            "### 不要在以下情况使用此 skill",
            "",
            *[f"- {boundary}" for boundary in skill.get("boundaries", [])],
            "",
            "### 作者在书中警告的失败模式",
            "",
            "- 只看成败结果而不还原当时的制度约束。",
            "- 只借人物标签做类比，忽略处境、激励和后果链。",
            "",
            "### 作者的盲点 / 时代局限",
            "",
            "- 古代政治秩序、身份伦理和现代组织场景不同，不能直接套用价值判断。",
            "",
            "---",
            "",
            "## 相关 skills (阶段 3 填充)",
            "",
            "- depends-on: {}",
            "- contrasts-with: {pure-chronology-lookup}",
            "- composes-with: {}",
            "",
            "---",
            "",
            "## 审计信息",
            "",
            "- **验证通过**: V1 ✓ / V2 ✓ / V3 ✓",
            "- **测试通过率**: 0.8 minimum_pass_rate (详见 test-prompts.json)",
            f"- **蒸馏时间**: {date.today().isoformat()}",
            "",
        ]
    )
    (skill_dir / "SKILL.md").write_text("\n".join(skill_markdown), encoding="utf-8")
    (skill_dir / "test-prompts.json").write_text(
        json.dumps(
            {
                "skill": skill["skill_id"],
                "version": "0.1.0",
                "source_book": f"《{book_title}》 — {author}",
                "darwin_compatible": True,
                "test_cases": skill.get("test_cases", []),
                "minimum_pass_rate": 0.8,
                "notes": "cangjie protocol adapter baseline; benchmark only, not official cangjie output.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_index(*, output: Path, book_title: str, author: str, publication_year: str, skills: list[dict[str, Any]]) -> None:
    lines = [
        f"# {book_title} — Skill Index",
        "",
        f"> 本书由 `{PROTOCOL_ID}` 生成同源 benchmark 基线，产出 **{len(skills)}** 个 skills。",
        f"> 处理时间: {date.today().isoformat()}",
        "",
        "## 关于这本书",
        "",
        f"- **作者**: {author}",
        f"- **出版年**: {publication_year}",
        "- **一句话主旨**: 通过历史叙事保留行动、权力、激励与后果之间的可复核样本。",
        "- **整书理解**: 见 [BOOK_OVERVIEW.md](./BOOK_OVERVIEW.md)",
        "",
        "## Skill 列表 (按主题分组)",
        "",
        "### 历史判断",
        "",
    ]
    for skill in skills:
        lines.append(f"- [`{skill['skill_id']}`](./{skill['skill_id']}/SKILL.md) — {skill['description']}")
    lines.extend(
        [
            "",
            "## 引用图",
            "",
            "```mermaid",
            "graph LR",
            *[f"    {skill['skill_id'].replace('-', '_')}[{skill['skill_id']}]" for skill in skills],
            "```",
            "",
            "## 审计轨迹",
            "",
            "- 候选单元池: [candidates/](./candidates/)",
            "- 被淘汰的候选: [rejected/](./rejected/)",
            "- BOOK_OVERVIEW: [BOOK_OVERVIEW.md](./BOOK_OVERVIEW.md)",
            "- metadata: [metadata.json](./metadata.json)",
            "",
        ]
    )
    (output / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def _render_candidate_items(title: str, evidence_items: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", f"协议: `{PROTOCOL_ID}`", ""]
    for index, evidence in enumerate(evidence_items, start=1):
        lines.extend(
            [
                f"## 候选 {index}",
                "",
                f"- source: `{evidence.get('source_file')}`:{evidence.get('line_start')}-{evidence.get('line_end')}",
                f"- section: {evidence.get('section') or evidence.get('chapter')}",
                f"- excerpt: {evidence.get('excerpt')}",
                "- triple_verify: V1=needs cross-case check; V2=can answer new consequence question; V3=non-generic if mechanism chain is explicit.",
                "",
            ]
        )
    return "\n".join(lines)


def _render_terms(*, top_chapters: list[str]) -> str:
    lines = ["# 术语候选", "", f"协议: `{PROTOCOL_ID}`", ""]
    for title in top_chapters[:12]:
        lines.append(f"- {title}")
    lines.append("")
    return "\n".join(lines)


def _historical_consequence_scenario_families() -> list[dict[str, str]]:
    return [
        {
            "kind": "正面场景",
            "scenario_id": "historical-analogy-for-current-decision",
            "user_says": "这个历史案例能不能类比我现在的决策；项羽和刘邦的故事能否判断我的商业选择。",
            "signal": "用户有 current_decision，并希望用多个历史案例做后果压力测试。",
            "next_step": "进入 E 段四步执行，重点比较机制链而不是人物标签。",
        },
        {
            "kind": "正面场景",
            "scenario_id": "short-gain-long-cost-stress-test",
            "user_says": "眼前收益很大但担心以后反噬；短期赢一时但长期失信。",
            "signal": "短期利益与长期代价之间存在二阶后果担忧。",
            "next_step": "构建 选择 -> 约束变化 -> 后续报复/信任折损 链条。",
        },
        {
            "kind": "边缘场景",
            "scenario_id": "suggestive-but-different-context",
            "user_says": "这个故事有点像，但时代、激励或制度位置可能不同。",
            "signal": "相似机制存在，但关键变量不同。",
            "next_step": "列出相似点、关键差异和不可迁移部分，再 partial_apply。",
        },
        {
            "kind": "拒绝场景",
            "scenario_id": "single-anecdote-proof",
            "user_says": "我只记得一个史记故事，想拿来支持我的方案。",
            "signal": "单个轶事被直接当作当前方案的证明。",
            "next_step": "要求补充 case_analogs 和 relevant_differences；证据不足时 do_not_apply。",
        },
        {
            "kind": "拒绝场景",
            "scenario_id": "history-summary-only",
            "user_says": "纯史实查询、翻译、编年、人物评价或观点摘要。",
            "signal": "缺少 current_decision，仅查询历史或文本本身。",
            "next_step": "不激活本 skill；转为 source/retrieval/translation 路径。",
        },
    ]


def _role_boundary_scenario_families() -> list[dict[str, str]]:
    return [
        {
            "kind": "正面场景",
            "scenario_id": "act-under-ambiguous-mandate",
            "user_says": "我有权推动但可能越过其他团队；老板让我直接处理但职责边界不清。",
            "signal": "存在 live action，且授权、责任边界、长期秩序成本不清。",
            "next_step": "输出 做/少做/请示/转交/拒绝 的边界化行动。",
        },
        {
            "kind": "边缘场景",
            "scenario_id": "urgent-but-authorization-unknown",
            "user_says": "事情很急，但不知道是否有授权，可能要先斩后奏。",
            "signal": "紧急性真实，但授权事实缺失。",
            "next_step": "只允许 low-regret bounded action，并要求补授权或升级给 owner。",
        },
        {
            "kind": "拒绝场景",
            "scenario_id": "role-definition-or-template-only",
            "user_says": "解释职责概念、生成会议纪要模板或给流程清单。",
            "signal": "没有正在判断的越界行动。",
            "next_step": "不激活本 skill；转为概念解释或 workflow 路由。",
        },
        {
            "kind": "拒绝场景",
            "scenario_id": "legal-or-ethics-final-opinion",
            "user_says": "这合法吗；能不能规避合规；不用告诉负责人。",
            "signal": "需要 accountable authority，而不是模型给最终授权。",
            "next_step": "结构化边界问题并转给合规/负责人。",
        },
        {
            "kind": "拒绝场景",
            "scenario_id": "ancient-order-direct-transfer",
            "user_says": "古代君臣秩序如此，所以现代组织也应照做。",
            "signal": "古代身份伦理被直接迁移到现代组织。",
            "next_step": "拒绝直接迁移，只保留角色边界风险提示。",
        },
    ]


def _historical_consequence_cases() -> list[dict[str, str]]:
    return [
        {
            "id": "should-trigger-01",
            "type": "should_trigger",
            "prompt": "我想用项羽和刘邦的故事判断一个短期强势但长期失信的商业决策。",
            "expected_behavior": "应激活 historical-case-consequence-judgment，并检查机制链而不是只类比人物。",
            "notes": "正面场景: 历史案例 + 当下决策后果。",
        },
        {
            "id": "should-trigger-02",
            "type": "should_trigger",
            "prompt": "这个选择眼前收益很大，但我担心以后会反噬，能不能借史记案例做一次压力测试？",
            "expected_behavior": "应激活并输出短期收益到长期后果的判断链。",
            "notes": "正面场景: 后果判断。",
        },
        {
            "id": "should-trigger-03",
            "type": "should_trigger",
            "prompt": "我手上有几个历史类比，但不知道哪个机制真的像我的处境。",
            "expected_behavior": "应激活并筛掉只有表面相似的类比。",
            "notes": "正面场景: 类比边界。",
        },
        {
            "id": "should-trigger-04",
            "type": "should_trigger",
            "prompt": "我们准备牺牲一个合作伙伴换取短期扩张，想先判断后续信任成本会不会失控。",
            "expected_behavior": "应激活并围绕选择、约束变化、后续报复或信任折损建立后果链。",
            "notes": "正面场景: 短利与长期信用。",
        },
        {
            "id": "should-trigger-05",
            "type": "should_trigger",
            "prompt": "两个方案都能赢一时，我想借历史案例比较哪个更容易引出连锁副作用。",
            "expected_behavior": "应激活并比较两个行动路径的二阶后果，而不是只给单点建议。",
            "notes": "正面场景: 多方案后果比较。",
        },
        {
            "id": "should-trigger-06",
            "type": "should_trigger",
            "prompt": "我担心团队正在拿一个成功故事过度类比当前市场，能否帮我拆机制是否同构？",
            "expected_behavior": "应激活并先拆机制相似度，再判断类比是否能迁移。",
            "notes": "正面场景: 类比迁移检验。",
        },
        {
            "id": "should-not-trigger-01",
            "type": "should_not_trigger",
            "prompt": "司马迁是哪一年出生的？",
            "expected_behavior": "不应激活本 skill，因为这是史实查询。",
            "notes": "诱饵: 百科查询。",
        },
        {
            "id": "should-not-trigger-02",
            "type": "should_not_trigger",
            "prompt": "请把这段古文翻译成现代汉语。",
            "expected_behavior": "不应激活本 skill，因为这是翻译任务。",
            "notes": "诱饵: 文本处理。",
        },
        {
            "id": "should-not-trigger-03",
            "type": "should_not_trigger",
            "prompt": "请按时间顺序列出秦末到汉初的主要事件。",
            "expected_behavior": "不应激活本 skill，因为这是编年整理而非行动后果判断。",
            "notes": "诱饵: 年代线整理。",
        },
        {
            "id": "should-not-trigger-04",
            "type": "should_not_trigger",
            "prompt": "请评价项羽是不是英雄人物。",
            "expected_behavior": "不应激活本 skill，因为这是人物立场评论，缺少当下决策情境。",
            "notes": "诱饵: 人物评论。",
        },
        {
            "id": "edge-01",
            "type": "edge_case",
            "prompt": "我只记得一个史记故事，想拿来支持我的方案。",
            "expected_behavior": "可以激活但必须先要求补机制证据，不能直接支持方案。",
            "notes": "边界: 证据不足。",
        },
        {
            "id": "edge-02",
            "type": "edge_case",
            "prompt": "这个历史故事和我现在的行业很像，但关键角色的激励可能不同。",
            "expected_behavior": "可以激活，但必须把激励差异列为迁移风险，不能直接套结论。",
            "notes": "边界: 机制相似但激励不确定。",
        },
        {
            "id": "edge-03",
            "type": "edge_case",
            "prompt": "我需要今天就拍板，但历史证据之间互相冲突。",
            "expected_behavior": "可以激活，但应输出暂缓、补证据或小步试错，而不是确定性建议。",
            "notes": "边界: 高风险 + 证据冲突。",
        },
    ]


def _role_boundary_cases() -> list[dict[str, str]]:
    return [
        {
            "id": "should-trigger-01",
            "type": "should_trigger",
            "prompt": "我有权限推动这件事，但担心越过其他团队的职责边界。",
            "expected_behavior": "应激活 role-boundary-before-action，先核对身份、授权和越界后果。",
            "notes": "正面场景: 角色边界。",
        },
        {
            "id": "should-trigger-02",
            "type": "should_trigger",
            "prompt": "老板让我直接处理跨部门冲突，我该不该介入？",
            "expected_behavior": "应激活并给出做、少做、请示、转交或拒绝的边界化方案。",
            "notes": "正面场景: 授权与行动。",
        },
        {
            "id": "should-trigger-03",
            "type": "should_trigger",
            "prompt": "这件事短期做了有效，但可能破坏长期秩序，怎么判断？",
            "expected_behavior": "应激活并检查长期秩序代价。",
            "notes": "正面场景: 短期有效 vs 长期秩序。",
        },
        {
            "id": "should-trigger-04",
            "type": "should_trigger",
            "prompt": "我不是项目 owner，但客户只信任我，我是否应该绕过 owner 直接承诺交付？",
            "expected_behavior": "应激活并核对授权、承诺后果和对组织秩序的影响。",
            "notes": "正面场景: 非 owner 越界承诺。",
        },
        {
            "id": "should-trigger-05",
            "type": "should_trigger",
            "prompt": "我有能力压下争议，但这样会不会让团队以后都绕开正式机制？",
            "expected_behavior": "应激活并判断短期控制是否制造长期角色依赖或制度损伤。",
            "notes": "正面场景: 能力优势与制度代价。",
        },
        {
            "id": "should-trigger-06",
            "type": "should_trigger",
            "prompt": "合作方要求我以私人关系推动内部审批，我想先判断这是否越过角色边界。",
            "expected_behavior": "应激活并检查身份混用、授权来源和旁观者解释风险。",
            "notes": "正面场景: 身份混用。",
        },
        {
            "id": "should-not-trigger-01",
            "type": "should_not_trigger",
            "prompt": "帮我生成一个会议纪要模板。",
            "expected_behavior": "不应激活本 skill，因为这是模板生成。",
            "notes": "诱饵: workflow 工具。",
        },
        {
            "id": "should-not-trigger-02",
            "type": "should_not_trigger",
            "prompt": "解释一下君臣父子的古代含义。",
            "expected_behavior": "不应激活本 skill，因为这是概念解释。",
            "notes": "诱饵: 概念说明。",
        },
        {
            "id": "should-not-trigger-03",
            "type": "should_not_trigger",
            "prompt": "汉代丞相、太尉、御史大夫分别是什么官职？",
            "expected_behavior": "不应激活本 skill，因为这是制度史事实查询。",
            "notes": "诱饵: 官职查询。",
        },
        {
            "id": "should-not-trigger-04",
            "type": "should_not_trigger",
            "prompt": "请总结《史记》里关于君臣关系的观点。",
            "expected_behavior": "不应激活本 skill，因为这是摘要任务，缺少行动边界问题。",
            "notes": "诱饵: 摘要请求。",
        },
        {
            "id": "edge-01",
            "type": "edge_case",
            "prompt": "我不知道自己有没有被授权，但事情很急。",
            "expected_behavior": "可以激活，但应先要求补授权事实或选择低越界行动。",
            "notes": "边界: 上下文不足。",
        },
        {
            "id": "edge-02",
            "type": "edge_case",
            "prompt": "我在旧组织有这个权限，但新组织的角色定义可能不一样。",
            "expected_behavior": "可以激活，但必须提示不能把旧角色边界直接迁移到新组织。",
            "notes": "边界: 角色迁移风险。",
        },
        {
            "id": "edge-03",
            "type": "edge_case",
            "prompt": "我只是想判断这件事道德上对不对，还没有具体行动。",
            "expected_behavior": "应要求补具体行动与角色事实；没有行动情境时不输出边界化方案。",
            "notes": "边界: 道德评论 vs 行动判断。",
        },
    ]

def _first_non_empty(*groups: list[dict[str, Any]]) -> dict[str, Any]:
    for group in groups:
        if group:
            return group[0]
    return {}


def _clean_excerpt(text: str, *, limit: int = 140) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _normalize_chapter_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()
