from __future__ import annotations

import re
from typing import Any

from .readiness import ReadinessFinding, ReadinessSeverity, aggregate_readiness


MIN_COVERAGE_UNIT_SIZE = 5


def build_coverage_report(
    *,
    graph_doc: dict[str, Any],
    published_skill_ids: list[str],
    workflow_candidate_ids: list[str],
    gateway_routes: list[str],
    artifact_texts: dict[str, str] | None = None,
    narrow_output_justification: str = "",
) -> dict[str, Any]:
    units = _coverage_units(graph_doc)
    covered = []
    uncovered = []
    routed_workflows = set(workflow_candidate_ids).intersection(set(gateway_routes))
    artifacts = list(published_skill_ids) + sorted(routed_workflows)
    artifact_texts = artifact_texts or {}
    for unit in units:
        matched = _matching_artifact(unit, artifacts, artifact_texts=artifact_texts)
        if matched:
            covered.append({**unit, "covered_by": matched})
        else:
            uncovered.append(unit)

    findings: list[ReadinessFinding] = []
    if uncovered and not narrow_output_justification.strip():
        findings.append(
            ReadinessFinding(
                model="coverage_model",
                severity=ReadinessSeverity.WARN,
                reason="narrow_output_without_justification",
                evidence={
                    "coverage_unit_count": len(units),
                    "covered_unit_count": len(covered),
                    "uncovered_unit_count": len(uncovered),
                },
                recommended_action="add model-backed coverage, workflow gateway routing, or narrow_output_justification",
            )
        )

    score = 100.0 if not units else 100.0 * (len(covered) / len(units))
    if narrow_output_justification.strip() and uncovered:
        score = max(score, 90.0)
        uncovered = []

    return {
        "schema_version": "kiu.coverage-readiness/v0.1",
        "coverage_units": units,
        "covered_units": covered,
        "uncovered_units": uncovered,
        "coverage_unit_count": len(units),
        "covered_unit_count": len(covered),
        "uncovered_unit_count": len(uncovered),
        "published_skill_count": len(published_skill_ids),
        "workflow_candidate_count": len(workflow_candidate_ids),
        "gateway_route_count": len(gateway_routes),
        "narrow_output_justification": narrow_output_justification,
        "readiness": aggregate_readiness(
            model="coverage_model",
            score_100=score,
            findings=findings,
        ),
    }


def _coverage_units(graph_doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw = graph_doc.get("communities", [])
    if isinstance(raw, dict):
        raw = list(raw.values())
    units = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        node_ids = item.get("node_ids", []) or []
        node_count = len(node_ids) if isinstance(node_ids, list) else int(item.get("node_count", 0) or 0)
        if node_count < MIN_COVERAGE_UNIT_SIZE:
            continue
        label = str(item.get("label") or item.get("id") or "coverage-unit")
        units.append(
            {
                "unit_id": str(item.get("id") or _slug(label)),
                "label": label,
                "node_count": node_count,
                "keywords": _keywords(label),
            }
        )
    return sorted(units, key=lambda unit: (-int(unit["node_count"]), str(unit["unit_id"])))


def _matching_artifact(unit: dict[str, Any], artifacts: list[str], *, artifact_texts: dict[str, str]) -> str | None:
    keywords = set(unit.get("keywords", []))
    for artifact in artifacts:
        artifact_keywords = set(_keywords(f"{artifact} {artifact_texts.get(artifact, '')}"))
        if keywords.intersection(artifact_keywords):
            return artifact
    return None


def _keywords(text: str) -> list[str]:
    lowered = str(text or "").lower()
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", lowered)
    stop = {"community", "cluster", "source", "skill", "candidate", "the", "and", "for"}
    return [token for token in tokens if token not in stop]


def _slug(text: str) -> str:
    return "-".join(_keywords(text)) or "coverage-unit"
