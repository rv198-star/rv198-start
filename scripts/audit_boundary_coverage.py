#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit v0.6.8 boundary/scenario coverage against blind-review cases.")
    parser.add_argument("--review-cases", required=True, help="YAML fixture with v0.6.7 blind-review cases.")
    parser.add_argument("--review-pack", default=None, help="Optional clean reviewer pack JSON; option excerpts are audited as artifacts.")
    parser.add_argument("--skill-root", action="append", default=[], help="Root containing SKILL.md files; may be repeated.")
    parser.add_argument("--output", required=True, help="Markdown report output path.")
    parser.add_argument("--min-coverage", type=float, default=0.85, help="Minimum coverage ratio required.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases_doc = yaml.safe_load(Path(args.review_cases).read_text(encoding="utf-8")) or {}
    cases = [case for case in cases_doc.get("cases", []) if isinstance(case, dict)]
    artifacts = _load_artifacts(review_pack=args.review_pack, skill_roots=args.skill_root)
    if not cases:
        raise SystemExit("no review cases found")
    if not artifacts:
        raise SystemExit("no artifacts found")

    rows = [_assess_case(case, artifacts) for case in cases]
    covered = sum(1 for row in rows if row["covered"])
    ratio = covered / len(rows)
    report = _render_report(rows=rows, covered=covered, total=len(rows), ratio=ratio, min_coverage=args.min_coverage)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    summary = {
        "schema_version": "kiu.boundary-coverage-summary/v0.1",
        "case_count": len(rows),
        "covered_count": covered,
        "coverage_ratio": round(ratio, 4),
        "min_coverage": args.min_coverage,
        "passed": ratio >= args.min_coverage,
        "output": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if ratio >= args.min_coverage else 2


def _load_artifacts(*, review_pack: str | None, skill_roots: list[str]) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    if review_pack:
        data = json.loads(Path(review_pack).read_text(encoding="utf-8"))
        for pair in data.get("pairs", []):
            if not isinstance(pair, dict):
                continue
            for side in ("option_a", "option_b"):
                excerpt = str(pair.get(side, {}).get("artifact_excerpt", "") or "")
                if excerpt.strip():
                    artifacts.append({"id": f"{pair.get('pair_id')}:{side}", "text": excerpt})
    for raw_root in skill_roots:
        root = Path(raw_root)
        paths = [root] if root.name == "SKILL.md" else sorted(root.rglob("SKILL.md"))
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            artifacts.append({"id": str(path), "text": text})
    return artifacts


def _assess_case(case: dict[str, Any], artifacts: list[dict[str, str]]) -> dict[str, Any]:
    case_id = str(case.get("case_id", ""))
    case_type = str(case.get("case_type", ""))
    prompt = str(case.get("prompt", ""))
    expected = str(case.get("expected_behavior", ""))
    notes = str(case.get("notes", ""))
    query = "\n".join([prompt, expected, notes])
    required = _required_markers(case_type=case_type, query=query)
    best = {"artifact_id": "", "matched": [], "score": 0}
    for artifact in artifacts:
        matched = _matched_markers(artifact["text"], required)
        score = len(matched)
        overlap = _text_overlap(query, artifact["text"])
        adjusted = score + (1 if overlap >= 0.12 else 0)
        if adjusted > best["score"]:
            best = {"artifact_id": artifact["id"], "matched": matched, "score": adjusted}
    covered = bool(best["matched"]) or (case_type == "should_trigger" and best["score"] >= 1)
    next_action = "covered" if covered else _next_action(case_type, query)
    return {
        "case_id": case_id,
        "case_type": case_type,
        "prompt": prompt,
        "covered": covered,
        "artifact_id": best["artifact_id"],
        "matched_markers": best["matched"],
        "next_action": next_action,
    }


def _required_markers(*, case_type: str, query: str) -> list[str]:
    q = query.lower()
    if case_type == "should_trigger":
        if any(token in q for token in ("短期", "长期", "反噬", "后果", "类比", "史记", "历史")):
            return ["historical-analogy-for-current-decision", "short-gain-long-cost-stress-test", "机制链", "case_pattern"]
        if any(token in q for token in ("越界", "授权", "职责", "角色", "请示", "转交")):
            return ["act-under-ambiguous-mandate", "authority_gap", "role_boundary", "做、少做、请示、转交或拒绝"]
        return ["should_trigger", "next_action"]
    if case_type == "edge_case":
        return ["suggestive-but-different-context", "urgent-but-authorization-unknown", "partial_apply", "ask_or_delegate", "补上下文", "激励不同", "证据不足"]
    markers = ["do_not_fire_when", "不要在以下情况使用", "should_not_trigger"]
    if any(token in q for token in ("评价", "英雄", "人物")):
        markers.extend(["pure_character_evaluation_request", "人物评价"])
    if any(token in q for token in ("观点", "总结")):
        markers.extend(["pure_viewpoint_summary_request", "观点摘要"])
    if any(token in q for token in ("模板", "会议纪要", "流程清单")):
        markers.extend(["mechanical_workflow_template_request", "会议纪要"])
    if any(token in q for token in ("出生", "官职", "时间顺序", "翻译", "古文", "含义", "解释")):
        markers.extend(["fact_lookup", "history_summary_only", "classical_text_translation", "史实查询", "翻译"])
    return markers


def _matched_markers(text: str, markers: list[str]) -> list[str]:
    lowered = text.lower()
    matched = []
    for marker in markers:
        if marker.lower() in lowered:
            matched.append(marker)
    return matched


def _text_overlap(query: str, text: str) -> float:
    q = _tokens(query)
    t = _tokens(text)
    if not q or not t:
        return 0.0
    return len(q & t) / max(4, min(len(q), 20))


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    tokens = set(re.findall(r"[a-z][a-z0-9_-]{2,}", lowered))
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        tokens.add(segment)
        for width in (2, 3, 4):
            if len(segment) >= width:
                tokens.update(segment[i : i + width] for i in range(len(segment) - width + 1))
    return tokens


def _next_action(case_type: str, query: str) -> str:
    if case_type == "should_not_trigger":
        return "Add or expose a named do_not_fire marker for this decoy prompt."
    if case_type == "edge_case":
        return "Add a scenario_families edge_case entry with a concrete partial/defer action."
    return "Add a scenario_families should_trigger entry with prompt signals and next_action."


def _render_report(*, rows: list[dict[str, Any]], covered: int, total: int, ratio: float, min_coverage: float) -> str:
    lines = [
        "# v0.6.8 Boundary Coverage Audit",
        "",
        f"- Cases: `{total}`",
        f"- Covered: `{covered}`",
        f"- Coverage ratio: `{ratio:.4f}`",
        f"- Minimum required: `{min_coverage:.2f}`",
        f"- Status: `{'PASS' if ratio >= min_coverage else 'FAIL'}`",
        "",
        "| case_id | type | covered | matched markers | artifact | next action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        markers = ", ".join(row["matched_markers"]) or "-"
        lines.append(
            f"| {row['case_id']} | {row['case_type']} | {'yes' if row['covered'] else 'no'} | {markers} | {row['artifact_id']} | {row['next_action']} |"
        )
    uncovered = [row for row in rows if not row["covered"]]
    lines.extend(["", "## Uncovered", ""])
    if not uncovered:
        lines.append("All cases are covered.")
    else:
        for row in uncovered:
            lines.append(f"- `{row['case_id']}`: {row['prompt']} -> {row['next_action']}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
