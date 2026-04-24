from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PUBLIC_SCHEMA = "blind-review-pack/v0.1"
RESPONSE_SCHEMA = "blind-review-response/v0.1"
KEY_SCHEMA = "kiu.blind-review-key/v0.1"
EVIDENCE_SCHEMA = "kiu.blind-preference-review/v0.1"
DIMENSIONS = ["usage", "depth", "transferability", "anti_misuse"]


def build_blind_review_pack(
    *,
    benchmark_report_path: str | Path,
    output_dir: str | Path,
    review_id: str,
    max_cases: int | None = None,
) -> dict[str, Any]:
    report_path = Path(benchmark_report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    generated_bundle = Path(
        str(report.get("generated_run", {}).get("generated_bundle_path", ""))
    )
    reference_root = Path(str(report.get("reference_pack", {}).get("path", "")))
    pairs = []
    key_pairs = []
    response_pairs = []
    case_limit = max_cases if max_cases is not None and max_cases > 0 else None

    for matched in report.get("same_scenario_usage", {}).get("matched_pairs", []):
        if not isinstance(matched, dict):
            continue
        kiu_skill_id = str(matched.get("kiu_skill_id", ""))
        reference_skill_id = str(matched.get("reference_skill_id", ""))
        kiu_card = _skill_card(generated_bundle / kiu_skill_id / "SKILL.md", redactions=[kiu_skill_id, reference_skill_id])
        reference_card = _skill_card(reference_root / reference_skill_id / "SKILL.md", redactions=[kiu_skill_id, reference_skill_id])
        for case in matched.get("cases", []):
            if not isinstance(case, dict):
                continue
            pair_index = len(pairs) + 1
            pair_id = f"{review_id}-p{pair_index:03d}"
            roles = _deterministic_roles(review_id=review_id, pair_id=pair_id)
            option_cards = {
                "kiu": kiu_card,
                "reference": reference_card,
            }
            prompt = _redact_text(str(case.get("prompt", "")), [kiu_skill_id, reference_skill_id])
            expected = _redact_text(
                str(case.get("expected_behavior", "")),
                [kiu_skill_id, reference_skill_id],
            )
            notes = _redact_text(str(case.get("notes", "")), [kiu_skill_id, reference_skill_id])
            pairs.append(
                {
                    "pair_id": pair_id,
                    "case": {
                        "case_type": str(case.get("type", "")),
                        "prompt": prompt,
                        "expected_behavior": expected,
                        "notes": notes,
                    },
                    "option_a": option_cards[roles["a"]],
                    "option_b": option_cards[roles["b"]],
                    "review_questions": [
                        "Which option is more useful for the prompt as an in-use judgment tool?",
                        "Which option has stronger boundary and anti-misuse discipline?",
                        "Which option preserves deeper transferable insight rather than generic advice?",
                    ],
                }
            )
            key_pairs.append(
                {
                    "pair_id": pair_id,
                    "source_case_id": str(case.get("case_id", "")),
                    "kiu_skill_id": kiu_skill_id,
                    "reference_skill_id": reference_skill_id,
                    "option_roles": roles,
                }
            )
            response_pairs.append(
                {
                    "pair_id": pair_id,
                    "preferred": "inconclusive",
                    "dimension_scores": {dimension: 0 for dimension in DIMENSIONS},
                    "notes": "",
                }
            )
            if case_limit is not None and len(pairs) >= case_limit:
                break
        if case_limit is not None and len(pairs) >= case_limit:
            break

    reviewer_pack = {
        "schema_version": PUBLIC_SCHEMA,
        "review_id": review_id,
        "benchmark_source": "same-source blind artifact preference",
        "labels_hidden": True,
        "instructions": [
            "Review Option A and Option B without trying to infer their origin.",
            "Choose a preference based on practical usefulness, depth, transferability, and anti-misuse discipline.",
            "Use tie when both options are materially equivalent and inconclusive when the case cannot be judged.",
        ],
        "dimension_scale": {
            "usage": "0-5 practical usefulness for the prompt",
            "depth": "0-5 non-generic mechanism depth",
            "transferability": "0-5 ability to transfer beyond the source story",
            "anti_misuse": "0-5 boundary and misuse resistance",
        },
        "pairs": pairs,
    }
    response_template = {
        "schema_version": RESPONSE_SCHEMA,
        "review_id": review_id,
        "pairs": response_pairs,
    }
    private_key = {
        "schema_version": KEY_SCHEMA,
        "review_id": review_id,
        "source_benchmark_report": report_path.as_posix(),
        "pairs": key_pairs,
    }
    _write_json(output / "reviewer-pack.json", reviewer_pack)
    _write_json(output / "reviewer-response-template.json", response_template)
    _write_json(output / "private-unblind-key.json", private_key)
    (output / "README.md").write_text(_readme(review_id=review_id), encoding="utf-8")
    return {
        "schema_version": "kiu.blind-review-pack-summary/v0.1",
        "review_id": review_id,
        "pair_count": len(pairs),
        "reviewer_pack_path": str(output / "reviewer-pack.json"),
        "response_template_path": str(output / "reviewer-response-template.json"),
        "private_key_path": str(output / "private-unblind-key.json"),
    }


def merge_blind_review_response(
    *,
    response_path: str | Path,
    key_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    response = json.loads(Path(response_path).read_text(encoding="utf-8"))
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    if response.get("review_id") != key.get("review_id"):
        raise ValueError("review_id_mismatch")
    roles_by_pair = {
        str(item.get("pair_id")): item.get("option_roles", {})
        for item in key.get("pairs", [])
        if isinstance(item, dict)
    }
    merged_pairs = []
    for item in response.get("pairs", []):
        if not isinstance(item, dict):
            continue
        pair_id = str(item.get("pair_id", ""))
        option_roles = roles_by_pair.get(pair_id)
        if not option_roles:
            raise ValueError(f"missing_unblind_key:{pair_id}")
        merged_pairs.append(
            {
                "pair_id": pair_id,
                "preferred": str(item.get("preferred", "inconclusive")),
                "option_roles": option_roles,
                "dimension_scores": item.get("dimension_scores", {}),
                "notes": str(item.get("notes", "")),
            }
        )
    evidence = {
        "schema_version": EVIDENCE_SCHEMA,
        "review_id": str(response.get("review_id", "")),
        "pairs": merged_pairs,
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, evidence)
    return {
        "schema_version": "kiu.blind-review-merge-summary/v0.1",
        "review_id": evidence["review_id"],
        "pair_count": len(merged_pairs),
        "output_path": str(out),
    }


def _deterministic_roles(*, review_id: str, pair_id: str) -> dict[str, str]:
    digest = hashlib.sha256(f"{review_id}:{pair_id}".encode("utf-8")).digest()
    if digest[0] % 2 == 0:
        return {"a": "kiu", "b": "reference"}
    return {"a": "reference", "b": "kiu"}


def _skill_card(path: Path, *, redactions: list[str]) -> dict[str, str]:
    try:
        markdown = path.read_text(encoding="utf-8")
    except OSError:
        markdown = ""
    cleaned = _redact_text(_clean_markdown(markdown), redactions)
    if not cleaned:
        cleaned = "No artifact excerpt available. Judge only the prompt fit."
    return {
        "artifact_excerpt": cleaned[:1800].rstrip(),
        "review_focus": "Assess whether this artifact would guide a model toward a useful, bounded answer for the case.",
    }


def _clean_markdown(markdown: str) -> str:
    text = re.sub(r"(?s)^---.*?---", "", markdown).strip()
    lines = []
    banned = (
        "skill_id:",
        "bundle_version:",
        "skill_revision:",
        "graph_hash:",
        "graph_version:",
        "anchor_refs:",
        "schema_version:",
    )
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.lower().startswith(item) for item in banned):
            continue
        lines.append(stripped)
        if len("\n".join(lines)) >= 2200:
            break
    return "\n".join(lines)


def _redact_text(text: str, redactions: list[str]) -> str:
    result = text
    for token in redactions:
        if token:
            result = result.replace(token, "[redacted-skill]")
    replacements = {
        "KiU": "System",
        "kiu": "system",
        "KIU": "SYSTEM",
        "cangjie": "baseline",
        "Cangjie": "Baseline",
        "reference": "baseline",
        "Reference": "Baseline",
    }
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _readme(*, review_id: str) -> str:
    return "\n".join(
        [
            f"# Blind Review Pack: {review_id}",
            "",
            "Files for external reviewers:",
            "",
            "- `reviewer-pack.json`: anonymous A/B cases.",
            "- `reviewer-response-template.json`: fill `preferred`, dimension scores, and notes.",
            "",
            "Private file for maintainers only:",
            "",
            "- `private-unblind-key.json`: maps A/B options to hidden origins. Do not send this to reviewers.",
            "",
            "After review, merge the response with the private key to create `blind-preference-review-v0.1` evidence.",
            "",
        ]
    )
