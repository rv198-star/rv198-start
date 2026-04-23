from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


VALID_STATUSES = {"todo", "in_progress", "blocked", "review", "done"}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def load_backlog(board_path: str | Path) -> dict[str, Any]:
    path = Path(board_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "kiu.backlog/v0.1":
        raise ValueError(f"Unsupported backlog schema: {payload.get('schema_version')!r}")
    tickets = payload.get("tickets")
    if not isinstance(tickets, list):
        raise ValueError("Backlog must contain a tickets list")
    for ticket in tickets:
        if not isinstance(ticket, dict):
            raise ValueError("Backlog tickets must be mappings")
        status = ticket.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"Unsupported backlog status: {status!r}")
    payload["tickets"] = tickets
    return payload


def build_backlog_view(
    board: dict[str, Any],
    *,
    version: str | None = None,
) -> dict[str, Any]:
    tickets = [
        dict(ticket)
        for ticket in board.get("tickets", [])
        if version is None or ticket.get("target_version") == version
    ]
    status_counts = dict(sorted(Counter(str(ticket.get("status", "")) for ticket in tickets).items()))
    target_counts = dict(
        sorted(Counter(str(ticket.get("target_version", "")) for ticket in tickets).items())
    )
    return _json_safe({
        "schema_version": board["schema_version"],
        "board_id": board.get("board_id"),
        "updated_at": board.get("updated_at"),
        "version": version,
        "summary": {
            "ticket_count": len(tickets),
            "status_counts": status_counts,
            "target_version_counts": target_counts,
        },
        "tickets": tickets,
    })


def format_backlog_text(view: dict[str, Any]) -> str:
    version = view.get("version") or "all"
    lines = [f"Backlog view: {version}"]
    summary = view.get("summary", {})
    lines.append(f"tickets: {summary.get('ticket_count', 0)}")
    status_counts = summary.get("status_counts", {})
    if status_counts:
        lines.append("status:")
        for status, count in status_counts.items():
            lines.append(f"- {status}: {count}")
    tickets = view.get("tickets", [])
    if tickets:
        lines.append("tickets:")
        for ticket in tickets:
            lines.append(
                f"- {ticket.get('id')}: {ticket.get('status')} [{ticket.get('priority')}] {ticket.get('title')}"
            )
    return "\n".join(lines) + "\n"
