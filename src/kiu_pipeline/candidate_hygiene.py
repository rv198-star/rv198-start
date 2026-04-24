from __future__ import annotations

import re
from typing import Any


CHAPTER_TITLE_PATTERNS = (
    re.compile(r"^第[一二三四五六七八九十百千万0-9]+[章节篇部卷].*$"),
    re.compile(r"^(问题的提起|结论|绪论|前言|附录|目录)$"),
    re.compile(r"^[一二三四五六七八九十]+$"),
    re.compile(r"^[一二三四五六七八九十]+-.{1,32}$"),
    re.compile(r"^[IVXLCDM]+$", flags=re.IGNORECASE),
    re.compile(r"^\d+[.、-].{0,24}$"),
)


def classify_pseudo_skill_candidate(
    *,
    candidate_id: str,
    title: str,
    seed_content: dict[str, Any] | None,
) -> dict[str, Any]:
    seed_content = seed_content if isinstance(seed_content, dict) else {}
    candidate_texts = [str(candidate_id or "").strip(), str(title or "").strip()]
    matched = next((text for text in candidate_texts if _is_chapter_title(text)), "")
    if not matched:
        return {"is_pseudo_skill": False, "reason": ""}
    if seed_content.get("hygiene_override") == "allow_heading_like_judgment_skill":
        return {"is_pseudo_skill": False, "reason": ""}
    if _has_real_judgment_contract(seed_content):
        return {
            "is_pseudo_skill": True,
            "reason": "chapter_title_requires_explicit_hygiene_override",
            "matched_text": matched,
        }
    return {
        "is_pseudo_skill": True,
        "reason": "chapter_title_pseudo_skill",
        "matched_text": matched,
    }


def build_pseudo_skill_audit(summary: dict[str, Any]) -> dict[str, Any]:
    accepted = [item for item in summary.get("accepted", []) if isinstance(item, dict)]
    rejected = [item for item in summary.get("rejected", []) if isinstance(item, dict)]
    chapter_title_rejected = [
        _audit_item(item)
        for item in rejected
        if any(str(reason).startswith("chapter_title") for reason in item.get("reasons", []))
    ]
    summary_candidate_rejected = [
        _audit_item(item)
        for item in rejected
        if "summary_candidate_pseudo_skill" in set(item.get("reasons", []))
    ]
    workflow_candidate_routed = [
        _audit_item(item)
        for item in accepted
        if item.get("disposition") == "workflow_script_candidate"
    ]
    agentic_skill_accepted = [
        _audit_item(item)
        for item in accepted
        if item.get("disposition") == "skill_candidate"
    ]
    return {
        "schema_version": "kiu.pseudo-skill-audit/v0.1",
        "chapter_title_rejected": chapter_title_rejected,
        "summary_candidate_rejected": summary_candidate_rejected,
        "workflow_candidate_routed": workflow_candidate_routed,
        "agentic_skill_accepted": agentic_skill_accepted,
        "summary": {
            "chapter_title_rejected_count": len(chapter_title_rejected),
            "summary_candidate_rejected_count": len(summary_candidate_rejected),
            "workflow_candidate_routed_count": len(workflow_candidate_routed),
            "agentic_skill_accepted_count": len(agentic_skill_accepted),
        },
    }


def _is_chapter_title(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.match(normalized) for pattern in CHAPTER_TITLE_PATTERNS)


def _has_real_judgment_contract(seed_content: dict[str, Any]) -> bool:
    contract = seed_content.get("contract")
    if not isinstance(contract, dict):
        return False
    trigger = contract.get("trigger") if isinstance(contract.get("trigger"), dict) else {}
    boundary = contract.get("boundary") if isinstance(contract.get("boundary"), dict) else {}
    judgment_schema = (
        contract.get("judgment_schema")
        if isinstance(contract.get("judgment_schema"), dict)
        else {}
    )
    trigger_patterns = trigger.get("patterns", [])
    has_trigger = any(isinstance(item, str) and len(item.strip()) >= 12 for item in trigger_patterns)
    has_boundary = bool(boundary.get("do_not_fire_when") or boundary.get("anti_conditions"))
    has_judgment = bool(judgment_schema or seed_content.get("rationale"))
    return has_trigger and has_boundary and has_judgment


def _audit_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": item.get("candidate_id"),
        "title": item.get("title") or item.get("candidate_id"),
        "candidate_kind": item.get("candidate_kind"),
        "disposition": item.get("disposition"),
        "reasons": list(item.get("reasons", [])) if isinstance(item.get("reasons"), list) else [],
        "source_file": item.get("source_file"),
        "source_location": item.get("source_location"),
    }
