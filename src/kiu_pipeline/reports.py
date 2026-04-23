from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_round_report(
    run_root: str | Path,
    round_index: int,
    doc: dict[str, Any],
    *,
    candidate_id: str | None = None,
) -> None:
    reports_root = Path(run_root) / "reports" / "rounds"
    reports_root.mkdir(parents=True, exist_ok=True)
    prefix = f"{candidate_id}-" if candidate_id else ""
    path = reports_root / f"{prefix}round-{round_index:02d}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_scorecard(
    run_root: str | Path,
    doc: dict[str, Any],
) -> None:
    path = Path(run_root) / "reports" / "scorecard.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_final_decision(
    run_root: str | Path,
    doc: dict[str, Any],
) -> None:
    path = Path(run_root) / "reports" / "final-decision.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_production_quality(
    run_root: str | Path,
    doc: dict[str, Any],
) -> None:
    path = Path(run_root) / "reports" / "production-quality.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_three_layer_review(
    run_root: str | Path,
    doc: dict[str, Any],
) -> None:
    path = Path(run_root) / "reports" / "three-layer-review.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reconcile_production_quality_with_review(
    run_root: str | Path,
    review_doc: dict[str, Any],
) -> dict[str, Any]:
    path = Path(run_root) / "reports" / "production-quality.json"
    if not path.exists():
        return {}

    loaded = json.loads(path.read_text(encoding="utf-8"))
    production_quality = loaded if isinstance(loaded, dict) else {}
    release_gate = (
        review_doc.get("release_gate", {})
        if isinstance(review_doc.get("release_gate"), dict)
        else {}
    )
    artifact_release_ready = bool(
        production_quality.get(
            "artifact_release_ready",
            production_quality.get("release_ready"),
        )
    )
    behavior_release_ready = bool(release_gate.get("overall_ready"))
    release_gate_reasons = [
        reason
        for reason in release_gate.get("reasons", [])
        if isinstance(reason, str) and reason
    ]

    production_quality["artifact_release_ready"] = artifact_release_ready
    production_quality["behavior_release_ready"] = behavior_release_ready
    production_quality["release_ready"] = artifact_release_ready and behavior_release_ready
    production_quality["release_gate_reasons"] = release_gate_reasons
    write_production_quality(run_root, production_quality)
    return production_quality
