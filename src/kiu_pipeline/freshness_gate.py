from __future__ import annotations

from typing import Any


STATUS_TO_VERDICT = {
    "supported": "apply_with_caveats",
    "partially_supported": "partial_apply",
    "unsupported": "refuse",
    "conflicting": "refuse",
    "stale": "ask_more_context",
    "undated": "ask_more_context",
    "insufficient_evidence": "ask_more_context",
    "retrieval_failed": "refuse",
}


def application_decision_from_verification(verification: dict[str, Any], *, high_stakes: bool = False) -> dict[str, Any]:
    status = str(verification.get("verification_status") or "insufficient_evidence")
    verdict = STATUS_TO_VERDICT.get(status, "ask_more_context")
    return {
        "verdict": verdict,
        "reason": _reason_for_status(status, high_stakes=high_stakes),
        "required_context": _required_context_for_status(status),
        "decision_effect": _decision_effect_for_status(status),
        "web_check_performed": status != "retrieval_failed",
        "world_context_isolated": True,
        "source_skill_unchanged": True,
        "verification_status": status,
        "caveats": _caveats_for_status(status, high_stakes=high_stakes),
    }


def _reason_for_status(status: str, *, high_stakes: bool) -> str:
    high_stakes_note = " High-stakes use still requires accountable human review." if high_stakes else ""
    reasons = {
        "supported": "Live evidence supports the bounded claim; apply only with visible citations.",
        "partially_supported": "Live evidence supports only part of the bounded claim; apply only the supported portion.",
        "unsupported": "Live evidence does not support the current-world claim; direct application is refused.",
        "conflicting": "Live evidence conflicts with the current-world claim; direct application is refused.",
        "stale": "Evidence is too old for this current-world claim; fresher context is required.",
        "undated": "Evidence lacks a usable date for this current-world claim; dated context is required.",
        "insufficient_evidence": "Evidence is insufficient for current-world application; more context is required.",
        "retrieval_failed": "Live retrieval failed; no verified current-world application is allowed.",
    }
    return reasons.get(status, reasons["insufficient_evidence"]) + high_stakes_note


def _required_context_for_status(status: str) -> list[str]:
    if status in {"supported", "partially_supported"}:
        return ["cite retrieved source", "state claim boundary"]
    if status in {"stale", "undated"}:
        return ["fresh dated source", "decision time window"]
    if status == "retrieval_failed":
        return ["working live retrieval or user-provided current source"]
    return ["supporting current evidence", "user decision context"]


def _decision_effect_for_status(status: str) -> list[str]:
    return {
        "supported": ["allow_cited_application"],
        "partially_supported": ["partial_apply", "ask_for_missing_context"],
        "unsupported": ["refuse_direct_application"],
        "conflicting": ["refuse_direct_application", "show_conflict"],
        "stale": ["ask_for_current_context"],
        "undated": ["ask_for_dated_context"],
        "insufficient_evidence": ["ask_for_supporting_evidence"],
        "retrieval_failed": ["refuse_direct_application"],
    }.get(status, ["ask_for_supporting_evidence"])


def _caveats_for_status(status: str, *, high_stakes: bool) -> list[str]:
    caveats = ["Live facts are external context, not source evidence for the book."]
    if high_stakes:
        caveats.append("Do not treat this as legal, medical, financial, or safety advice.")
    if status != "supported":
        caveats.append("Do not convert this verification result into a direct current-world recommendation.")
    return caveats
