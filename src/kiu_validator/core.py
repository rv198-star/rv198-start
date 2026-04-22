import hashlib
import json
import re
from glob import glob
from pathlib import Path
from typing import Any

import yaml

from kiu_pipeline.profile_resolver import resolve_profile


REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "anchors.yaml",
    "eval/summary.yaml",
    "iterations/revisions.yaml",
)
REQUIRED_SKILL_SECTIONS = (
    "Identity",
    "Contract",
    "Rationale",
    "Evidence Summary",
    "Relations",
    "Usage Summary",
    "Evaluation Summary",
    "Revision Summary",
)
REQUIRED_RELATIONS = (
    "depends_on",
    "delegates_to",
    "constrained_by",
    "complements",
    "contradicts",
)
ALLOWED_STATUSES = {"candidate", "under_evaluation", "published", "archived"}
ANCHOR_REQUIRED_STATUSES = {"under_evaluation", "published"}
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VALIDATION_PROFILE = {
    "trigger_registry": "shared_profiles/default/triggers.yaml",
    "min_eval_cases_for_published": {
        "real_decisions": 5,
        "synthetic_adversarial": 5,
        "out_of_distribution": 2,
    },
    "content_density": {
        "rationale": {
            "warning_min_chars": 180,
            "min_anchor_refs": 1,
        },
        "evidence_summary": {
            "min_anchor_refs": 1,
        },
    }
}


