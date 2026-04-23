from __future__ import annotations

import re
from typing import Any


BOOK_OVERVIEW_SCHEMA_VERSION = "kiu.book-overview/v0.1"
DOMAIN_TAG_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "requirements-analysis",
        ("需求", "业务", "接口", "子系统", "模块", "用户", "场景", "边界"),
    ),
    (
        "business-analysis",
        ("业务", "职责", "价值", "结果", "目标", "损失", "协同"),
    ),
    (
        "system-design",
        ("系统", "接口", "模块", "拆分", "结构", "服务", "实现"),
    ),
    (
        "investing",
        ("投资", "估值", "市场", "企业", "股价", "价值", "商业模式"),
    ),
    (
        "accounting-analysis",
        ("会计", "报表", "现金流", "利润", "资产", "资本配置"),
    ),
    (
        "risk-control",
        ("边界", "风险", "失败", "错误", "不能", "不要", "退化", "遗漏"),
    ),
)
BOUNDARY_CUES = (
    "不要",
    "不能",
    "无法",
    "失败",
    "错误",
    "遗漏",
    "重叠",
    "漂移",
    "退化",
    "站不住",
    "不应",
    "不适合",
)
THESIS_SKIP_PREFIXES = ("这是一份用于", "这份文档只保留")


def build_book_overview_doc(source_chunks_doc: dict[str, Any]) -> dict[str, Any]:
    chunks = [
        chunk
        for chunk in source_chunks_doc.get("chunks", [])
        if isinstance(chunk, dict) and chunk.get("chunk_id")
    ]
    chapter_map = _build_chapter_map(source_chunks_doc=source_chunks_doc, chunks=chunks)
    thesis_summary = _build_thesis_summary(chapter_map=chapter_map)
    boundary_warnings = _extract_boundary_warnings(chunks=chunks)
    domain_tags = _derive_domain_tags(chunks=chunks)
    extraction_context = _build_extraction_context(
        chapter_map=chapter_map,
        boundary_warnings=boundary_warnings,
    )

    return {
        "schema_version": BOOK_OVERVIEW_SCHEMA_VERSION,
        "source_id": source_chunks_doc.get("source_id"),
        "source_file": source_chunks_doc.get("source_file"),
        "language": source_chunks_doc.get("language", "zh-CN"),
        "chunk_count": len(chunks),
        "chapter_count": len(chapter_map),
        "section_count": len(
            {
                chunk.get("section")
                for chunk in chunks
                if isinstance(chunk.get("section"), str) and chunk.get("section")
            }
        ),
        "chapter_map": chapter_map,
        "thesis_summary": thesis_summary,
        "boundary_warnings": boundary_warnings,
        "domain_tags": domain_tags,
        "extraction_context": extraction_context,
    }


def validate_book_overview_doc(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("schema_version") != BOOK_OVERVIEW_SCHEMA_VERSION:
        errors.append("book_overview: invalid schema_version")
    for field in ("source_id", "source_file", "language"):
        if not isinstance(doc.get(field), str) or not doc[field]:
            errors.append(f"book_overview: missing {field}")
    for field in ("chunk_count", "chapter_count", "section_count"):
        if not isinstance(doc.get(field), int) or doc[field] < 0:
            errors.append(f"book_overview: invalid {field}")

    chapter_map = doc.get("chapter_map")
    if not isinstance(chapter_map, list) or not chapter_map:
        errors.append("book_overview: chapter_map must be a non-empty list")
    else:
        for index, entry in enumerate(chapter_map):
            label = f"book_overview.chapter_map[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{label}: must be an object")
                continue
            if not isinstance(entry.get("chapter"), str) or not entry["chapter"]:
                errors.append(f"{label}: missing chapter")
            if not isinstance(entry.get("line_start"), int) or entry["line_start"] < 1:
                errors.append(f"{label}: invalid line_start")
            if not isinstance(entry.get("line_end"), int) or entry["line_end"] < entry.get("line_start", 1):
                errors.append(f"{label}: invalid line_end")
            if not isinstance(entry.get("chunk_count"), int) or entry["chunk_count"] < 0:
                errors.append(f"{label}: invalid chunk_count")

    for field in ("thesis_summary", "boundary_warnings", "domain_tags"):
        value = doc.get(field)
        if not isinstance(value, list):
            errors.append(f"book_overview: {field} must be a list")
            continue
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                errors.append(f"book_overview: {field}[{index}] must be a non-empty string")

    extraction_context = doc.get("extraction_context")
    if not isinstance(extraction_context, dict):
        errors.append("book_overview: extraction_context must be an object")
    else:
        for field in ("priority_chapters", "boundary_dense_chapters"):
            value = extraction_context.get(field)
            if not isinstance(value, list):
                errors.append(f"book_overview: extraction_context.{field} must be a list")
                continue
            for index, item in enumerate(value):
                if not isinstance(item, str) or not item:
                    errors.append(
                        f"book_overview: extraction_context.{field}[{index}] must be a non-empty string"
                    )
    return errors


