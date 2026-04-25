#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import yaml

from kiu_pipeline.world_alignment import build_world_alignment_artifacts, build_world_alignment_gate_evidence

SAMPLE_BUNDLES = {
    "poor_charlie_principles": {
        "circle-of-competence": "Circle Of Competence",
        "invert-the-problem": "Invert The Problem",
        "bias-self-audit": "Bias Self Audit",
        "value-assessment-source-note": "Value Assessment Source Note",
        "role-boundary-before-action": "Role Boundary Before Action",
    },
    "effective_requirements_methods": {
        "business-first-subsystem-decomposition": "Business First Subsystem Decomposition",
        "stakeholder-conflict-clarification": "Stakeholder Conflict Clarification",
    },
    "financial_statement_current_context": {
        "financial-statement-current-investment-check": "Financial Statement Current Investment Check",
        "challenge-price-with-value": "Challenge Price With Value",
    },
    "no_web_refuse_fixture": {
        "current-investment-advice": "Current Investment Advice",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate v0.7.1 world-alignment gate evidence.")
    parser.add_argument("--workdir", default="/tmp/kiu-v071-world-alignment-gate", help="Directory for generated sample bundles.")
    parser.add_argument("--output", required=True, help="Markdown report output path.")
    parser.add_argument("--json-output", help="Optional JSON evidence output path.")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    bundles = []
    for sample_id, skills in SAMPLE_BUNDLES.items():
        bundle = _write_sample_bundle(workdir / sample_id, skills)
        build_world_alignment_artifacts(bundle, no_web_mode=True)
        bundles.append(bundle)

    evidence = build_world_alignment_gate_evidence(bundles)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_markdown(evidence), encoding="utf-8")
    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": evidence["passed"], "output": str(output)}, ensure_ascii=False))
    return 0 if evidence["passed"] else 1


def _write_sample_bundle(root: Path, skills: dict[str, str]) -> Path:
    bundle = root / "bundle"
    (bundle / "skills").mkdir(parents=True, exist_ok=True)
    manifest_skills = []
    for skill_id, title in skills.items():
        skill_dir = bundle / "skills" / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_text = (
            f"# {title}\n\n"
            f"## Identity\n```yaml\nskill_id: {skill_id}\ntitle: {title}\n```\n\n"
            "## Rationale\nSource-faithful rationale only.\n\n"
            "## Usage Summary\nUse the source-derived skill within its native boundary.\n"
        )
        (skill_dir / "SKILL.md").write_text(skill_text, encoding="utf-8")
        manifest_skills.append({"skill_id": skill_id, "path": f"skills/{skill_id}"})
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump({"bundle_id": root.name, "skills": manifest_skills}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return bundle


def _render_markdown(evidence: dict) -> str:
    lines = [
        "# v0.7.1 World Alignment Gate Evidence",
        "",
        "This report is internal release-gate evidence. It does not claim external blind preference, real-user validation, live-web factual correctness, domain-expert validation, or multi-world modeling.",
        "",
        f"Overall gate: {'PASS' if evidence['passed'] else 'FAIL'}",
        "",
        "## Charter Gate Scorecard",
        "",
        "| Check | Actual | Threshold | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for name, check in evidence["checks"].items():
        lines.append(f"| `{name}` | `{check['actual']}` | `{check['threshold']}` | {'PASS' if check['passed'] else 'FAIL'} |")
    lines.extend([
        "",
        "## Verdict Distribution",
        "",
        "| Verdict | Count |",
        "| --- | ---: |",
    ])
    for verdict, count in sorted(evidence["verdict_counts"].items()):
        lines.append(f"| `{verdict}` | {count} |")
    lines.extend([
        "",
        "## Mechanism Run Counts",
        "",
        "| Mechanism | Count |",
        "| --- | ---: |",
    ])
    mechanism_counts = evidence["mechanism_counts"]
    for name, count in mechanism_counts.items():
        if isinstance(count, dict):
            rendered = ", ".join(f"{key}: {value}" for key, value in sorted(count.items()))
            lines.append(f"| `{name}` | `{rendered}` |")
        else:
            lines.append(f"| `{name}` | {count} |")
    lines.extend([
        "",
        "## Sample Results",
        "",
        "| Bundle | Gates | Verdicts | Score | Depth | Pollution | Status |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- |",
    ])
    for sample in evidence["sample_results"]:
        lines.append(
            f"| `{sample['bundle_root']}` | {sample['gate_count']} | `{sample['verdict_counts']}` | {sample['world_alignment_score_100']} | {sample['world_context_depth_score']} | {sample['source_pollution_errors']} | {'PASS' if sample['passed'] else 'FAIL'} |"
        )
    lines.extend([
        "",
        "## v0.6.x Prerequisite Reference",
        "",
        "v0.7.1 inherits the sealed v0.6.x cold-start baseline and does not reopen KIU-672 through KIU-675. The relevant evidence remains the v0.6.4-v0.6.8 release reports and the v0.7.0 cangjie baseline scope note.",
        "",
        "## Condition-Dependent Validation",
        "",
        "External blind review, real user validation, live-web factual validation, and domain-expert validation are tracked in `docs/condition-dependent-validation-backlog.md`. They are future validation sources and are not short-term v0.7.1 blockers.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
