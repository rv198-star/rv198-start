from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any


SAFE_DIRECT_STATUSES = {"supported", "partially_supported"}
CURRENT_MARKERS = ("current", "today", "now", "latest", "当前", "最新", "目前")
CONFLICT_MARKERS = (" not ", "not required", "is not", "不是", "不需要", "不得")


def verify_claim_against_evidence(claim: str, evidence: list[dict[str, Any]], retrieved_at: str) -> dict[str, Any]:
    if not evidence:
        return _result(claim, "insufficient_evidence", evidence, "No evidence retrieved.")
    if any(item.get("retrieval_error") for item in evidence):
        return _result(claim, "retrieval_failed", evidence, "Retrieval failed before evidence could be checked.")

    evidence_text = " ".join(str(item.get("text") or item.get("snippet") or "") for item in evidence).strip()
    if _is_current_claim(claim) and any(not item.get("published_at") for item in evidence):
        return _result(claim, "undated", evidence, "Current claim evidence lacks a published date.")
    if _is_current_claim(claim) and _is_stale(evidence, retrieved_at):
        return _result(claim, "stale", evidence, "Current claim evidence is too old for direct application.")
    if _conflicts(claim, evidence_text):
        return _result(claim, "conflicting", evidence, "Evidence conflicts with the claim.")

    overlap = _token_overlap_ratio(claim, evidence_text)
    if overlap >= 0.8:
        return _result(claim, "supported", evidence, "Evidence supports the claim.")
    if overlap >= 0.45:
        return _result(claim, "partially_supported", evidence, "Evidence supports only part of the claim.")
    return _result(claim, "unsupported", evidence, "Evidence is related but does not support the claim.")


def direct_apply_allowed(verification: dict[str, Any]) -> bool:
    return verification.get("verification_status") in SAFE_DIRECT_STATUSES


def _result(claim: str, status: str, evidence: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    return {
        "claim": claim,
        "verification_status": status,
        "evidence": evidence,
        "reason": reason,
        "direct_apply_allowed": status in SAFE_DIRECT_STATUSES,
    }


def _is_current_claim(claim: str) -> bool:
    lowered = claim.lower()
    return any(marker in lowered for marker in CURRENT_MARKERS)


def _is_stale(evidence: list[dict[str, Any]], retrieved_at: str) -> bool:
    retrieved_date = _parse_date(retrieved_at)
    if retrieved_date is None:
        retrieved_date = date.today()
    for item in evidence:
        published = _parse_date(str(item.get("published_at") or ""))
        if published is None:
            continue
        if (retrieved_date - published).days > 730:
            return True
    return False


def _conflicts(claim: str, evidence_text: str) -> bool:
    claim_lower = f" {claim.lower()} "
    evidence_lower = f" {evidence_text.lower()} "
    if not any(marker in evidence_lower for marker in CONFLICT_MARKERS):
        return False
    if "require" in claim_lower and ("not required" in evidence_lower or "not require" in evidence_lower):
        return True
    claim_tokens = _tokens(claim_lower) - {"requires", "required", "require", "policy"}
    evidence_tokens = _tokens(evidence_lower) - {"not", "requires", "required", "require", "policy", "says"}
    return bool(claim_tokens & evidence_tokens)


def _token_overlap_ratio(claim: str, evidence_text: str) -> float:
    claim_tokens = _tokens(claim)
    evidence_tokens = _tokens(evidence_text)
    if not claim_tokens or not evidence_tokens:
        return 0.0
    return len(claim_tokens & evidence_tokens) / len(claim_tokens)


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(token) > 1}


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
