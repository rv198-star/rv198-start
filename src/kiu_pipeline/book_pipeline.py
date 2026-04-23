from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from kiu_graph.materialize import materialize_graph_from_extraction_result
from kiu_graph.report import generate_graph_report
from kiu_graph.clustering import derive_graph_communities

from .book_overview import (
    build_book_overview_doc,
    render_book_overview_markdown,
    validate_book_overview_doc,
)
from .extraction import (
    validate_extraction_result_doc,
    validate_source_chunks_doc,
)
from .extractor_runtime import build_extraction_result_with_audit
from .extraction_bundle import scaffold_extraction_bundle
from .load import extract_yaml_section, parse_sections
from .load import load_source_bundle
from .normalize import normalize_graph
from .preflight import validate_generated_bundle
from .quality import assess_run_quality
from .refiner import refine_bundle_candidates
from .render import (
    load_generated_candidates,
    materialize_refined_candidates,
    render_generated_run,
)
from .reports import (
    reconcile_production_quality_with_review,
    write_production_quality,
    write_three_layer_review,
)
from .review import review_generated_run
from .seed import mine_candidate_seed_assessment
from .source_chunks import build_source_chunks_from_markdown
from .verification_gate import write_seed_verification_reports


def run_book_pipeline(
    *,
    input_path: str | Path,
    bundle_id: str,
    source_id: str,
    run_id: str,
    output_root: str | Path,
    max_chars: int = 1200,
    language: str = "zh-CN",
    deterministic_pass: str = "heuristic-extractors",
    drafting_mode: str = "deterministic",
    inherits_from: str = "default",
    title: str | None = None,
    llm_budget_tokens: int = 100000,
) -> dict[str, Any]:
    output_root = Path(output_root)
    intermediate_root = output_root / "intermediate" / source_id / run_id
    source_root = output_root / "sources" / source_id
    generated_root = output_root / "generated"
    intermediate_root.mkdir(parents=True, exist_ok=True)

    source_chunks_doc = build_source_chunks_from_markdown(
        input_path=input_path,
        bundle_id=bundle_id,
        source_id=source_id,
        language=language,
        max_chars=max_chars,
    )
    source_chunk_errors = validate_source_chunks_doc(source_chunks_doc)
    if source_chunk_errors:
        raise ValueError(f"source-chunks validation failed: {source_chunk_errors}")
    source_chunks_path = intermediate_root / "source-chunks.json"
    _write_json(source_chunks_path, source_chunks_doc)

    book_overview_doc = build_book_overview_doc(source_chunks_doc)
    book_overview_errors = validate_book_overview_doc(book_overview_doc)
    if book_overview_errors:
        raise ValueError(f"book-overview validation failed: {book_overview_errors}")

    extraction_result = _build_extraction_result(
        deterministic_pass=deterministic_pass,
        source_chunks_doc=source_chunks_doc,
    )
    extraction_errors = validate_extraction_result_doc(extraction_result)
    if extraction_errors:
        raise ValueError(f"extraction-result validation failed: {extraction_errors}")
    extraction_result_path = intermediate_root / "extraction-result.json"
    _write_json(extraction_result_path, extraction_result)

    graph_doc = materialize_graph_from_extraction_result(extraction_result)
    graph_path = intermediate_root / "graph.json"
    _write_json(graph_path, graph_doc)

    source_bundle_root = scaffold_extraction_bundle(
        source_chunks_path=source_chunks_path,
        graph_path=graph_path,
        output_root=source_root,
        inherits_from=inherits_from,
        title=title,
    )
    book_overview_paths = _write_book_overview(
        source_bundle_root=source_bundle_root,
        book_overview_doc=book_overview_doc,
    )
    graph_report_path = _write_graph_report(source_bundle_root)

    run_root = _build_candidates(
        source_bundle_root=source_bundle_root,
        generated_root=generated_root,
        run_id=run_id,
        drafting_mode=drafting_mode,
        llm_budget_tokens=llm_budget_tokens,
    )
    _write_smoke_usage_reviews(run_root)
    review_doc = review_generated_run(
        run_root=run_root,
        source_bundle_path=source_bundle_root,
    )
    write_three_layer_review(run_root, review_doc)
    reconcile_production_quality_with_review(run_root, review_doc)

    return {
        "source_bundle_root": str(source_bundle_root),
        "source_chunks_path": str(source_chunks_path),
        "book_overview_path": str(book_overview_paths["markdown_path"]),
        "book_overview_json_path": str(book_overview_paths["json_path"]),
        "extraction_result_path": str(extraction_result_path),
        "graph_path": str(graph_path),
        "graph_report_path": str(graph_report_path),
        "run_root": str(run_root),
        "three_layer_review_path": str(run_root / "reports" / "three-layer-review.json"),
    }


