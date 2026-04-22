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
