from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kiu_pipeline.source_shape import classify_source_shape


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paragraph:
    source_file: str
    headings: tuple[tuple[int, str, int], ...]
    line_start: int
    line_end: int
    text: str


def build_source_chunks_from_markdown(
    *,
    input_path: str | Path,
    bundle_id: str,
    source_id: str,
    language: str = "zh-CN",
    max_chars: int = 1200,
) -> dict[str, Any]:
    path = Path(input_path)
    source_file = _to_repo_relative(path)
    source_files = _discover_markdown_sources(path)
    section_map: list[dict[str, Any]] = []
    paragraphs: list[Paragraph] = []
    for source_path in source_files:
        file_source = _to_repo_relative(source_path)
        file_sections, file_paragraphs = _parse_markdown(
            source_path.read_text(encoding="utf-8").splitlines(),
            source_file=file_source,
        )
        section_map.extend(file_sections)
        paragraphs.extend(file_paragraphs)
    section_map, paragraphs = _remove_repeated_boilerplate_headings(
        section_map=section_map,
        paragraphs=paragraphs,
        source_file_count=len(source_files),
    )
    chunks = _paragraphs_to_chunks(
        paragraphs=paragraphs,
        source_id=source_id,
        source_file=source_file,
        language=language,
        max_chars=max_chars,
    )
    doc = {
        "schema_version": "kiu.source-chunks/v0.1",
        "bundle_id": bundle_id,
        "source_id": source_id,
        "source_file": source_file,
        "language": language,
        "section_map": section_map,
        "chunks": chunks,
    }
    if len(source_files) != 1 or path.is_dir():
        doc["source_files"] = [_to_repo_relative(item) for item in source_files]
    doc["source_shape"] = classify_source_shape(doc)
    return doc


def _parse_markdown(
    lines: list[str],
    *,
    source_file: str,
) -> tuple[list[dict[str, Any]], list[Paragraph]]:
    section_map: list[dict[str, Any]] = []
    paragraphs: list[Paragraph] = []
    headings: list[tuple[int, str, int]] = []
    paragraph_lines: list[str] = []
    paragraph_start: int | None = None
    in_frontmatter = False
    frontmatter_seen = False

    def flush_paragraph(line_end: int) -> None:
        nonlocal paragraph_lines, paragraph_start
        if not paragraph_lines or paragraph_start is None:
            paragraph_lines = []
            paragraph_start = None
            return
        text = "\n".join(paragraph_lines).strip()
        if text:
            paragraphs.append(
                Paragraph(
                    source_file=source_file,
                    headings=tuple(headings),
                    line_start=paragraph_start,
                    line_end=line_end,
                    text=text,
                )
            )
        paragraph_lines = []
        paragraph_start = None

    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()

        if line_no == 1 and line.strip() == "---":
            in_frontmatter = True
            frontmatter_seen = True
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            continue

        if frontmatter_seen and line.strip() == "":
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading_match:
            flush_paragraph(line_no - 1)
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            if _is_degenerate_heading(title):
                continue
            headings = headings[: level - 1]
            headings.append((level, title, line_no))
            section_map.append(
                {
                    "level": level,
                    "title": title,
                    "source_file": source_file,
                    "line_start": line_no,
                    "path": [item[1] for item in headings],
                }
            )
            continue

        if _should_skip_line(line):
            flush_paragraph(line_no - 1)
            continue

        if not line.strip():
            flush_paragraph(line_no - 1)
            continue

        if paragraph_start is None:
            paragraph_start = line_no
        paragraph_lines.append(line)

    flush_paragraph(len(lines))
    return section_map, paragraphs


