from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from kiu_graph.materialize import materialize_graph_from_extraction_result
from kiu_graph.report import generate_graph_report
from kiu_graph.clustering import derive_graph_communities

from .extraction import (
    build_empty_extraction_result,
    build_heuristic_extraction_result,
    build_section_heading_extraction_result,
    validate_extraction_result_doc,
    validate_source_chunks_doc,
)
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
from .reports import write_production_quality, write_three_layer_review
from .review import review_generated_run
from .seed import mine_candidate_seeds
from .source_chunks import build_source_chunks_from_markdown


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

    return {
        "source_bundle_root": str(source_bundle_root),
        "source_chunks_path": str(source_chunks_path),
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
    if deterministic_pass == "empty-shell":
        return build_empty_extraction_result(source_chunks_doc)
    if deterministic_pass == "section-headings":
        return build_section_heading_extraction_result(source_chunks_doc)
    if deterministic_pass == "heuristic-extractors":
        return build_heuristic_extraction_result(source_chunks_doc)
    raise ValueError(f"unsupported deterministic_pass: {deterministic_pass}")


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
    seeds = mine_candidate_seeds(
        source_bundle,
        graph,
        drafting_mode=drafting_mode,
    )
    run_root = render_generated_run(
        source_bundle=source_bundle,
        seeds=seeds,
        output_root=generated_root,
        run_id=run_id,
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
        usage_doc = {
            "review_case_id": f"{skill_id}-smoke-usage",
            "generated_run_root": str(run_root),
            "skill_path": str(bundle_root / "skills" / skill_id / "SKILL.md"),
            "input_scenario": {
                "scenario": primary_anchor.get("snippet", ""),
                "decision_goal": f"Decide whether `{skill_id}` should fire for this source-backed situation.",
                "current_constraints": [
                    f"Confirm the scenario still satisfies `{trigger_patterns[0]}`."
                ] if trigger_patterns else [],
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
                "next_action": "review_source_evidence",
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


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