def _build_extraction_result(
    *,
    deterministic_pass: str,
    source_chunks_doc: dict[str, Any],
) -> dict[str, Any]:
    return build_extraction_result_with_audit(
        source_chunks_doc=source_chunks_doc,
        deterministic_pass=deterministic_pass,
        drafting_mode="deterministic",
    )


def _write_graph_report(source_bundle_root: Path) -> Path:
    manifest_path = source_bundle_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    graph_path = source_bundle_root / manifest["graph"]["path"]
    graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
    graph_report_path = source_bundle_root / "GRAPH_REPORT.md"
    graph_report_path.write_text(generate_graph_report(graph_doc), encoding="utf-8")
    manifest["graph_report"] = {
        "path": "GRAPH_REPORT.md",
        "community_count": len(derive_graph_communities(graph_doc)),
    }
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return graph_report_path


def _write_book_overview(
    *,
    source_bundle_root: Path,
    book_overview_doc: dict[str, Any],
) -> dict[str, Path]:
    manifest_path = source_bundle_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    markdown_path = source_bundle_root / "BOOK_OVERVIEW.md"
    json_path = source_bundle_root / "ingestion" / "book-overview-v0.1.json"
    _write_json(json_path, book_overview_doc)
    markdown_path.write_text(
        render_book_overview_markdown(book_overview_doc),
        encoding="utf-8",
    )
    manifest["book_overview"] = {
        "path": "BOOK_OVERVIEW.md",
        "ingestion_path": "ingestion/book-overview-v0.1.json",
        "chapter_count": book_overview_doc.get("chapter_count", 0),
        "domain_tags": list(book_overview_doc.get("domain_tags", [])),
    }
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {
        "markdown_path": markdown_path,
        "json_path": json_path,
    }


def _build_candidates(
    *,
    source_bundle_root: Path,
    generated_root: Path,
    run_id: str,
    drafting_mode: str,
    llm_budget_tokens: int,
) -> Path:
    source_bundle = load_source_bundle(source_bundle_root)
    graph = normalize_graph(source_bundle.graph_doc)
    assessment = mine_candidate_seed_assessment(
        source_bundle,
        graph,
        drafting_mode=drafting_mode,
    )
    seeds = assessment["accepted"]
    run_root = render_generated_run(
        source_bundle=source_bundle,
        seeds=seeds,
        output_root=generated_root,
        run_id=run_id,
    )
    write_seed_verification_reports(
        run_root=run_root,
        summary=assessment["summary"],
    )
    bundle_root = run_root / "bundle"
    candidates = load_generated_candidates(bundle_root)
    refined = refine_bundle_candidates(
        candidates=candidates,
        source_bundle=source_bundle,
        run_root=run_root,
        llm_budget_tokens=llm_budget_tokens,
    )
    materialize_refined_candidates(bundle_root, refined)

    report = validate_generated_bundle(bundle_root)
    if report["errors"]:
        raise ValueError(f"generated bundle validation failed: {report['errors']}")

    quality_report = assess_run_quality(
        candidates=refined,
        profile=source_bundle.profile,
    )
    write_production_quality(run_root, quality_report)
    return run_root