def validate_bundle(bundle_path: str | Path) -> dict[str, Any]:
    root = Path(bundle_path)
    errors: list[str] = []
    warnings: list[str] = []

    manifest = _load_yaml(root / "manifest.yaml", errors, "manifest")
    profile = _resolve_validation_profile(root, warnings)
    trigger_registry = _load_trigger_registry(root, profile, errors, warnings)
    graph_doc = {}
    graph_report = {"node_count": 0, "edge_count": 0, "community_count": 0}
    node_ids: set[str] = set()
    edge_ids: set[str] = set()
    community_ids: set[str] = set()
    computed_graph_hash = None

    if manifest:
        graph_meta = manifest.get("graph", {})
        graph_path_value = graph_meta.get("path")
        if not graph_path_value:
            errors.append("manifest: missing graph.path")
        else:
            graph_path = root / graph_path_value
            graph_doc = _load_json(graph_path, errors, "graph")
            if graph_doc:
                computed_graph_hash = _canonical_graph_hash(graph_doc)
                graph_hashes = {
                    "manifest.graph.graph_hash": graph_meta.get("graph_hash"),
                    "graph.graph_hash": graph_doc.get("graph_hash"),
                }
                for label, value in graph_hashes.items():
                    if not value:
                        errors.append(f"{label}: missing graph_hash")
                    elif value != computed_graph_hash:
                        errors.append(
                            f"{label}: graph_hash mismatch, expected {computed_graph_hash}"
                        )

                node_ids = {node["id"] for node in graph_doc.get("nodes", [])}
                edge_ids = {edge["id"] for edge in graph_doc.get("edges", [])}
                community_ids = {
                    community["id"] for community in graph_doc.get("communities", [])
                }
                graph_report = {
                    "node_count": len(node_ids),
                    "edge_count": len(edge_ids),
                    "community_count": len(community_ids),
                }

    skills: list[dict[str, Any]] = []
    skill_entries = manifest.get("skills", []) if manifest else []
    known_skill_ids = {
        entry["skill_id"] for entry in skill_entries if isinstance(entry.get("skill_id"), str)
    }
    for entry in skill_entries:
        skills.append(
            _validate_skill(
                root=root,
                manifest=manifest,
                skill_entry=entry,
                errors=errors,
                warnings=warnings,
                node_ids=node_ids,
                edge_ids=edge_ids,
                community_ids=community_ids,
                computed_graph_hash=computed_graph_hash,
                known_skill_ids=known_skill_ids,
                trigger_registry=trigger_registry,
                profile=profile,
            )
        )
    _detect_relation_cycles(skills, warnings)

    traces_root = root / "traces"
    evaluation_root = root / "evaluation"
    evaluation_breakdown = {
        "real_decisions": len(list((evaluation_root / "real_decisions").rglob("*.yaml"))),
        "synthetic_adversarial": len(
            list((evaluation_root / "synthetic_adversarial").rglob("*.yaml"))
        ),
        "out_of_distribution": len(
            list((evaluation_root / "out_of_distribution").rglob("*.yaml"))
        ),
    }
    shared_assets = {
        "trace_count": len(list(traces_root.rglob("*.yaml"))),
        "evaluation_count": len(list(evaluation_root.rglob("*.yaml"))),
        "evaluation_breakdown": evaluation_breakdown,
    }

    return {
        "bundle_path": str(root),
        "manifest": manifest,
        "graph": graph_report,
        "shared_assets": shared_assets,
        "skills": skills,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_skill(
    *,
    root: Path,
    manifest: dict[str, Any],
    skill_entry: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    node_ids: set[str],
    edge_ids: set[str],
    community_ids: set[str],
    computed_graph_hash: str | None,
    known_skill_ids: set[str],
    trigger_registry: dict[str, dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    skill_id = skill_entry.get("skill_id", "<missing-skill-id>")
    skill_dir = root / skill_entry.get("path", "")
    skill_errors: list[str] = []
    skill_warnings: list[str] = []

    for relative_path in REQUIRED_SKILL_FILES:
        if not (skill_dir / relative_path).exists():
            skill_errors.append(f"{skill_id}: missing required file {relative_path}")

    skill_doc_path = skill_dir / "SKILL.md"
    skill_doc = skill_doc_path.read_text(encoding="utf-8") if skill_doc_path.exists() else ""
    sections = _parse_sections(skill_doc)
    for section_name in REQUIRED_SKILL_SECTIONS:
        if section_name not in sections:
            skill_errors.append(f"{skill_id}: missing required section {section_name}")

    identity = _extract_yaml_section(
        sections.get("Identity", ""),
        skill_errors,
        f"{skill_id}: Identity",
    )
    contract = _extract_yaml_section(
        sections.get("Contract", ""),
        skill_errors,
        f"{skill_id}: Contract",
    )
    relations = _extract_yaml_section(
        sections.get("Relations", ""),
        skill_errors,
        f"{skill_id}: Relations",
    )

    status = identity.get("status")
    if status not in ALLOWED_STATUSES:
        skill_errors.append(f"{skill_id}: invalid status {status!r}")

    if identity.get("skill_id") != skill_id:
        skill_errors.append(
            f"{skill_id}: Identity.skill_id {identity.get('skill_id')!r} does not match manifest"
        )
    if identity.get("bundle_version") != manifest.get("bundle_version"):
        skill_errors.append(
            f"{skill_id}: bundle_version mismatch between SKILL.md and manifest"
        )
    if identity.get("skill_revision") != skill_entry.get("skill_revision"):
        skill_errors.append(
            f"{skill_id}: skill_revision mismatch between SKILL.md and manifest"
        )
    if status != skill_entry.get("status"):
        skill_errors.append(f"{skill_id}: status mismatch between SKILL.md and manifest")

    _validate_contract(
        skill_id,
        contract,
        skill_errors,
        trigger_registry,
    )
    _validate_relations(
        skill_id,
        relations,
        skill_errors,
        known_skill_ids,
    )
    _validate_density(skill_id, sections, skill_warnings, profile)

    anchors = _load_yaml(skill_dir / "anchors.yaml", skill_errors, f"{skill_id}: anchors")
    _validate_anchors(
        skill_id=skill_id,
        anchors=anchors,
        skill_errors=skill_errors,
        skill_dir=skill_dir,
        node_ids=node_ids,
        edge_ids=edge_ids,
        community_ids=community_ids,
        computed_graph_hash=computed_graph_hash,
        status=status,
    )

    eval_summary_path = skill_dir / "eval" / "summary.yaml"
    eval_summary = _load_yaml(
        eval_summary_path,
        skill_errors,
        f"{skill_id}: eval summary",
    )
    all_eval_subsets_pass, eval_case_counts = _validate_eval_summary(
        skill_id,
        eval_summary,
        skill_errors,
        manifest.get("bundle_version"),
        identity.get("skill_revision"),
        eval_summary_path,
        profile,
    )

    revisions = _load_yaml(
        skill_dir / "iterations" / "revisions.yaml",
        skill_errors,
        f"{skill_id}: revisions",
    )
    revision_entry_count, has_revision_loop = _validate_revisions(
        skill_id,
        revisions,
        skill_errors,
        manifest.get("bundle_version"),
        identity.get("skill_revision"),
        computed_graph_hash,
    )
    usage_trace_count = _validate_usage_summary(skill_id, sections, skill_dir, skill_errors)
    if status == "published" and usage_trace_count < 3:
        skill_errors.append(f"{skill_id}: published skill must reference at least 3 usage traces")
    if status == "published" and not all_eval_subsets_pass:
        skill_errors.append(f"{skill_id}: published skill must pass all evaluation subsets")
    if status == "published":
        required_eval_cases = profile.get("min_eval_cases_for_published", {})
        for subset_name, minimum in required_eval_cases.items():
            actual = eval_case_counts.get(subset_name, 0)
            if actual < int(minimum):
                skill_errors.append(
                    f"{skill_id}: published requires {subset_name}>={minimum}, got {actual} "
                    f"(need {int(minimum) - actual} more)"
                )
    if status == "published" and not has_revision_loop:
        skill_errors.append(
            f"{skill_id}: published skills must have gone through at least one revision cycle "
            f"(current revision={identity.get('skill_revision')}, history={revision_entry_count})"
        )

    errors.extend(skill_errors)
    warnings.extend(skill_warnings)
    return {
        "skill_id": skill_id,
        "status": status,
        "skill_revision": identity.get("skill_revision"),
        "revision_entry_count": revision_entry_count,
        "has_revision_loop": has_revision_loop,
        "usage_trace_count": usage_trace_count,
        "all_eval_subsets_pass": all_eval_subsets_pass,
        "eval_case_counts": eval_case_counts,
        "relations": relations,
    }


def _validate_contract(
    skill_id: str,
    contract: dict[str, Any],
    errors: list[str],
    trigger_registry: dict[str, dict[str, Any]],
) -> None:
    for field in ("trigger", "intake", "judgment_schema", "boundary"):
        if field not in contract:
            errors.append(f"{skill_id}: Contract missing {field}")

    trigger = contract.get("trigger", {})
    intake = contract.get("intake", {})
    boundary = contract.get("boundary", {})
    if not trigger.get("patterns"):
        errors.append(f"{skill_id}: trigger.patterns must contain at least one pattern")
    if not intake.get("required"):
        errors.append(f"{skill_id}: intake.required must contain at least one field")
    if not boundary.get("fails_when"):
        errors.append(f"{skill_id}: boundary.fails_when must contain at least one pattern")
    if not boundary.get("do_not_fire_when"):
        errors.append(
            f"{skill_id}: boundary.do_not_fire_when must contain at least one pattern"
        )

    _validate_trigger_symbol_list(
        skill_id,
        "Contract.trigger.patterns",
        trigger.get("patterns"),
        errors,
        trigger_registry,
    )
    _validate_trigger_symbol_list(
        skill_id,
        "Contract.trigger.exclusions",
        trigger.get("exclusions"),
        errors,
        trigger_registry,
    )
    _validate_trigger_symbol_list(
        skill_id,
        "Contract.boundary.fails_when",
        boundary.get("fails_when"),
        errors,
        trigger_registry,
    )
    _validate_trigger_symbol_list(
        skill_id,
        "Contract.boundary.do_not_fire_when",
        boundary.get("do_not_fire_when"),
        errors,
        trigger_registry,
    )


def _validate_relations(
    skill_id: str,
    relations: dict[str, Any],
    errors: list[str],
    known_skill_ids: set[str],
) -> None:
    keys = set(relations.keys())
    if keys != set(REQUIRED_RELATIONS):
        errors.append(
            f"{skill_id}: Relations must contain exactly {', '.join(REQUIRED_RELATIONS)}"
        )
    for relation_name in REQUIRED_RELATIONS:
        value = relations.get(relation_name)
        if value is None:
            continue
        if not isinstance(value, list):
            errors.append(f"{skill_id}: relation {relation_name} must be a list")
            continue
        for target in value:
            if not isinstance(target, str):
                errors.append(
                    f"{skill_id}: relation {relation_name} contains non-string target {target!r}"
                )
                continue
            if target.startswith("external:"):
                continue
            if target not in known_skill_ids:
                errors.append(
                    f"{skill_id}: unknown relation target {target} in {relation_name}"
                )


def _validate_anchors(
    *,
    skill_id: str,
    anchors: dict[str, Any],
    skill_errors: list[str],
    skill_dir: Path,
    node_ids: set[str],
    edge_ids: set[str],
    community_ids: set[str],
    computed_graph_hash: str | None,
    status: str | None,
) -> None:
    if not anchors:
        return

    graph_anchor_sets = anchors.get("graph_anchor_sets", [])
    source_anchor_sets = anchors.get("source_anchor_sets", [])
    if status in ANCHOR_REQUIRED_STATUSES and not graph_anchor_sets:
        skill_errors.append(f"{skill_id}: missing graph anchor set for active skill")
    if status in ANCHOR_REQUIRED_STATUSES and not source_anchor_sets:
        skill_errors.append(
            f"{skill_id}: missing source/scenario anchor set for active skill"
        )

    if computed_graph_hash and anchors.get("graph_hash") != computed_graph_hash:
        skill_errors.append(f"{skill_id}: anchors graph_hash mismatch")

    for anchor_set in graph_anchor_sets:
        referenced = 0
        for node_id in anchor_set.get("node_ids", []):
            referenced += 1
            if node_id not in node_ids:
                skill_errors.append(f"{skill_id}: unknown graph node id {node_id}")
        for edge_id in anchor_set.get("edge_ids", []):
            referenced += 1
            if edge_id not in edge_ids:
                skill_errors.append(f"{skill_id}: unknown graph edge id {edge_id}")
        for community_id in anchor_set.get("community_ids", []):
            referenced += 1
            if community_id not in community_ids:
                skill_errors.append(
                    f"{skill_id}: unknown graph community id {community_id}"
                )
        if referenced == 0:
            skill_errors.append(f"{skill_id}: empty graph anchor set")

    for anchor in source_anchor_sets:
        relative_path = anchor.get("path")
        if not relative_path:
            skill_errors.append(f"{skill_id}: source anchor missing path")
            continue
        resolved = (skill_dir / relative_path).resolve()
        if not resolved.exists():
            skill_errors.append(f"{skill_id}: source anchor path does not exist: {relative_path}")
            continue
        line_start = anchor.get("line_start")
        line_end = anchor.get("line_end")
        if line_start is None or line_end is None:
            skill_errors.append(f"{skill_id}: source anchor missing line range for {relative_path}")
            continue
        line_count = len(resolved.read_text(encoding="utf-8").splitlines())
        if not (1 <= int(line_start) <= int(line_end) <= max(line_count, 1)):
            skill_errors.append(f"{skill_id}: source anchor line range invalid for {relative_path}")


def _validate_eval_summary(
    skill_id: str,
    summary: dict[str, Any],
    errors: list[str],
    bundle_version: str | None,
    skill_revision: int | None,
    summary_path: Path,
    profile: dict[str, Any],
) -> tuple[bool, dict[str, int]]:
    if not summary:
        return False, {}

    if summary.get("bundle_version") != bundle_version:
        errors.append(f"{skill_id}: eval summary bundle_version mismatch")
    if summary.get("skill_revision") != skill_revision:
        errors.append(f"{skill_id}: eval summary skill_revision mismatch")
    kiu_test = summary.get("kiu_test", {})
    for gate in ("trigger_test", "fire_test", "boundary_test"):
        if gate not in kiu_test:
            errors.append(f"{skill_id}: eval summary missing kiu_test.{gate}")
    subsets = summary.get("subsets", {})
    for subset_name in (
        "real_decisions",
        "synthetic_adversarial",
        "out_of_distribution",
    ):
        if subset_name not in subsets:
            errors.append(f"{skill_id}: eval summary missing subset {subset_name}")
    coverage_mode = summary.get("references", {}).get("coverage_mode")
    subset_counts = {
        subset_name: _subset_case_count(
            skill_id=skill_id,
            subset_name=subset_name,
            subset=subsets.get(subset_name, {}),
            summary_path=summary_path,
            errors=errors,
            coverage_mode=coverage_mode,
            minimum_required=int(
                profile.get("min_eval_cases_for_published", {}).get(subset_name, 0)
            ),
        )
        for subset_name in (
            "real_decisions",
            "synthetic_adversarial",
            "out_of_distribution",
        )
    }
    return all(
        subsets.get(subset_name, {}).get("status") == "pass"
        for subset_name in (
            "real_decisions",
            "synthetic_adversarial",
            "out_of_distribution",
        )
    ), subset_counts


def _validate_revisions(
    skill_id: str,
    revisions: dict[str, Any],
    errors: list[str],
    bundle_version: str | None,
    skill_revision: int | None,
    computed_graph_hash: str | None,
) -> tuple[int, bool]:
    if not revisions:
        return 0, False

    if revisions.get("bundle_version") != bundle_version:
        errors.append(f"{skill_id}: revisions bundle_version mismatch")
    if revisions.get("current_revision") != skill_revision:
        errors.append(f"{skill_id}: revisions current_revision mismatch")

    history = revisions.get("history", [])
    if not history:
        errors.append(f"{skill_id}: revisions history must contain at least one entry")
        return 0, False

    for entry in history:
        if computed_graph_hash and entry.get("graph_hash") != computed_graph_hash:
            errors.append(f"{skill_id}: revision entry graph_hash mismatch")

    has_revision_loop = int(skill_revision or 0) > 1 and len(history) >= 2
    return len(history), has_revision_loop


def _resolve_validation_profile(root: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        resolved = resolve_profile(root)
    except Exception as exc:
        warnings.append(f"bundle: profile_resolution_fallback ({exc})")
        resolved = {}
    return _normalize_validation_profile(resolved)


def _normalize_validation_profile(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = _deep_merge(DEFAULT_VALIDATION_PROFILE, profile)
    rationale_alias = normalized.get("rationale_density", {})
    rationale_cfg = normalized.setdefault("content_density", {}).setdefault("rationale", {})
    if "warning_min_chars" not in rationale_cfg and "warning_min_chars" in rationale_alias:
        rationale_cfg["warning_min_chars"] = rationale_alias["warning_min_chars"]
    if "min_anchor_refs" not in rationale_cfg and "min_anchor_refs" in rationale_alias:
        rationale_cfg["min_anchor_refs"] = rationale_alias["min_anchor_refs"]
    legacy_min_eval_cases = normalized.get("published_min_eval_cases", {})
    published_cfg = normalized.setdefault("min_eval_cases_for_published", {})
    for subset_name, minimum in legacy_min_eval_cases.items():
        published_cfg.setdefault(subset_name, minimum)
    return normalized


def _load_trigger_registry(
    bundle_root: Path,
    profile: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> dict[str, dict[str, Any]]:
    registry_value = profile.get("trigger_registry")
    if not registry_value:
        errors.append("bundle: missing trigger_registry in resolved profile")
        return {}

    registry_path = _resolve_profile_path(bundle_root, registry_value)
    registry_doc = _load_yaml(registry_path, errors, "trigger registry")
    trigger_entries = registry_doc.get("triggers", [])
    if not isinstance(trigger_entries, list):
        errors.append("trigger registry: triggers must be a list")
        return {}

    registry: dict[str, dict[str, Any]] = {}
    for entry in trigger_entries:
        if not isinstance(entry, dict):
            errors.append(f"trigger registry: invalid trigger entry {entry!r}")
            continue
        symbol = entry.get("symbol")
        if not symbol or not isinstance(symbol, str):
            errors.append("trigger registry: missing symbol")
            continue
        if symbol in registry:
            errors.append(f"trigger registry: duplicate symbol {symbol}")
            continue
        registry[symbol] = entry
        if not str(entry.get("definition", "")).strip():
            warnings.append(f"trigger registry: trigger_symbol_missing_definition {symbol}")
        if not entry.get("positive_examples"):
            warnings.append(
                f"trigger registry: trigger_symbol_missing_positive_examples {symbol}"
            )
        if not entry.get("negative_examples"):
            warnings.append(
                f"trigger registry: trigger_symbol_missing_negative_examples {symbol}"
            )
    return registry


def _resolve_profile_path(bundle_root: Path, raw_path: str | Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate

    bundle_candidate = bundle_root / candidate
    if bundle_candidate.exists():
        return bundle_candidate

    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate

    return bundle_candidate


def _validate_trigger_symbol_list(
    skill_id: str,
    field_name: str,
    value: Any,
    errors: list[str],
    trigger_registry: dict[str, dict[str, Any]],
) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{skill_id}: {field_name} must be a list")
        return
    for symbol in value:
        if not isinstance(symbol, str):
            errors.append(f"{skill_id}: {field_name} contains non-string symbol {symbol!r}")
            continue
        if symbol not in trigger_registry:
            errors.append(f"{skill_id}: unknown_trigger_symbol {symbol} in {field_name}")


def _validate_density(
    skill_id: str,
    sections: dict[str, str],
    warnings: list[str],
    profile: dict[str, Any],
) -> None:
    rationale_cfg = profile.get("content_density", {}).get("rationale", {})
    rationale_text = sections.get("Rationale", "")
    rationale_chars = _dense_char_count(rationale_text)
    rationale_anchor_refs = _count_anchor_refs(rationale_text)
    warning_min_chars = int(rationale_cfg.get("warning_min_chars", 180))
    min_anchor_refs = int(rationale_cfg.get("min_anchor_refs", 1))
    if rationale_chars < warning_min_chars or rationale_anchor_refs < min_anchor_refs:
        warnings.append(
            f"{skill_id}: rationale_below_density_threshold "
            f"(chars={rationale_chars}, min_chars={warning_min_chars}, "
            f"anchor_refs={rationale_anchor_refs}, min_anchor_refs={min_anchor_refs})"
        )

    evidence_cfg = profile.get("content_density", {}).get("evidence_summary", {})
    evidence_text = sections.get("Evidence Summary", "")
    evidence_anchor_refs = _count_anchor_refs(evidence_text)
    evidence_min_anchor_refs = int(evidence_cfg.get("min_anchor_refs", 1))
    if evidence_anchor_refs < evidence_min_anchor_refs:
        warnings.append(
            f"{skill_id}: evidence_summary_missing_anchors "
            f"(anchor_refs={evidence_anchor_refs}, min_anchor_refs={evidence_min_anchor_refs})"
        )


def _dense_char_count(text: str) -> int:
    stripped = re.sub(r"\[\^(?:anchor|trace):[^\]]+\]", "", text)
    stripped = re.sub(r"[`*_>#\-\[\]\(\)\s]+", "", stripped)
    return len(stripped)


def _count_anchor_refs(text: str) -> int:
    return len(re.findall(r"\[\^(?:anchor|trace):[^\]]+\]", text))


def _subset_case_count(
    *,
    skill_id: str,
    subset_name: str,
    subset: dict[str, Any],
    summary_path: Path,
    errors: list[str],
    coverage_mode: str | None,
    minimum_required: int,
) -> int:
    if not isinstance(subset, dict):
        return 0
    resolved_cases = _resolve_subset_cases(
        skill_id=skill_id,
        subset_name=subset_name,
        subset=subset,
        summary_path=summary_path,
        errors=errors,
    )
    total = subset.get("total")
    if total is not None:
        try:
            parsed_total = int(total)
        except (TypeError, ValueError):
            return 0
        if parsed_total != len(resolved_cases):
            errors.append(
                f"{skill_id}: {subset_name} total={parsed_total} does not match "
                f"resolved_cases={len(resolved_cases)}"
            )

    if coverage_mode == "shared_corpus_full_release":
        expected_pattern = f"../../../evaluation/{subset_name}/*.yaml"
        raw_cases = subset.get("cases", [])
        if raw_cases != [expected_pattern]:
            errors.append(
                f"{skill_id}: {subset_name} shared_corpus_full_release cases must be "
                f"[{expected_pattern}]"
            )
        if len(resolved_cases) < minimum_required:
            errors.append(
                f"{skill_id}: {subset_name} shared_corpus_full_release resolves to "
                f"{len(resolved_cases)} cases, requires at least {minimum_required}"
            )

    return len(resolved_cases)


def _resolve_subset_cases(
    *,
    skill_id: str,
    subset_name: str,
    subset: dict[str, Any],
    summary_path: Path,
    errors: list[str],
) -> list[str]:
    raw_cases = subset.get("cases", [])
    if not isinstance(raw_cases, list):
        errors.append(f"{skill_id}: {subset_name} cases must be a list")
        return []

    summary_dir = summary_path.parent
    resolved_cases: list[str] = []
    for entry in raw_cases:
        if not isinstance(entry, str):
            errors.append(
                f"{skill_id}: {subset_name} contains non-string case entry {entry!r}"
            )
            continue
        if any(char in entry for char in "*?[]"):
            matches = sorted(glob(str(summary_dir / entry)))
            if not matches:
                errors.append(
                    f"{skill_id}: {subset_name} cases pattern matched 0 files: {entry}"
                )
                continue
            resolved_cases.extend(str(Path(match).resolve()) for match in matches)
            continue
        resolved_cases.append(entry)
    return resolved_cases


def _detect_relation_cycles(skills: list[dict[str, Any]], warnings: list[str]) -> None:
    depends_on = {
        skill["skill_id"]: set(skill.get("relations", {}).get("depends_on", []))
        for skill in skills
    }
    for skill_id, targets in depends_on.items():
        if skill_id in targets:
            warnings.append(f"{skill_id}: relation_cycle_detected depends_on self")
        for target in targets:
            if target in depends_on and skill_id in depends_on[target] and skill_id < target:
                warnings.append(
                    f"relation_cycle_detected: depends_on {skill_id} <-> {target}"
                )


def _load_yaml(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"{label}: missing file {path}")
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        errors.append(f"{label}: failed to parse YAML: {exc}")
        return {}
    return loaded or {}


def _load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"{label}: missing file {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        errors.append(f"{label}: failed to parse JSON: {exc}")
        return {}


def _parse_sections(markdown: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", markdown, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[name] = markdown[start:end].strip()
    return sections


def _validate_usage_summary(
    skill_id: str,
    sections: dict[str, str],
    skill_dir: Path,
    errors: list[str],
) -> int:
    usage_summary = sections.get("Usage Summary", "")
    trace_refs = re.findall(r"traces/[\w./-]+\.yaml", usage_summary)
    for trace_ref in trace_refs:
        resolved = (skill_dir / ".." / ".." / trace_ref).resolve()
        if not resolved.exists():
            errors.append(f"{skill_id}: missing trace reference {trace_ref}")
    return len(trace_refs)


def _extract_yaml_section(section_text: str, errors: list[str], label: str) -> dict[str, Any]:
    match = re.search(r"```ya?ml\n(.*?)```", section_text, flags=re.DOTALL)
    if not match:
        errors.append(f"{label}: missing fenced yaml block")
        return {}
    try:
        loaded = yaml.safe_load(match.group(1))
    except Exception as exc:  # pragma: no cover
        errors.append(f"{label}: invalid YAML block: {exc}")
        return {}
    return loaded or {}


def _canonical_graph_hash(graph_doc: dict[str, Any]) -> str:
    canonical_doc = dict(graph_doc)
    canonical_doc.pop("graph_hash", None)
    encoded = json.dumps(canonical_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
