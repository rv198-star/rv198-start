from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .draft import build_evaluation_summary_markdown, build_revision_summary_markdown
from .load import parse_sections
from kiu_validator.core import validate_bundle


def validate_generated_bundle(bundle_root: str | Path) -> dict[str, Any]:
    bundle_root = Path(bundle_root)
    report = validate_bundle(bundle_root)
    errors = list(report["errors"])
    manifest = report.get("manifest") or {}

    skill_candidates = 0
    workflow_script_candidates = 0
    workflow_gateway_boundary_preserved = True
    workflow_candidate_ids = _workflow_candidate_ids(bundle_root)

    for entry in manifest.get("skills", []):
        skill_id = entry.get("skill_id", "<missing-skill-id>")
        candidate_path = bundle_root / entry.get("path", "") / "candidate.yaml"
        if not candidate_path.exists():
            errors.append(f"{skill_id}: missing required file candidate.yaml")
            continue

        candidate_doc = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
        skill_candidates += 1

        disposition = candidate_doc.get("disposition")
        if disposition == "workflow_script_candidate":
            workflow_script_candidates += 1
            errors.append(
                f"{skill_id}: workflow_script_candidate must not be emitted inside bundle/skills/"
            )

        if candidate_doc.get("candidate_id") != skill_id:
            errors.append(f"{skill_id}: candidate.yaml candidate_id mismatch")
        if candidate_doc.get("source_graph_hash") != manifest.get("graph", {}).get("graph_hash"):
            errors.append(f"{skill_id}: candidate.yaml source_graph_hash mismatch")
        if "drafting_mode" not in candidate_doc:
            errors.append(f"{skill_id}: candidate.yaml missing drafting_mode")
        if "recommended_execution_mode" not in candidate_doc:
            errors.append(f"{skill_id}: candidate.yaml missing recommended_execution_mode")
        if "loop_mode" not in candidate_doc:
            errors.append(f"{skill_id}: candidate.yaml missing loop_mode")
        if "terminal_state" not in candidate_doc:
            errors.append(f"{skill_id}: candidate.yaml missing terminal_state")

        skill_markdown = (candidate_path.parent / "SKILL.md").read_text(encoding="utf-8")
        gateway_errors = _validate_workflow_gateway_boundary(
            skill_id=skill_id,
            candidate_doc=candidate_doc,
            skill_markdown=skill_markdown,
            workflow_candidate_ids=workflow_candidate_ids,
        )
        if gateway_errors:
            workflow_gateway_boundary_preserved = False
            errors.extend(gateway_errors)
        sections = parse_sections(skill_markdown)
        eval_doc = yaml.safe_load(
            (candidate_path.parent / "eval" / "summary.yaml").read_text(encoding="utf-8")
        ) or {}
        revisions_doc = yaml.safe_load(
            (candidate_path.parent / "iterations" / "revisions.yaml").read_text(encoding="utf-8")
        ) or {}
        scenario_families = {}
        scenario_path = candidate_path.parent / "usage" / "scenarios.yaml"
        if scenario_path.exists():
            scenario_families = yaml.safe_load(
                scenario_path.read_text(encoding="utf-8")
            ) or {}

        expected_eval_summary = build_evaluation_summary_markdown(
            eval_doc,
            scenario_families=scenario_families,
        ).strip()
        if sections.get("Evaluation Summary", "").strip() != expected_eval_summary:
            errors.append(f"{skill_id}: Evaluation Summary drift vs eval/summary.yaml")

        expected_revision_summary = build_revision_summary_markdown(revisions_doc).strip()
        if sections.get("Revision Summary", "").strip() != expected_revision_summary:
            errors.append(f"{skill_id}: Revision Summary drift vs iterations/revisions.yaml")

    report["errors"] = errors
    report["workflow_gateway_boundary_preserved"] = workflow_gateway_boundary_preserved
    report["summary"] = {
        "skill_candidates": skill_candidates,
        "workflow_script_candidates": workflow_script_candidates,
        "workflow_gateway_boundary_preserved": workflow_gateway_boundary_preserved,
    }
    return report


def scan_live_fact_pollution(skill_markdown: str, fact_pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for fact in fact_pack.get("facts") or []:
        for evidence in fact.get("evidence") or []:
            source_url = str(evidence.get("source_url") or "").strip()
            if source_url and source_url in skill_markdown:
                errors.append(f"live fact URL must not appear in source SKILL.md evidence: {source_url}")
    return errors


def _workflow_candidate_ids(bundle_root: Path) -> list[str]:
    workflow_root = bundle_root.parent / "workflow_candidates"
    if not workflow_root.exists():
        return []
    return sorted(path.name for path in workflow_root.iterdir() if path.is_dir())


def _validate_workflow_gateway_boundary(
    *,
    skill_id: str,
    candidate_doc: dict[str, Any],
    skill_markdown: str,
    workflow_candidate_ids: list[str],
) -> list[str]:
    if skill_id != "workflow-gateway" and candidate_doc.get("candidate_kind") != "workflow_gateway":
        return []

    errors: list[str] = []
    gateway_doc = candidate_doc.get("workflow_gateway", {})
    if not isinstance(gateway_doc, dict):
        gateway_doc = {}
    routes_to = sorted(
        str(item)
        for item in gateway_doc.get("routes_to", [])
        if isinstance(item, str) and item
    )
    if workflow_candidate_ids and not routes_to:
        errors.append("workflow-gateway: missing workflow_gateway.routes_to for existing workflow_candidates")
    if workflow_candidate_ids and set(routes_to) != set(workflow_candidate_ids):
        errors.append("workflow-gateway: workflow_gateway.routes_to must match workflow_candidates directories")
    if workflow_candidate_ids and "workflow_candidates" not in skill_markdown:
        errors.append("workflow-gateway: SKILL.md must route to workflow_candidates instead of hiding workflow steps")

    inline_markers = (
        "## Rollback",
        "## Reversibility",
        "- [ ] Confirm rollback steps",
        "- [ ] Identify any irreversible data writes",
        "- [ ] Summarize the proposed change and the exact affected surface",
    )
    if any(marker in skill_markdown for marker in inline_markers):
        errors.append("workflow-gateway: SKILL.md appears to inline deterministic workflow checklist steps")
    return errors
