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
    report["summary"] = {
        "skill_candidates": skill_candidates,
        "workflow_script_candidates": workflow_script_candidates,
    }
    return report
