import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


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


def validate_bundle(bundle_path: str | Path) -> dict[str, Any]:
    root = Path(bundle_path)
    errors: list[str] = []

    manifest = _load_yaml(root / "manifest.yaml", errors, "manifest")
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
    for entry in skill_entries:
        skills.append(
            _validate_skill(
                root=root,
                manifest=manifest,
                skill_entry=entry,
                errors=errors,
                node_ids=node_ids,
                edge_ids=edge_ids,
                community_ids=community_ids,
                computed_graph_hash=computed_graph_hash,
            )
        )

    traces_root = root / "traces"
    evaluation_root = root / "evaluation"
    shared_assets = {
        "trace_count": len(list(traces_root.rglob("*.yaml"))),
        "evaluation_count": len(list(evaluation_root.rglob("*.yaml"))),
    }

    return {
        "bundle_path": str(root),
        "manifest": manifest,
        "graph": graph_report,
        "shared_assets": shared_assets,
        "skills": skills,
        "errors": errors,
    }


def _validate_skill(
    *,
    root: Path,
    manifest: dict[str, Any],
    skill_entry: dict[str, Any],
    errors: list[str],
    node_ids: set[str],
    edge_ids: set[str],
    community_ids: set[str],
    computed_graph_hash: str | None,
) -> dict[str, Any]:
    skill_id = skill_entry.get("skill_id", "<missing-skill-id>")
    skill_dir = root / skill_entry.get("path", "")
    skill_errors: list[str] = []

    for relative_path in REQUIRED_SKILL_FILES:
        if not (skill_dir / relative_path).exists():
            skill_errors.append(f"{skill_id}: missing required file {relative_path}")

    skill_doc = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
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

    _validate_contract(skill_id, contract, skill_errors)
    _validate_relations(skill_id, relations, skill_errors)

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

    eval_summary = _load_yaml(
        skill_dir / "eval" / "summary.yaml",
        skill_errors,
        f"{skill_id}: eval summary",
    )
    _validate_eval_summary(
        skill_id,
        eval_summary,
        skill_errors,
        manifest.get("bundle_version"),
        identity.get("skill_revision"),
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

    errors.extend(skill_errors)
    return {
        "skill_id": skill_id,
        "status": status,
        "skill_revision": identity.get("skill_revision"),
        "revision_entry_count": revision_entry_count,
        "has_revision_loop": has_revision_loop,
    }


def _validate_contract(skill_id: str, contract: dict[str, Any], errors: list[str]) -> None:
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


def _validate_relations(skill_id: str, relations: dict[str, Any], errors: list[str]) -> None:
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
) -> None:
    if not summary:
        return

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
