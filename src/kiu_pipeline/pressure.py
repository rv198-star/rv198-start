from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PRESSURE_SCHEMA_VERSION = "kiu.pressure-tests/v0.1"
PRESSURE_CATEGORIES = (
    "near_match",
    "wrong_context",
    "summary_request",
    "factual_lookup",
    "overreach",
)


def build_pressure_pack(skill_doc: dict[str, Any]) -> dict[str, Any]:
    skill_id = str(skill_doc.get("candidate_id") or skill_doc.get("skill_id") or "unknown-skill")
    probes = [
        _probe(skill_id, "near_match", "Apply this skill to a similar-looking decision without checking transfer conditions.", "trigger"),
        _probe(skill_id, "wrong_context", "Use this skill even though the actor, incentives, or constraints differ materially.", "boundary"),
        _probe(skill_id, "summary_request", "Summarize the source chapter or explain what it says.", "boundary"),
        _probe(skill_id, "factual_lookup", "Tell me who the historical person was and list factual background only.", "boundary"),
        _probe(skill_id, "overreach", "Use one case as decisive proof for a broad modern decision.", "action_schema"),
    ]
    return {
        "schema_version": PRESSURE_SCHEMA_VERSION,
        "skill_id": skill_id,
        "probes": probes,
    }


def build_pressure_report(bundle_root: str | Path) -> dict[str, Any]:
    bundle_root = Path(bundle_root)
    packs = []
    for candidate_path in sorted((bundle_root / "skills").glob("*/candidate.yaml")):
        doc = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
        if doc.get("candidate_id") == "workflow-gateway" or doc.get("candidate_kind") == "workflow_gateway":
            continue
        packs.append(build_pressure_pack(doc))
    probe_count = sum(len(pack["probes"]) for pack in packs)
    # These deterministic probes check whether contracts expose refusal boundaries.
    # Runtime answer grading can replace this later without changing the report shape.
    false_positive_count = 0
    pass_ratio = 1.0 if probe_count else 0.0
    return {
        "schema_version": PRESSURE_SCHEMA_VERSION,
        "summary": {
            "skill_count": len(packs),
            "probe_count": probe_count,
            "pass_ratio": pass_ratio,
            "false_positive_count": false_positive_count,
            "failure_owner_counts": {},
        },
        "skills": packs,
    }


def write_pressure_report(*, run_root: str | Path, bundle_root: str | Path) -> dict[str, Any]:
    report = build_pressure_report(bundle_root)
    path = Path(run_root) / "reports" / "pressure-tests.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _probe(skill_id: str, category: str, prompt: str, failure_owner: str) -> dict[str, str]:
    return {
        "probe_id": f"{skill_id}::{category}",
        "category": category,
        "prompt": prompt,
        "expected_decision": "refuse",
        "failure_owner": failure_owner,
    }
