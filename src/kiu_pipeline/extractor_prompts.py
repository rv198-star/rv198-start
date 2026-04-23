from __future__ import annotations

from typing import Any


EXTRACTOR_PROMPT_REGISTRY_VERSION = "kiu.extractor-prompts/v0.1"

_DETERMINISTIC_STAGE_CATALOG: dict[str, list[dict[str, Any]]] = {
    "empty-shell": [
        {
            "extractor_kind": "empty-shell",
            "pass_kind": "deterministic",
            "prompt_key": "empty-shell-bootstrap",
            "description": "Emit a schema-valid empty extraction shell with no extracted signals.",
        }
    ],
    "section-headings": [
        {
            "extractor_kind": "section-headings",
            "pass_kind": "deterministic",
            "prompt_key": "section-heading-structure",
            "description": "Project markdown headings into source_section nodes and next_section edges.",
        }
    ],
    "heuristic-extractors": [
        {
            "extractor_kind": "framework",
            "pass_kind": "deterministic",
            "prompt_key": "heuristic-framework",
            "description": "Lift top-level headings into framework signals.",
        },
        {
            "extractor_kind": "principle",
            "pass_kind": "deterministic",
            "prompt_key": "heuristic-principle",
            "description": "Lift section headings into principle signals.",
        },
        {
            "extractor_kind": "evidence",
            "pass_kind": "deterministic",
            "prompt_key": "heuristic-evidence",
            "description": "Materialize chunk-level evidence nodes and explicit support edges.",
        },
        {
            "extractor_kind": "case",
            "pass_kind": "deterministic",
            "prompt_key": "heuristic-case",
            "description": "Flag example-heavy chunks as case signals.",
        },
        {
            "extractor_kind": "counter-example",
            "pass_kind": "deterministic",
            "prompt_key": "heuristic-counter-example",
            "description": "Flag negative/boundary chunks as ambiguous counter-example signals.",
        },
        {
            "extractor_kind": "term",
            "pass_kind": "deterministic",
            "prompt_key": "heuristic-term",
            "description": "Extract capitalized or emphasized terms as reusable term signals.",
        },
    ],
}

_LLM_STAGE_CATALOG = {
    "extractor_kind": "llm-patch",
    "pass_kind": "llm_patch",
    "prompt_key": "llm-extraction-patch",
    "description": "Apply an audited LLM patch on top of deterministic extraction output.",
}


def get_deterministic_stage_catalog(deterministic_pass: str) -> list[dict[str, Any]]:
    return [dict(stage) for stage in _DETERMINISTIC_STAGE_CATALOG.get(deterministic_pass, [])]


def get_llm_patch_stage_metadata() -> dict[str, Any]:
    return dict(_LLM_STAGE_CATALOG)
