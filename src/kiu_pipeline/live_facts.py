from __future__ import annotations

import urllib.request
from typing import Any

from kiu_pipeline.fact_verification import verify_claim_against_evidence


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


def retrieve_live_facts_for_claims(
    claims: list[dict[str, Any]],
    source_urls: list[str],
    retrieved_at: str,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    fetch = fetcher or _fetch_url
    facts: list[dict[str, Any]] = []
    for index, claim in enumerate(claims):
        url = source_urls[min(index, len(source_urls) - 1)] if source_urls else ""
        try:
            evidence = dict(fetch(url))
            evidence.setdefault("source_url", url)
            evidence.setdefault("source_title", url or "live source")
            evidence.setdefault("retrieved_at", retrieved_at)
            verification = verify_claim_against_evidence(str(claim.get("text") or ""), [evidence], retrieved_at=retrieved_at)
            relation = _relation_for_status(str(verification["verification_status"]))
            evidence.setdefault("relation_to_claim", relation)
            facts.append(
                {
                    "claim_id": claim.get("claim_id"),
                    "skill_id": claim.get("skill_id"),
                    "claim": claim.get("text"),
                    "verification_status": verification["verification_status"],
                    "evidence": [evidence],
                    "freshness_status": _freshness_for_status(str(verification["verification_status"])),
                    "confidence": "medium" if verification["verification_status"] in {"supported", "partially_supported"} else "low",
                    "decision_effect": _decision_effect_for_status(str(verification["verification_status"])),
                }
            )
        except Exception as exc:  # Network failures become evidence states, not fabricated facts.
            facts.append(
                {
                    "claim_id": claim.get("claim_id"),
                    "skill_id": claim.get("skill_id"),
                    "claim": claim.get("text"),
                    "verification_status": "retrieval_failed",
                    "evidence": [
                        {
                            "source_url": url,
                            "source_title": url or "live source",
                            "retrieved_at": retrieved_at,
                            "relation_to_claim": "retrieval_failed",
                            "retrieval_error": str(exc),
                        }
                    ],
                    "freshness_status": "unknown",
                    "confidence": "low",
                    "decision_effect": ["refuse_direct_application"],
                }
            )
    return build_external_fact_pack(claims=claims, facts=facts, retrieved_at=retrieved_at)


def _fetch_url(url: str) -> dict[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "KiU-live-fact-verification/0.7.2"})
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read(120_000)
    text = raw.decode("utf-8", errors="replace")
    title = _extract_title(text) or url
    return {"source_url": url, "source_title": title, "text": text[:20_000]}


def _extract_title(html: str) -> str:
    lower = html.lower()
    start = lower.find("<title")
    if start == -1:
        return ""
    start = lower.find(">", start)
    end = lower.find("</title>", start)
    if start == -1 or end == -1:
        return ""
    return " ".join(html[start + 1 : end].split())


def _relation_for_status(status: str) -> str:
    return {
        "supported": "supports",
        "partially_supported": "partially_supports",
        "unsupported": "related_but_not_supporting",
        "conflicting": "conflicts",
        "stale": "stale_support",
        "undated": "undated_support",
        "insufficient_evidence": "insufficient_evidence",
        "retrieval_failed": "retrieval_failed",
    }.get(status, "insufficient_evidence")


def _freshness_for_status(status: str) -> str:
    if status == "stale":
        return "stale"
    if status in {"undated", "retrieval_failed", "insufficient_evidence"}:
        return "unknown"
    return "current"


def _decision_effect_for_status(status: str) -> list[str]:
    if status == "supported":
        return ["allow_cited_application"]
    if status == "partially_supported":
        return ["partial_apply", "ask_for_missing_context"]
    if status in {"stale", "undated", "insufficient_evidence"}:
        return ["ask_for_current_context"]
    return ["refuse_direct_application"]
