from __future__ import annotations

from typing import Any


EXTERNAL_FACT_PACK_SCHEMA = "kiu.external-fact-pack/v0.1"
REQUIRED_EVIDENCE_FIELDS = ("source_url", "source_title", "retrieved_at", "relation_to_claim")


def build_external_fact_pack(
    claims: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    retrieved_at: str,
    retrieval_mode: str = "live_web",
) -> dict[str, Any]:
    return {
        "schema_version": EXTERNAL_FACT_PACK_SCHEMA,
        "retrieved_at": retrieved_at,
        "retrieval_mode": retrieval_mode,
        "claims": claims,
        "facts": facts,
    }


def validate_external_fact_pack(pack: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if pack.get("schema_version") != EXTERNAL_FACT_PACK_SCHEMA:
        errors.append("schema_version must be kiu.external-fact-pack/v0.1")
    if not pack.get("retrieved_at"):
        errors.append("retrieved_at is required")
    for fact_index, fact in enumerate(pack.get("facts") or [], 1):
        if not fact.get("claim_id"):
            errors.append(f"facts[{fact_index}].claim_id is required")
        if not fact.get("verification_status"):
            errors.append(f"facts[{fact_index}].verification_status is required")
        evidence_items = fact.get("evidence") or []
        if not evidence_items:
            errors.append(f"facts[{fact_index}].evidence is required")
        for evidence_index, evidence in enumerate(evidence_items, 1):
            for field in REQUIRED_EVIDENCE_FIELDS:
                if not evidence.get(field):
                    errors.append(f"facts[{fact_index}].evidence[{evidence_index}].{field} is required")
    return errors