def render_book_overview_markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# BOOK_OVERVIEW",
        "",
        "## Snapshot",
        f"- source_id: `{doc.get('source_id', '<unknown>')}`",
        f"- source_file: `{doc.get('source_file', '<unknown>')}`",
        f"- language: `{doc.get('language', '<unknown>')}`",
        f"- chunk_count: `{doc.get('chunk_count', 0)}`",
        f"- chapter_count: `{doc.get('chapter_count', 0)}`",
        f"- section_count: `{doc.get('section_count', 0)}`",
        "",
        "## Chapter Map",
    ]
    for chapter in doc.get("chapter_map", []):
        lines.extend(
            [
                f"### {chapter.get('chapter', '<unknown>')}",
                f"- lines: `{chapter.get('line_start', 0)}-{chapter.get('line_end', 0)}`",
                f"- chunk_count: `{chapter.get('chunk_count', 0)}`",
                "- chunk_ids: "
                + ", ".join(
                    f"`{chunk_id}`"
                    for chunk_id in chapter.get("chunk_ids", [])
                    if isinstance(chunk_id, str) and chunk_id
                ),
            ]
        )

    lines.extend(["", "## Thesis Summary"])
    for index, thesis in enumerate(doc.get("thesis_summary", []), start=1):
        lines.append(f"{index}. {thesis}")

    lines.extend(["", "## Boundary Warnings"])
    warnings = doc.get("boundary_warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- No explicit boundary warnings were extracted.")

    lines.extend(["", "## Domain Tags"])
    tags = doc.get("domain_tags", [])
    if tags:
        lines.append("- " + ", ".join(f"`{tag}`" for tag in tags))
    else:
        lines.append("- No domain tags inferred.")

    extraction_context = doc.get("extraction_context", {})
    lines.extend(["", "## Extraction Context"])
    lines.append(
        "- priority_chapters: "
        + (
            ", ".join(f"`{item}`" for item in extraction_context.get("priority_chapters", []))
            or "none"
        )
    )
    lines.append(
        "- boundary_dense_chapters: "
        + (
            ", ".join(f"`{item}`" for item in extraction_context.get("boundary_dense_chapters", []))
            or "none"
        )
    )
    lines.append(
        "- note: This artifact provides source context for extraction and review only; it must not carry workflow or agentic routing decisions."
    )
    return "\n".join(lines) + "\n"


