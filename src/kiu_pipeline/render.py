from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from .anchors import build_candidate_anchors
from .diff import build_metrics
from .draft import build_candidate_skill_markdown
from .eval_prefill import build_prefilled_eval_summary
from .models import CandidateSeed, SourceBundle


BUNDLE_VERSION = "0.2.0"
SCHEMA_VERSION = "kiu.bundle.schema/v0.1"
SKILL_SPEC_VERSION = "kiu.skill-spec/v0.1"
RELATION_ENUM_VERSION = "kiu.relation-enum/v1"


def render_generated_run(
    *,
    source_bundle: SourceBundle,
    seeds: list[CandidateSeed],
    output_root: str | Path,
    run_id: str,
) -> Path:
    output_root = Path(output_root)
    run_root = output_root / source_bundle.manifest["bundle_id"] / run_id
    bundle_root = run_root / "bundle"
    reports_root = run_root / "reports"
    workflow_root = run_root / "workflow_candidates"

    if run_root.exists():
        shutil.rmtree(run_root)

    bundle_root.mkdir(parents=True, exist_ok=True)
    reports_root.mkdir(parents=True, exist_ok=True)
    workflow_root.mkdir(parents=True, exist_ok=True)

    _copy_shared_assets(source_bundle.root, bundle_root)
    _copy_bundle_profile(source_bundle.root, bundle_root)

    rendered_seeds: list[CandidateSeed] = []
    workflow_only_seeds: list[CandidateSeed] = []
    manifest_skills: list[dict[str, Any]] = []

    for seed in seeds:
        if seed.metadata["disposition"] == "workflow_script_candidate":
            _render_workflow_candidate(
                workflow_root=workflow_root,
                source_bundle=source_bundle,
                seed=seed,
            )
            workflow_only_seeds.append(seed)
            continue

        _render_skill_candidate(
            bundle_root=bundle_root,
            source_bundle=source_bundle,
            seed=seed,
            skill_revision=1,
        )
        rendered_seeds.append(seed)
        manifest_skills.append(
            {
                "skill_id": seed.candidate_id,
                "path": f"skills/{seed.candidate_id}",
                "status": "under_evaluation",
                "skill_revision": 1,
            }
        )

    manifest = {
        "bundle_id": f"{source_bundle.manifest['bundle_id']}-candidate-bundle",
        "title": f"KiU v0.2 Candidate Bundle for {source_bundle.manifest['bundle_id']}",
        "bundle_version": BUNDLE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "skill_spec_version": SKILL_SPEC_VERSION,
        "relation_enum_version": RELATION_ENUM_VERSION,
        "language": source_bundle.manifest.get("language", "zh-CN"),
        "domain": source_bundle.domain,
        "created_at": date.today().isoformat(),
        "generated_from": {
            "source_bundle_id": source_bundle.manifest["bundle_id"],
            "source_bundle_version": source_bundle.manifest["bundle_version"],
            "profile_version": source_bundle.profile.get("profile_version"),
        },
        "graph": {
            "path": source_bundle.manifest["graph"]["path"],
            "graph_version": source_bundle.manifest["graph"]["graph_version"],
            "graph_hash": source_bundle.manifest["graph"]["graph_hash"],
        },
        "skills": manifest_skills,
        "shared_assets": dict(source_bundle.manifest.get("shared_assets", {})),
    }
    _write_yaml(bundle_root / "manifest.yaml", manifest)

    metrics = build_metrics(
        source_bundle=source_bundle,
        rendered_seeds=rendered_seeds,
        workflow_only_seeds=workflow_only_seeds,
    )
    (reports_root / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return run_root


def load_generated_candidates(bundle_root: str | Path) -> list[dict[str, Any]]:
    bundle_root = Path(bundle_root)
    manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
    candidates: list[dict[str, Any]] = []
    for entry in manifest.get("skills", []):
        skill_dir = bundle_root / entry["path"]
        candidates.append(
            {
                "skill_id": entry["skill_id"],
                "skill_dir": skill_dir,
                "skill_markdown": (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
                "anchors": yaml.safe_load((skill_dir / "anchors.yaml").read_text(encoding="utf-8")),
                "eval_summary": yaml.safe_load(
                    (skill_dir / "eval" / "summary.yaml").read_text(encoding="utf-8")
                ),
                "revisions": yaml.safe_load(
                    (skill_dir / "iterations" / "revisions.yaml").read_text(encoding="utf-8")
                ),
                "scenario_families": yaml.safe_load(
                    (skill_dir / "usage" / "scenarios.yaml").read_text(encoding="utf-8")
                ),
                "candidate": yaml.safe_load(
                    (skill_dir / "candidate.yaml").read_text(encoding="utf-8")
                ),
                "nearest_skill_id": entry["skill_id"],
            }
        )
    return candidates


def materialize_refined_candidates(
    bundle_root: str | Path,
    refined_candidates: list[dict[str, Any]],
) -> None:
    bundle_root = Path(bundle_root)
    manifest_path = bundle_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    skill_revision_map = {
        candidate["candidate"]["candidate_id"]: candidate["revisions"]["current_revision"]
        for candidate in refined_candidates
    }
    for entry in manifest.get("skills", []):
        if entry["skill_id"] in skill_revision_map:
            entry["skill_revision"] = skill_revision_map[entry["skill_id"]]
            entry["status"] = "under_evaluation"
    _write_yaml(manifest_path, manifest)

    for candidate in refined_candidates:
        skill_dir = candidate.get("skill_dir") or (
            bundle_root / "skills" / candidate["candidate"]["candidate_id"]
        )
        (skill_dir / "SKILL.md").write_text(candidate["skill_markdown"], encoding="utf-8")
        _write_yaml(skill_dir / "anchors.yaml", candidate["anchors"])
        _write_yaml(skill_dir / "eval" / "summary.yaml", candidate["eval_summary"])
        _write_yaml(skill_dir / "iterations" / "revisions.yaml", candidate["revisions"])
        _write_yaml(skill_dir / "candidate.yaml", candidate["candidate"])


def _copy_shared_assets(source_root: Path, bundle_root: Path) -> None:
    for relative in ("graph", "traces", "evaluation", "sources"):
        shutil.copytree(source_root / relative, bundle_root / relative)


def _copy_bundle_profile(source_root: Path, bundle_root: Path) -> None:
    for relative in ("automation.yaml", "triggers.yaml", "materials.yaml"):
        source_path = source_root / relative
        if source_path.exists():
            shutil.copy2(source_path, bundle_root / relative)


def _render_skill_candidate(
    *,
    bundle_root: Path,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
    skill_revision: int,
) -> None:
    skill_dir = bundle_root / "skills" / seed.candidate_id
    (skill_dir / "eval").mkdir(parents=True, exist_ok=True)
    (skill_dir / "iterations").mkdir(parents=True, exist_ok=True)
    (skill_dir / "usage").mkdir(parents=True, exist_ok=True)

    anchors = build_candidate_anchors(
        source_bundle=source_bundle,
        seed=seed,
        bundle_version=BUNDLE_VERSION,
        skill_revision=skill_revision,
    )
    _write_yaml(skill_dir / "anchors.yaml", anchors)

    eval_summary = build_prefilled_eval_summary(
        seed=seed,
        bundle_version=BUNDLE_VERSION,
        skill_revision=skill_revision,
    )
    _write_yaml(skill_dir / "eval" / "summary.yaml", eval_summary)

    revisions = _build_revision_log(source_bundle, seed, skill_revision)
    _write_yaml(skill_dir / "iterations" / "revisions.yaml", revisions)

    scenario_families = _scenario_families_for_seed(seed)
    _write_yaml(skill_dir / "usage" / "scenarios.yaml", scenario_families)

    skill_markdown = build_candidate_skill_markdown(
        source_bundle=source_bundle,
        seed=seed,
        bundle_version=BUNDLE_VERSION,
        skill_revision=skill_revision,
        eval_summary=eval_summary,
        revisions=revisions,
    )
    (skill_dir / "SKILL.md").write_text(skill_markdown, encoding="utf-8")

    _write_yaml(skill_dir / "candidate.yaml", seed.metadata)


def _scenario_families_for_seed(seed: CandidateSeed) -> dict[str, Any]:
    if seed.source_skill and seed.source_skill.scenario_families:
        return seed.source_skill.scenario_families
    scenario_families = seed.seed_content.get("scenario_families", {})
    return scenario_families if isinstance(scenario_families, dict) else {}


def _render_workflow_candidate(
    *,
    workflow_root: Path,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
) -> None:
    candidate_dir = workflow_root / seed.candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    _write_yaml(candidate_dir / "candidate.yaml", seed.metadata)
    workflow_doc = _build_workflow_descriptor(source_bundle=source_bundle, seed=seed)
    _write_yaml(candidate_dir / "workflow.yaml", workflow_doc)
    note = (
        f"# {seed.candidate_id}\n\n"
        "This seed was downgraded to `workflow_script_candidate` because both"
        " workflow certainty and context certainty are high. It is preserved for"
        " audit but is intentionally excluded from `bundle/skills/`.\n"
    )
    (candidate_dir / "README.md").write_text(note, encoding="utf-8")
    (candidate_dir / "CHECKLIST.md").write_text(
        _build_workflow_checklist(workflow_doc),
        encoding="utf-8",
    )


def _build_revision_log(
    source_bundle: SourceBundle,
    seed: CandidateSeed,
    skill_revision: int,
) -> dict[str, Any]:
    revision_seed = seed.seed_content.get("revision_seed", {})
    source_skill = seed.source_skill
    source_revisions = source_skill.revisions if source_skill else {}
    source_history = source_revisions.get("history", []) if isinstance(source_revisions, dict) else []
    source_current_summary = (
        source_skill.sections.get("Revision Summary", "").strip()
        if source_skill and isinstance(source_skill.sections, dict)
        else ""
    )
    if not source_current_summary and source_history:
        source_current_summary = str(source_history[-1].get("summary", "") or "").strip()
    source_evidence_changes = []
    if source_history and isinstance(source_history[-1], dict):
        source_evidence_changes = [
            str(item).strip()
            for item in source_history[-1].get("evidence_changes", [])
            if str(item).strip()
        ]
    source_open_gaps = [
        str(item).strip()
        for item in source_revisions.get("open_gaps", [])
        if str(item).strip()
    ] if isinstance(source_revisions, dict) else []
    return {
        "skill_id": seed.candidate_id,
        "bundle_version": BUNDLE_VERSION,
        "current_revision": skill_revision,
        "history": [
            {
                "revision": skill_revision,
                "date": date.today().isoformat(),
                "summary": source_current_summary or revision_seed.get(
                    "summary",
                    (
                        "Initial v0.2 deterministic candidate seed produced from the"
                        " released graph snapshot and source bundle."
                    ),
                ),
                "graph_hash": source_bundle.manifest["graph"]["graph_hash"],
                "effective_status": "under_evaluation",
                "evidence_changes": source_evidence_changes or revision_seed.get(
                    "evidence_changes",
                    [
                        "Attached graph-derived seed anchors.",
                        "Preserved available source/scenario anchors from the gold reference skill.",
                        "Prefilled evaluation summary from the shared evaluation corpus.",
                    ],
                ),
            }
        ],
        "open_gaps": source_open_gaps or revision_seed.get(
            "open_gaps",
            [
                "Review whether the contract should be tightened before publication.",
                "Confirm that representative traces still match the intended trigger boundary.",
            ],
        ),
    }


def _build_workflow_descriptor(
    *,
    source_bundle: SourceBundle,
    seed: CandidateSeed,
) -> dict[str, Any]:
    nodes = {
        node["id"]: node
        for node in source_bundle.graph_doc.get("nodes", [])
        if isinstance(node, dict) and "id" in node
    }
    edges = {
        edge["id"]: edge
        for edge in source_bundle.graph_doc.get("edges", [])
        if isinstance(edge, dict) and "id" in edge
    }
    communities = {
        community["id"]: community
        for community in source_bundle.graph_doc.get("communities", [])
        if isinstance(community, dict) and "id" in community
    }
    primary_node_id = seed.primary_node_id
    primary_node = nodes.get(primary_node_id, {})
    supporting_nodes = [nodes[node_id] for node_id in seed.supporting_node_ids if node_id in nodes]
    supporting_edges = [edges[edge_id] for edge_id in seed.supporting_edge_ids if edge_id in edges]
    related_communities = [
        communities[community_id]
        for community_id in seed.community_ids
        if community_id in communities
    ]

    return {
        "workflow_id": seed.candidate_id,
        "title": _humanize_identifier(seed.candidate_id),
        "source_bundle_id": source_bundle.manifest["bundle_id"],
        "source_graph_hash": source_bundle.manifest["graph"]["graph_hash"],
        "recommended_execution_mode": seed.metadata["recommended_execution_mode"],
        "disposition": seed.metadata["disposition"],
        "workflow_certainty": seed.metadata["workflow_certainty"],
        "context_certainty": seed.metadata["context_certainty"],
        "objective": (
            "Run a deterministic preflight before execution when the control pattern is"
            " better served by a fixed workflow than an agentic skill."
        ),
        "seed": {
            "primary_node_id": primary_node_id,
            "supporting_node_ids": list(seed.supporting_node_ids),
            "supporting_edge_ids": list(seed.supporting_edge_ids),
            "community_ids": list(seed.community_ids),
        },
        "evidence_anchors": {
            "primary_node": {
                "id": primary_node_id,
                "label": primary_node.get("label", primary_node_id),
                "type": primary_node.get("type"),
            },
            "supporting_nodes": [
                {
                    "id": node["id"],
                    "label": node.get("label", node["id"]),
                    "type": node.get("type"),
                }
                for node in supporting_nodes
            ],
            "supporting_edges": [
                {
                    "id": edge["id"],
                    "type": edge.get("type"),
                    "from": edge.get("from"),
                    "to": edge.get("to"),
                }
                for edge in supporting_edges
            ],
            "communities": [
                {
                    "id": community["id"],
                    "label": community.get("label", community["id"]),
                }
                for community in related_communities
            ],
        },
        "checklist_sections": [
            "Scope",
            "Rollback",
            "Reversibility",
            "Evidence Anchors",
        ],
    }


def _build_workflow_checklist(workflow_doc: dict[str, Any]) -> str:
    anchors = workflow_doc.get("evidence_anchors", {})
    primary = anchors.get("primary_node", {})
    supporting_nodes = anchors.get("supporting_nodes", [])
    supporting_edges = anchors.get("supporting_edges", [])
    communities = anchors.get("communities", [])

    return (
        f"# {workflow_doc['workflow_id']}\n\n"
        f"Execution mode: `{workflow_doc['recommended_execution_mode']}`\n\n"
        "## Objective\n"
        f"{workflow_doc['objective']}\n\n"
        "## Scope\n"
        "- [ ] Summarize the proposed change and the exact affected surface.\n"
        "- [ ] Name the users, data paths, and downstream systems in scope.\n"
        "- [ ] Define the abort condition before execution starts.\n\n"
        "## Rollback\n"
        "- [ ] Confirm rollback steps are written, owned, and time-bounded.\n"
        "- [ ] State whether rollback has been rehearsed on a representative environment.\n"
        "- [ ] Record the monitoring signal that would trigger rollback.\n\n"
        "## Reversibility\n"
        "- [ ] Identify any irreversible data writes or side effects.\n"
        "- [ ] Document the safeguard for irreversible steps: backup, dual-write, holdback, or canary.\n"
        "- [ ] Record the explicit go/no-go decision.\n\n"
        "## Evidence Anchors\n"
        f"- Primary node: `{primary.get('id', '<missing>')}`"
        f" ({primary.get('label', '<missing-label>')})\n"
        f"- Supporting nodes: {', '.join(_format_anchor_list(supporting_nodes, key='label')) or 'none'}\n"
        f"- Supporting edges: {', '.join(_format_edge_list(supporting_edges)) or 'none'}\n"
        f"- Communities: {', '.join(_format_anchor_list(communities, key='label')) or 'none'}\n"
    )


def _format_anchor_list(items: list[dict[str, Any]], *, key: str) -> list[str]:
    rendered: list[str] = []
    for item in items:
        item_id = item.get("id", "<missing-id>")
        label = item.get(key, item_id)
        rendered.append(f"`{item_id}` ({label})")
    return rendered


def _format_edge_list(items: list[dict[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for item in items:
        item_id = item.get("id", "<missing-id>")
        edge_type = item.get("type", "<missing-type>")
        edge_from = item.get("from", "<missing-from>")
        edge_to = item.get("to", "<missing-to>")
        rendered.append(f"`{item_id}` ({edge_type}: {edge_from} -> {edge_to})")
    return rendered


def _humanize_identifier(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
