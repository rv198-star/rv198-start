from __future__ import annotations

import re
from typing import Any


CLAIM_LEDGER_SCHEMA = "kiu.claim-ledger/v0.1"

CURRENT_FACT_MARKERS = (
    "当前",
    "最新",
    "目前",
    "实时",
    "today",
    "current",
    "latest",
    "now",
)

MARKET_MARKERS = ("市场", "价格", "买入", "低估", "market", "price", "undervalued", "buy")
REGULATORY_MARKERS = ("监管", "政策", "合规", "regulation", "regulatory", "policy", "sec", "10-k")
MEDICAL_MARKERS = ("medical", "clinical", "treatment", "医疗", "治疗")
LEGAL_MARKERS = ("legal", "law", "court", "法律", "法院")


def build_claim_ledger(bundle_id: str, records: list[dict[str, Any]], mode: str = "no_web") -> dict[str, Any]:
    claims: list[dict[str, Any]] = []
    for index, record in enumerate(records, 1):
        text = _record_text(record)
        temporal = str(record.get("temporal_sensitivity") or "low").lower()
        if not _requires_live_verification(text, temporal):
            continue
        claims.append(
            {
                "claim_id": f"claim-{index:03d}",
                "bundle_id": bundle_id,
                "skill_id": record.get("skill_id"),
                "text": text,
                "claim_type": classify_claim_type(text),
                "origin": record.get("origin", "application_gate"),
                "temporal_sensitivity": temporal,
                "verification_required": True,
                "no_web_status": "blocked_current_fact_claim" if mode == "no_web" else "live_check_required",
                "allowed_without_web": False,
                "verification_status": "pending",
            }
        )
    return {"schema_version": CLAIM_LEDGER_SCHEMA, "bundle_id": bundle_id, "claims": claims}


def classify_claim_type(text: str) -> str:
    lowered = text.lower()
    if _contains_any(lowered, MARKET_MARKERS):
        return "current_market_fact"
    if _contains_any(lowered, REGULATORY_MARKERS):
        return "current_regulatory_fact"
    if _contains_any(lowered, MEDICAL_MARKERS):
        return "current_medical_fact"
    if _contains_any(lowered, LEGAL_MARKERS):
        return "current_legal_fact"
    return "current_world_fact"


def _record_text(record: dict[str, Any]) -> str:
    parts = [str(record.get(key) or "") for key in ("prompt", "claim", "reason")]
    return " ".join(part for part in parts if part).strip()


def _requires_live_verification(text: str, temporal_sensitivity: str) -> bool:
    if temporal_sensitivity != "high":
        return False
    lowered = text.lower()
    return _contains_any(lowered, CURRENT_FACT_MARKERS) or bool(re.search(r"\b20\d{2}\b", lowered))


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker.lower() in text for marker in markers)