def _write_smoke_usage_reviews(run_root: Path) -> None:
    bundle_root = run_root / "bundle"
    usage_root = run_root / "usage-review"
    usage_root.mkdir(parents=True, exist_ok=True)
    candidates = load_generated_candidates(bundle_root)
    for candidate in candidates:
        skill_id = candidate["candidate"]["candidate_id"]
        anchors = candidate.get("anchors", {})
        source_anchors = anchors.get("source_anchor_sets", [])
        primary_anchor = source_anchors[0] if source_anchors else {}
        secondary_anchor = source_anchors[1] if len(source_anchors) > 1 else primary_anchor
        sections = parse_sections(candidate.get("skill_markdown", ""))
        contract = extract_yaml_section(sections.get("Contract", ""))
        trigger_patterns = [
            item
            for item in contract.get("trigger", {}).get("patterns", [])
            if isinstance(item, str)
        ]
        output_schema = (
            contract.get("judgment_schema", {})
            .get("output", {})
            .get("schema", {})
        )
        verdict = output_schema.get("verdict", "apply")
        evidence_to_check = _derive_smoke_evidence_to_check(
            primary_anchor=primary_anchor,
            secondary_anchor=secondary_anchor,
            trigger_patterns=trigger_patterns,
        )
        next_action = _derive_specific_next_action(
            skill_id=skill_id,
            verdict=verdict if isinstance(verdict, str) else "apply",
            primary_anchor=primary_anchor,
            secondary_anchor=secondary_anchor,
        )
        usage_doc = {
            "review_case_id": f"{skill_id}-smoke-usage",
            "generated_run_root": str(run_root),
            "skill_path": str(bundle_root / "skills" / skill_id / "SKILL.md"),
            "input_scenario": {
                "scenario": primary_anchor.get("snippet", ""),
                "decision_goal": f"Decide whether `{skill_id}` should fire for this source-backed situation.",
                "decision_scope": (
                    f"Only use `{skill_id}` for the decision boundary implied by "
                    f"`{primary_anchor.get('anchor_id', skill_id)}`."
                ),
                "current_constraints": [
                    f"Confirm the scenario still satisfies `{trigger_patterns[0]}`."
                ] if trigger_patterns else [],
                "disconfirming_evidence": [
                    (
                        "Do not apply if new facts contradict the primary evidence "
                        f"anchored at `{primary_anchor.get('anchor_id', skill_id)}`."
                    )
                ],
            },
            "firing_assessment": {
                "should_fire": True,
                "why_this_skill_fired": [
                    f"The scenario directly resembles `{primary_anchor.get('anchor_id', skill_id)}`.",
                    f"The neighboring evidence in `{secondary_anchor.get('anchor_id', skill_id)}` keeps the boundary specific.",
                ],
            },
            "boundary_check": {
                "status": "pass",
                "notes": [
                    "This is an automated smoke usage review, not a production judgment.",
                    "The scenario still includes concrete evidence and decision context.",
                ],
            },
            "structured_output": {
                "verdict": verdict if isinstance(verdict, str) else "apply",
                "next_action": next_action,
                "evidence_to_check": evidence_to_check,
                "decline_reason": (
                    "Decline if the scenario loses concrete decision context or if disconfirming "
                    "evidence overrides the anchored pattern."
                ),
                "confidence": "medium",
            },
            "analysis_summary": (
                f"The smoke review fired `{skill_id}` because the scenario is anchored to "
                f"the same evidence path as `{primary_anchor.get('anchor_id', skill_id)}`."
            ),
            "quality_assessment": {
                "contract_fit": "strong" if trigger_patterns else "medium",
                "evidence_alignment": [
                    anchor.get("anchor_id")
                    for anchor in source_anchors[:2]
                    if isinstance(anchor, dict) and anchor.get("anchor_id")
                ],
                "caveats": [
                    "Replace this smoke review with real usage evidence before release."
                ],
            },
        }
        (usage_root / f"{skill_id}-smoke.yaml").write_text(
            yaml.safe_dump(usage_doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _derive_specific_next_action(
    *,
    skill_id: str,
    verdict: str,
    primary_anchor: dict[str, Any],
    secondary_anchor: dict[str, Any],
) -> str:
    primary_fragment = _smoke_action_fragment(primary_anchor, fallback=skill_id)
    secondary_fragment = _smoke_action_fragment(secondary_anchor, fallback=f"{skill_id}_boundary")
    normalized_verdict = verdict.strip().lower()

    if normalized_verdict == "do_not_apply":
        return f"test_{primary_fragment}_against_{secondary_fragment}_disconfirming_evidence"
    if normalized_verdict == "defer":
        return f"resolve_{secondary_fragment}_before_applying_{primary_fragment}"
    return f"verify_{primary_fragment}_evidence_and_{secondary_fragment}_boundary"


def _derive_smoke_evidence_to_check(
    *,
    primary_anchor: dict[str, Any],
    secondary_anchor: dict[str, Any],
    trigger_patterns: list[str],
) -> list[str]:
    evidence_items: list[str] = []
    for anchor in (primary_anchor, secondary_anchor):
        if not isinstance(anchor, dict):
            continue
        anchor_id = anchor.get("anchor_id")
        snippet = _compact_snippet(anchor.get("snippet", ""))
        if anchor_id:
            detail = f"`{anchor_id}`"
            if snippet:
                detail += f": {snippet}"
            evidence_items.append(detail)
    for pattern in trigger_patterns[:1]:
        evidence_items.append(f"Trigger still satisfied: `{pattern}`")
    return evidence_items or ["Re-check the anchored scenario before applying the draft."]


def _smoke_action_fragment(anchor: dict[str, Any], *, fallback: str) -> str:
    if not isinstance(anchor, dict):
        return _normalize_smoke_symbol(fallback)
    raw = anchor.get("anchor_id") or anchor.get("label") or anchor.get("snippet") or fallback
    return _normalize_smoke_symbol(str(raw))


def _normalize_smoke_symbol(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return normalized or "anchored_evidence"


def _compact_snippet(raw: str, *, limit: int = 96) -> str:
    text = " ".join(str(raw).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