def _remove_repeated_boilerplate_headings(
    *,
    section_map: list[dict[str, Any]],
    paragraphs: list[Paragraph],
    source_file_count: int,
) -> tuple[list[dict[str, Any]], list[Paragraph]]:
    if source_file_count < 3:
        return section_map, paragraphs
    title_files: dict[str, set[str]] = {}
    for entry in section_map:
        title = entry.get("title")
        source_file = entry.get("source_file")
        level = entry.get("level")
        if not isinstance(title, str) or not isinstance(source_file, str):
            continue
        if not isinstance(level, int) or level <= 1:
            continue
        title_files.setdefault(title, set()).add(source_file)
    repeat_threshold = max(3, int(source_file_count * 0.3))
    boilerplate_titles = {
        title for title, files in title_files.items() if len(files) >= repeat_threshold
    }
    if not boilerplate_titles:
        return section_map, paragraphs

    filtered_sections: list[dict[str, Any]] = []
    for entry in section_map:
        if entry.get("title") in boilerplate_titles:
            continue
        section_doc = dict(entry)
        path = section_doc.get("path")
        if isinstance(path, list):
            section_doc["path"] = [item for item in path if item not in boilerplate_titles]
        filtered_sections.append(section_doc)

    filtered_paragraphs = [
        Paragraph(
            source_file=paragraph.source_file,
            headings=tuple(
                item for item in paragraph.headings if item[1] not in boilerplate_titles
            ),
            line_start=paragraph.line_start,
            line_end=paragraph.line_end,
            text=paragraph.text,
        )
        for paragraph in paragraphs
    ]
    return filtered_sections, filtered_paragraphs


def _paragraphs_to_chunks(
    *,
    paragraphs: list[Paragraph],
    source_id: str,
    source_file: str,
    language: str,
    max_chars: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[Paragraph] = []
    current_key: tuple[str, str] | None = None

    def flush_current() -> None:
        nonlocal current, current_key
        if not current:
            return
        chunk_index = len(chunks) + 1
        chapter, section = current_key or (source_id, source_id)
        chunk_text = "\n\n".join(item.text for item in current)
        chunks.append(
            {
                "chunk_id": f"{source_id}:{chunk_index:04d}",
                "source_id": source_id,
                "source_file": current[0].source_file if current else source_file,
                "chapter": chapter,
                "section": section,
                "line_start": current[0].line_start,
                "line_end": current[-1].line_end,
                "chunk_text": chunk_text,
                "token_estimate": _estimate_tokens(chunk_text),
                "language": language,
            }
        )
        current = []
        current_key = None

    for paragraph in paragraphs:
        chapter, section = _resolve_heading_scope(paragraph.headings, source_id)
        para_key = (chapter, section)
        if not current:
            current = [paragraph]
            current_key = para_key
            continue

        proposed_text = "\n\n".join([*(item.text for item in current), paragraph.text])
        if para_key != current_key or len(proposed_text) > max_chars:
            flush_current()
            current = [paragraph]
            current_key = para_key
            continue

        current.append(paragraph)

    flush_current()
    return chunks


def _resolve_heading_scope(
    headings: tuple[tuple[int, str, int], ...],
    source_id: str,
) -> tuple[str, str]:
    if not headings:
        return source_id, source_id

    chapter = headings[0][1]
    section = headings[-1][1]
    if len(headings) == 1:
        return chapter, chapter
    return chapter, section


def _estimate_tokens(text: str) -> int:
    tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]|[^\s]", text)
    return max(len(tokens), 1)


def _should_skip_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("@import "):
        return True
    if re.fullmatch(r"!\[.*?\]\(.*?\)", stripped):
        return True
    return False


def _discover_markdown_sources(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"markdown source not found: {path}")
    markdown_files = [item for item in path.rglob("*.md") if item.is_file()]
    markdown_files = [item for item in markdown_files if not _is_navigation_markdown(item)]
    if not markdown_files:
        raise FileNotFoundError(f"no markdown files found under source directory: {path}")
    return sorted(markdown_files, key=_natural_path_key)


def _is_navigation_markdown(path: Path) -> bool:
    return path.name.lower() in {"summary.md", "readme.md"}


def _is_degenerate_heading(title: str) -> bool:
    normalized = title.strip().strip("#*-_ ")
    if not normalized:
        return True
    if re.fullmatch(r"[0-9]+", normalized):
        return True
    if re.fullmatch(r"[零〇一二三四五六七八九十百千万]+", normalized):
        return True
    return False


def _natural_path_key(path: Path) -> tuple[object, ...]:
    parts: list[object] = []
    for raw_part in path.parts:
        for token in re.split(r"(\d+)", raw_part):
            if not token:
                continue
            parts.append((0, int(token)) if token.isdigit() else (1, token))
    return tuple(parts)


def _to_repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
