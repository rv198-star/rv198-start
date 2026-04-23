from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


GRAPH_VERSION_V02 = "kiu.graph/v0.2"

NODE_SOURCE_FILES: dict[str, dict[str, str]] = {
    "poor-charlies-almanack-v0.1": {
        "n_circle_principle": "sources/circle-of-competence.md",
        "n_invert_principle": "sources/invert-the-problem.md",
        "n_margin_principle": "sources/margin-of-safety-sizing.md",
        "n_bias_principle": "sources/bias-self-audit.md",
        "n_opportunity_principle": "sources/opportunity-cost-of-the-next-best-idea.md",
        "n_dotcom_refusal_trace": "traces/canonical/dotcom-refusal.yaml",
        "n_google_omission_trace": "traces/canonical/google-omission.yaml",
        "n_crypto_rejection_trace": "traces/canonical/crypto-rejection.yaml",
        "n_inversion_checklist_trace": "traces/canonical/anti-ruin-checklist.yaml",
        "n_margin_see_candies_trace": "traces/canonical/sees-candies-discipline.yaml",
        "n_salomon_cap_trace": "traces/canonical/salomon-exposure-cap.yaml",
        "n_bias_us_air_trace": "traces/canonical/us-air-regret.yaml",
        "n_costco_switch_trace": "traces/canonical/costco-next-best-idea.yaml",
        "n_eval_surface_familiarity": "evaluation/synthetic_adversarial/tsla-surface-familiarity.yaml",
        "n_eval_ood_career_offer": "evaluation/out_of_distribution/career-offer-choice.yaml",
    },
    "engineering-postmortem-v0.1": {
        "n_postmortem_principle": "sources/engineering-postmortem-notes.md",
        "n_blast_radius_principle": "sources/engineering-postmortem-notes.md",
        "n_reversibility_gate": "sources/engineering-postmortem-notes.md",
        "n_blameless_db_trace": "traces/canonical/blameless-db-index-rollout.yaml",
        "n_timeline_gap_trace": "traces/canonical/incident-timeline-gap.yaml",
        "n_runbook_reset_trace": "traces/canonical/runbook-ownership-reset.yaml",
        "n_flag_guard_trace": "traces/canonical/blast-radius-flag-guard.yaml",
        "n_phased_rollout_trace": "traces/canonical/phased-rollout-holdback.yaml",
        "n_irreversible_migration_trace": "traces/canonical/irreversible-migration-precheck.yaml",
    },
}


def canonical_graph_hash(graph_doc: dict[str, Any]) -> str:
    canonical_doc = dict(graph_doc)
    canonical_doc.pop("graph_hash", None)
    encoded = json.dumps(canonical_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def migrate_bundle_graph(bundle_path: str | Path) -> dict[str, Any]:
    root = Path(bundle_path)
    manifest = _load_yaml(root / "manifest.yaml")
    bundle_id = manifest.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise ValueError(f"{root}: manifest missing bundle_id")

    graph_meta = manifest.get("graph", {})
    graph_path_value = graph_meta.get("path")
    if not isinstance(graph_path_value, str) or not graph_path_value:
        raise ValueError(f"{root}: manifest missing graph.path")

    graph_path = root / graph_path_value
    graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
    migrated = migrate_graph_doc(bundle_id=bundle_id, graph_doc=graph_doc)
    graph_hash = migrated["graph_hash"]

    graph_path.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest.setdefault("graph", {})
    manifest["graph"]["graph_version"] = migrated["graph_version"]
    manifest["graph"]["graph_hash"] = graph_hash
    _write_yaml(root / "manifest.yaml", manifest)

    for skill_entry in manifest.get("skills", []):
        skill_dir = root / skill_entry["path"]
        anchors_path = skill_dir / "anchors.yaml"
        anchors = _load_yaml(anchors_path)
        if anchors:
            anchors["graph_version"] = migrated["graph_version"]
            anchors["graph_hash"] = graph_hash
            _write_yaml(anchors_path, anchors)

        revisions_path = skill_dir / "iterations" / "revisions.yaml"
        revisions = _load_yaml(revisions_path)
        if revisions:
            for entry in revisions.get("history", []):
                entry["graph_hash"] = graph_hash
            _write_yaml(revisions_path, revisions)

    return {
        "bundle_path": str(root),
        "bundle_id": bundle_id,
        "graph_version": migrated["graph_version"],
        "graph_hash": graph_hash,
        "node_count": len(migrated.get("nodes", [])),
        "edge_count": len(migrated.get("edges", [])),
    }


def migrate_graph_doc(
    *,
    bundle_id: str,
    graph_doc: dict[str, Any],
) -> dict[str, Any]:
    source_key = bundle_id
    if source_key not in NODE_SOURCE_FILES:
        source_snapshot = graph_doc.get("source_snapshot")
        if isinstance(source_snapshot, str) and source_snapshot in NODE_SOURCE_FILES:
            source_key = source_snapshot
    node_source_map = NODE_SOURCE_FILES.get(source_key)
    if node_source_map is None:
        raise ValueError(f"{bundle_id}: no v0.2 migration source map registered")

    migrated = dict(graph_doc)
    migrated["graph_version"] = GRAPH_VERSION_V02

    nodes: list[dict[str, Any]] = []
    for node in graph_doc.get("nodes", []):
        source_file = node_source_map.get(node["id"])
        if source_file is None:
            raise ValueError(f"{bundle_id}: missing source_file mapping for node {node['id']}")
        migrated_node = dict(node)
        migrated_node["source_file"] = source_file
        migrated_node["source_location"] = None
        migrated_node["extraction_kind"] = "EXTRACTED"
        nodes.append(migrated_node)

    edges: list[dict[str, Any]] = []
    source_by_node_id = {node["id"]: node["source_file"] for node in nodes}
    for edge in graph_doc.get("edges", []):
        migrated_edge = dict(edge)
        migrated_edge["source_file"] = _infer_edge_source_file(edge, source_by_node_id)
        migrated_edge["source_location"] = None
        migrated_edge["extraction_kind"] = "EXTRACTED"
        migrated_edge["confidence"] = 1.0
        edges.append(migrated_edge)

    migrated["nodes"] = nodes
    migrated["edges"] = edges
    migrated["graph_hash"] = canonical_graph_hash(migrated)
    return migrated


def _infer_edge_source_file(edge: dict[str, Any], source_by_node_id: dict[str, str]) -> str:
    if edge.get("type") == "supports":
        target_source = source_by_node_id.get(edge.get("to"))
        if target_source:
            return target_source
    source_source = source_by_node_id.get(edge.get("from"))
    if source_source:
        return source_source
    target_source = source_by_node_id.get(edge.get("to"))
    if target_source:
        return target_source
    raise ValueError(f"edge {edge.get('id')}: unable to infer source_file")


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