def _build_chapter_map(
    *,
    source_chunks_doc: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chunks_by_section: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        section = chunk.get("section")
        if isinstance(section, str) and section:
            chunks_by_section.setdefault(section, []).append(chunk)

    section_entries = [
        entry
        for entry in source_chunks_doc.get("section_map", [])
        if isinstance(entry, dict)
        and isinstance(entry.get("title"), str)
        and entry.get("title")
        and isinstance(entry.get("level"), int)
        and entry["level"] >= 2
    ]
    if not section_entries:
        section_entries = [
            entry
            for entry in source_chunks_doc.get("section_map", [])
            if isinstance(entry, dict)
            and isinstance(entry.get("title"), str)
            and entry.get("title")
        ]

    chapter_map: list[dict[str, Any]] = []
    for entry in section_entries:
        title = entry["title"]
        related_chunks = chunks_by_section.get(title, [])
        if not related_chunks:
            continue
        line_start = min(
            [entry.get("line_start", related_chunks[0].get("line_start", 1))]
            + [chunk.get("line_start", 1) for chunk in related_chunks]
        )
        line_end = max(chunk.get("line_end", line_start) for chunk in related_chunks)
        chapter_map.append(
            {
                "chapter": title,
                "line_start": line_start,
                "line_end": line_end,
                "chunk_count": len(related_chunks),
                "chunk_ids": [chunk["chunk_id"] for chunk in related_chunks if chunk.get("chunk_id")],
                "summary_seed": _extract_summary_seed(related_chunks),
                "boundary_warning_count": _count_boundary_sentences(related_chunks),
            }
        )

    if chapter_map:
        return chapter_map

    if not chunks:
        return []

    return [
        {
            "chapter": str(source_chunks_doc.get("source_id", "source")),
            "line_start": min(chunk.get("line_start", 1) for chunk in chunks),
            "line_end": max(chunk.get("line_end", 1) for chunk in chunks),
            "chunk_count": len(chunks),
            "chunk_ids": [chunk["chunk_id"] for chunk in chunks if chunk.get("chunk_id")],
            "summary_seed": _extract_summary_seed(chunks),
            "boundary_warning_count": _count_boundary_sentences(chunks),
        }
    ]


def _build_thesis_summary(*, chapter_map: list[dict[str, Any]]) -> list[str]:
    summaries: list[str] = []
    for entry in chapter_map:
        summary_seed = entry.get("summary_seed")
        chapter = entry.get("chapter", "chapter")
        if not isinstance(summary_seed, str) or not summary_seed:
            continue
        summaries.append(f"{chapter}: {summary_seed}")
    return summaries[:5]


def _extract_boundary_warnings(*, chunks: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        text = chunk.get("chunk_text")
        if not isinstance(text, str) or not text:
            continue
        for sentence in _split_sentences(text):
            normalized = sentence.strip()
            if not normalized or normalized in seen:
                continue
            if any(cue in normalized for cue in BOUNDARY_CUES):
                warnings.append(normalized)
                seen.add(normalized)
            if len(warnings) >= 6:
                return warnings
    return warnings


def _derive_domain_tags(*, chunks: list[dict[str, Any]]) -> list[str]:
    corpus = "\n".join(
        chunk.get("chunk_text", "")
        for chunk in chunks
        if isinstance(chunk.get("chunk_text"), str)
    )
    scored: list[tuple[int, str]] = []
    for tag, keywords in DOMAIN_TAG_RULES:
        score = sum(corpus.count(keyword) for keyword in keywords)
        if score > 0:
            scored.append((score, tag))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [tag for _, tag in scored[:6]]


def _build_extraction_context(
    *,
    chapter_map: list[dict[str, Any]],
    boundary_warnings: list[str],
) -> dict[str, list[str]]:
    priority_chapters = [
        entry["chapter"]
        for entry in sorted(
            chapter_map,
            key=lambda entry: (
                -int(entry.get("chunk_count", 0) or 0),
                -int(entry.get("boundary_warning_count", 0) or 0),
                str(entry.get("chapter", "")),
            ),
        )[:4]
        if isinstance(entry.get("chapter"), str) and entry.get("chapter")
    ]
    boundary_dense_chapters = [
        entry["chapter"]
        for entry in chapter_map
        if int(entry.get("boundary_warning_count", 0) or 0) > 0
        and isinstance(entry.get("chapter"), str)
        and entry.get("chapter")
    ]
    if boundary_warnings and not boundary_dense_chapters and priority_chapters:
        boundary_dense_chapters = priority_chapters[:1]
    return {
        "priority_chapters": priority_chapters,
        "boundary_dense_chapters": boundary_dense_chapters[:4],
    }


def _extract_summary_seed(chunks: list[dict[str, Any]]) -> str:
    for chunk in chunks:
        text = chunk.get("chunk_text")
        if not isinstance(text, str) or not text:
            continue
        for sentence in _split_sentences(text):
            normalized = sentence.strip()
            if (
                normalized
                and not any(normalized.startswith(prefix) for prefix in THESIS_SKIP_PREFIXES)
                and len(normalized) >= 12
            ):
                return normalized
    return ""


def _count_boundary_sentences(chunks: list[dict[str, Any]]) -> int:
    count = 0
    for chunk in chunks:
        text = chunk.get("chunk_text")
        if not isinstance(text, str) or not text:
            continue
        for sentence in _split_sentences(text):
            if any(cue in sentence for cue in BOUNDARY_CUES):
                count += 1
    return count


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[。！？!?])\s+|\n+", text)
    return [sentence.strip(" \t-") for sentence in sentences if sentence.strip()]
