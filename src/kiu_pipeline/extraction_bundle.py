from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from kiu_graph.clustering import derive_graph_communities
from kiu_graph.migrate import canonical_graph_hash


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEED_NODE_TYPES = ["principle_signal", "control_signal"]
DEFAULT_CANDIDATE_KINDS = {
    "general_agentic": {
        "workflow_certainty": "medium",
        "context_certainty": "high",
    },
    "workflow_script": {
        "workflow_certainty": "high",
        "context_certainty": "high",
    },
}
DEFAULT_ROUTING_RULES = [
    {
        "when": {
            "workflow_certainty": "high",
            "context_certainty": "high",
        },
        "recommended_execution_mode": "workflow_script",
        "disposition": "workflow_script_candidate",
    },
    {
        "when": {
            "workflow_certainty": "medium",
            "context_certainty": "high",
        },
        "recommended_execution_mode": "llm_agentic",
        "disposition": "skill_candidate",
    },
]


def scaffold_extraction_bundle(
    *,
    source_chunks_path: str | Path,
    graph_path: str | Path,
    output_root: str | Path,
    inherits_from: str = "default",
    title: str | None = None,
) -> Path:
    source_chunks_input_path = Path(source_chunks_path)
    output_root = Path(output_root)

    source_chunks_doc = json.loads(source_chunks_input_path.read_text(encoding="utf-8"))
    graph_doc = json.loads(Path(graph_path).read_text(encoding="utf-8"))

    source_id = str(source_chunks_doc["source_id"])
    bundle_root = output_root / "bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)

    (bundle_root / "graph").mkdir(parents=True, exist_ok=True)
    (bundle_root / "sources").mkdir(parents=True, exist_ok=True)
    (bundle_root / "ingestion").mkdir(parents=True, exist_ok=True)
    (bundle_root / "skills").mkdir(parents=True, exist_ok=True)
    (bundle_root / "traces" / "canonical").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "real_decisions").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "synthetic_adversarial").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "out_of_distribution").mkdir(parents=True, exist_ok=True)

    source_markdown_path = _resolve_source_file(
        source_file=str(source_chunks_doc["source_file"]),
        source_chunks_path=source_chunks_input_path,
    )
    copied_source_relpath = Path("sources") / source_markdown_path.name
    shutil.copy2(source_markdown_path, bundle_root / copied_source_relpath)

    persisted_source_chunks = _rewrite_source_chunks_doc(
        source_chunks_doc=source_chunks_doc,
        rewritten_source_file=copied_source_relpath.as_posix(),
    )
    (bundle_root / "ingestion" / "source-chunks-v0.1.json").write_text(
        json.dumps(persisted_source_chunks, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rewritten_graph_doc = _rewrite_graph_source_paths(
        graph_doc=graph_doc,
        source_snapshot=source_id,
        rewritten_source_file=copied_source_relpath.as_posix(),
    )
    if not rewritten_graph_doc.get("communities"):
        rewritten_graph_doc["communities"] = derive_graph_communities(rewritten_graph_doc)

    skill_seed_specs = _hydrate_graph_with_skill_seeds(
        bundle_root=bundle_root,
        graph_doc=rewritten_graph_doc,
    )

    graph_hash = canonical_graph_hash(rewritten_graph_doc)
    rewritten_graph_doc["graph_hash"] = graph_hash
    (bundle_root / "graph" / "graph.json").write_text(
        json.dumps(rewritten_graph_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "bundle_id": f"{source_id}-source-v0.6",
        "title": title or _humanize_title(source_id),
        "bundle_version": "0.6.0-dev",
        "schema_version": "kiu.bundle.schema/v0.1",
        "skill_spec_version": "kiu.skill-spec/v0.6",
        "relation_enum_version": "kiu.relation-enum/v1",
        "language": source_chunks_doc.get("language", "zh-CN"),
        "domain": inherits_from,
        "created_at": date.today().isoformat(),
        "graph": {
            "path": "graph/graph.json",
            "graph_version": rewritten_graph_doc["graph_version"],
            "graph_hash": graph_hash,
        },
        "skills": [],
        "shared_assets": {
            "traces": "traces",
            "evaluation": "evaluation",
            "sources": "sources",
        },
    }
    _write_yaml(bundle_root / "manifest.yaml", manifest)
    _write_yaml(
        bundle_root / "automation.yaml",
        {
            "profile_version": "kiu.pipeline-profile/v0.3",
            "source_bundle_id": manifest["bundle_id"],
            "inherits_from": inherits_from,
            "trigger_registry": "triggers.yaml",
            "seed_node_types": DEFAULT_SEED_NODE_TYPES,
            "max_candidates": 12,
            "candidate_kinds": DEFAULT_CANDIDATE_KINDS,
            "routing_rules": DEFAULT_ROUTING_RULES,
        },
    )
    _write_yaml(
        bundle_root / "materials.yaml",
        {
            "source_id": source_id,
            "materials": [
                {
                    "source_id": source_id,
                    "kind": "markdown_document",
                    "original_path": source_markdown_path.as_posix(),
                    "bundle_path": copied_source_relpath.as_posix(),
                    "line_count": len(source_markdown_path.read_text(encoding="utf-8").splitlines()),
                    "source_chunks_path": "ingestion/source-chunks-v0.1.json",
                    "chunk_count": len(source_chunks_doc.get("chunks", [])),
                }
            ],
        },
    )
    _write_yaml(
        bundle_root / "triggers.yaml",
        _build_trigger_registry(skill_seed_specs),
    )
    return bundle_root


def _hydrate_graph_with_skill_seeds(
    *,
    bundle_root: Path,
    graph_doc: dict[str, Any],
) -> list[dict[str, Any]]:
    node_map = {
        node["id"]: node
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    adjacency = _build_adjacency(graph_doc.get("edges", []))
    seed_specs: list[dict[str, Any]] = []

    for node in graph_doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("type") not in DEFAULT_SEED_NODE_TYPES:
            continue
        candidate_id = _slugify(str(node.get("label", node["id"])))
        title = _humanize_title(candidate_id)
        descriptors = _collect_descriptors(
            bundle_root=bundle_root,
            node=node,
            node_map=node_map,
            adjacency=adjacency,
            candidate_id=candidate_id,
        )
        contract = _build_seed_contract(candidate_id)
        trace_ref = _write_trace_doc(
            bundle_root=bundle_root,
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
        )
        eval_summary = _write_eval_docs(
            bundle_root=bundle_root,
            candidate_id=candidate_id,
            title=title,
            descriptors=descriptors,
            contract=contract,
        )
        usage_notes = _build_usage_notes(title=title, descriptors=descriptors)
        skill_seed = {
            "title": title,
            "contract": contract,
            "relations": {
                "depends_on": [],
                "delegates_to": [],
                "constrained_by": [],
                "complements": [],
                "contradicts": [],
            },
            "rationale": _build_seed_rationale(title=title, descriptors=descriptors, contract=contract),
            "evidence_summary": _build_seed_evidence_summary(title=title, descriptors=descriptors),
            "trace_refs": [trace_ref],
            "usage_notes": usage_notes,
            "eval_summary": eval_summary,
            "revision_seed": {
                "summary": (
                    f"Initial extraction-backed draft for {title} created from provenance-rich graph evidence."
                ),
                "evidence_changes": [
                    "Bound the draft to graph/source double anchoring.",
                    "Attached one canonical smoke trace and one smoke case per evaluation subset.",
                ],
                "open_gaps": [
                    "Confirm whether the current trigger symbols are specific enough for production use.",
                    "Replace smoke evaluation with real domain cases before publication.",
                ],
            },
        }
        node["skill_seed"] = skill_seed
        seed_specs.append(
            {
                "candidate_id": candidate_id,
                "title": title,
                "contract": contract,
            }
        )
    return seed_specs


def _rewrite_graph_source_paths(
    *,
    graph_doc: dict[str, Any],
    source_snapshot: str,
    rewritten_source_file: str,
) -> dict[str, Any]:
    rewritten = dict(graph_doc)
    rewritten["source_snapshot"] = source_snapshot
    rewritten["nodes"] = [
        _rewrite_source_file(entity=node, rewritten_source_file=rewritten_source_file)
        for node in graph_doc.get("nodes", [])
        if isinstance(node, dict)
    ]
    rewritten["edges"] = [
        _rewrite_source_file(entity=edge, rewritten_source_file=rewritten_source_file)
        for edge in graph_doc.get("edges", [])
        if isinstance(edge, dict)
    ]
    rewritten["communities"] = [
        dict(community)
        for community in graph_doc.get("communities", [])
        if isinstance(community, dict)
    ]
    rewritten.pop("graph_hash", None)
    return rewritten


def _rewrite_source_chunks_doc(
    *,
    source_chunks_doc: dict[str, Any],
    rewritten_source_file: str,
) -> dict[str, Any]:
    rewritten = dict(source_chunks_doc)
    rewritten["source_file"] = rewritten_source_file
    rewritten["chunks"] = []
    for chunk in source_chunks_doc.get("chunks", []):
        if not isinstance(chunk, dict):
            continue
        chunk_doc = dict(chunk)
        chunk_doc["source_file"] = rewritten_source_file
        rewritten["chunks"].append(chunk_doc)
    return rewritten


def _rewrite_source_file(
    *,
    entity: dict[str, Any],
    rewritten_source_file: str,
) -> dict[str, Any]:
    rewritten = dict(entity)
    if rewritten.get("source_file") is not None:
        rewritten["source_file"] = rewritten_source_file
    return rewritten


def _build_trigger_registry(skill_seed_specs: list[dict[str, Any]]) -> dict[str, Any]:
    trigger_entries = []
    seen_symbols: set[str] = set()
    for spec in skill_seed_specs:
        title = spec["title"]
        trigger = spec["contract"]["trigger"]
        boundary = spec["contract"]["boundary"]
        definitions = {
            trigger["patterns"][0]: f"Use {title} when the scenario clearly matches its core decision pattern.",
            trigger["patterns"][1]: f"Use {title} when the scenario is inside the active decision window for this principle.",
            trigger["exclusions"][0]: f"Do not use {title} when the scenario is clearly outside its intended boundary.",
            boundary["fails_when"][0]: f"Abort {title} when source evidence for the scenario conflicts with the principle.",
            boundary["do_not_fire_when"][0]: f"Do not fire {title} when the scenario is missing required context or inputs.",
        }
        for symbol, definition in definitions.items():
            if symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)
            trigger_entries.append(
                {
                    "symbol": symbol,
                    "definition": definition,
                    "positive_examples": [definition],
                    "negative_examples": [f"Scenario does not satisfy `{symbol}`."],
                }
            )
    return {"triggers": trigger_entries}


def _collect_descriptors(
    *,
    bundle_root: Path,
    node: dict[str, Any],
    node_map: dict[str, dict[str, Any]],
    adjacency: dict[str, list[dict[str, Any]]],
    candidate_id: str,
) -> list[dict[str, str]]:
    descriptors = [_descriptor_from_node(bundle_root=bundle_root, node=node, candidate_id=candidate_id)]
    evidence_nodes = []
    context_nodes = []
    for edge in adjacency.get(node["id"], []):
        other_id = edge["to"] if edge["from"] == node["id"] else edge["from"]
        other = node_map.get(other_id)
        if not other:
            continue
        if other.get("type") == "chunk_evidence":
            evidence_nodes.append(other)
        elif other.get("type") in {"framework_signal", "source_section"}:
            context_nodes.append(other)
    for index, support_node in enumerate([*evidence_nodes, *context_nodes][:3], start=1):
        descriptor = _descriptor_from_node(
            bundle_root=bundle_root,
            node=support_node,
            candidate_id=candidate_id,
        )
        descriptor["rank"] = str(index)
        descriptors.append(descriptor)
    return descriptors


def _descriptor_from_node(
    *,
    bundle_root: Path,
    node: dict[str, Any],
    candidate_id: str,
) -> dict[str, str]:
    relative_path = str(node.get("source_file", ""))
    source_location = node.get("source_location", {}) or {}
    line_start = int(source_location.get("line_start", 1) or 1)
    line_end = int(source_location.get("line_end", line_start) or line_start)
    snippet = _read_snippet(
        bundle_root=bundle_root,
        relative_path=relative_path,
        line_start=line_start,
        line_end=line_end,
    )
    return {
        "anchor_id": f"{candidate_id}-{node['id']}",
        "node_id": node["id"],
        "label": str(node.get("label", node["id"])),
        "snippet": snippet or str(node.get("label", node["id"])),
        "path": relative_path,
        "line_start": str(line_start),
        "line_end": str(line_end),
    }


def _build_seed_contract(candidate_id: str) -> dict[str, Any]:
    symbol_root = candidate_id.replace("-", "_")
    return {
        "trigger": {
            "patterns": [
                f"{symbol_root}_needed",
                f"{symbol_root}_decision_window",
            ],
            "exclusions": [f"{symbol_root}_out_of_scope"],
        },
        "intake": {
            "required": [
                {
                    "name": "scenario",
                    "type": "structured",
                    "description": "Scenario summary that may require this principle.",
                },
                {
                    "name": "decision_goal",
                    "type": "string",
                    "description": "The concrete decision, tradeoff, or next action under review.",
                },
                {
                    "name": "current_constraints",
                    "type": "list[string]",
                    "description": "Constraints, missing context, or boundary conditions that could block firing.",
                },
            ]
        },
        "judgment_schema": {
            "output": {
                "type": "structured",
                "schema": {
                    "verdict": "enum[apply|defer|do_not_apply]",
                    "next_action": "string",
                    "confidence": "enum[low|medium|high]",
                },
            },
            "reasoning_chain_required": True,
        },
        "boundary": {
            "fails_when": [f"{symbol_root}_evidence_conflict"],
            "do_not_fire_when": [f"{symbol_root}_scenario_missing"],
        },
    }


def _build_seed_rationale(
    *,
    title: str,
    descriptors: list[dict[str, str]],
    contract: dict[str, Any],
) -> str:
    primary = descriptors[0]
    supporting = descriptors[1:]
    support_text = " ".join(
        (
            f"`{item['label']}` adds operational context through "
            f"\"{item['snippet']}\"[^anchor:{item['anchor_id']}]."
        )
        for item in supporting[:2]
    )
    return (
        f"`{title}` is distilled from the source excerpt "
        f"\"{primary['snippet']}\"[^anchor:{primary['anchor_id']}]. "
        "The draft treats this as a decision-facing principle rather than a thematic summary: "
        "the contract asks for a concrete scenario, a clear decision goal, and explicit constraints "
        "so the skill can judge whether the principle should actively fire, be deferred, or stay out of scope. "
        f"{support_text} "
        f"The boundary remains narrow by design: if `{contract['boundary']['fails_when'][0]}` or "
        f"`{contract['boundary']['do_not_fire_when'][0]}` is true, the skill should not over-claim."
    ).strip()


def _build_seed_evidence_summary(
    *,
    title: str,
    descriptors: list[dict[str, str]],
) -> str:
    primary = descriptors[0]
    supporting = descriptors[1:]
    lines = [
        (
            f"`{title}` is primarily anchored to \"{primary['snippet']}\""
            f"[^anchor:{primary['anchor_id']}]."
        ),
    ]
    for item in supporting[:2]:
        lines.append(
            (
                f"`{item['label']}` preserves neighboring evidence: \"{item['snippet']}\""
                f"[^anchor:{item['anchor_id']}]."
            )
        )
    lines.append(
        "These excerpts remain bound to both `anchors.yaml` and the source-backed graph snapshot."
    )
    return "\n\n".join(lines)


def _build_usage_notes(
    *,
    title: str,
    descriptors: list[dict[str, str]],
) -> list[str]:
    primary = descriptors[0]
    return [
        f"Use `{title}` when the scenario materially resembles the decision pattern in `{primary['label']}`.",
        "Verify the scenario already includes enough concrete context to test the boundary before firing.",
    ]


def _write_trace_doc(
    *,
    bundle_root: Path,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
) -> str:
    trace_id = f"{candidate_id}-source-smoke"
    trace_path = Path("traces") / "canonical" / f"{trace_id}.yaml"
    primary = descriptors[0]
    trace_doc = {
        "trace_id": trace_id,
        "title": f"{title} Smoke Trace",
        "summary": primary["snippet"],
        "scenario_excerpt": primary["snippet"],
        "evidence_anchor_ids": [item["anchor_id"] for item in descriptors[:3]],
        "related_skills": [candidate_id],
    }
    _write_yaml(bundle_root / trace_path, trace_doc)
    return trace_path.as_posix()


def _write_eval_docs(
    *,
    bundle_root: Path,
    candidate_id: str,
    title: str,
    descriptors: list[dict[str, str]],
    contract: dict[str, Any],
) -> dict[str, Any]:
    primary = descriptors[0]
    subsets = {}
    for subset_name, scenario_suffix in (
        ("real_decisions", "real_decision_smoke"),
        ("synthetic_adversarial", "adversarial_smoke"),
        ("out_of_distribution", "ood_smoke"),
    ):
        case_id = f"{candidate_id}-{scenario_suffix}"
        relative_path = Path("evaluation") / subset_name / f"{case_id}.yaml"
        case_doc = {
            "case_id": case_id,
            "skill_id": candidate_id,
            "title": f"{title} {subset_name} smoke case",
            "input_scenario": {
                "scenario": primary["snippet"],
                "decision_goal": f"Decide whether `{title}` should fire.",
                "current_constraints": [
                    f"Confirm `{contract['trigger']['patterns'][0]}` is truly present.",
                ],
            },
            "expected_behavior": {
                "verdict": "apply",
                "minimum_confidence": "medium",
            },
            "evidence_anchor_ids": [item["anchor_id"] for item in descriptors[:3]],
            "evaluation_mode": "auto_smoke_prefill",
        }
        _write_yaml(bundle_root / relative_path, case_doc)
        subsets[subset_name] = {
            "cases": [relative_path.as_posix()],
            "passed": 1,
            "total": 1,
            "threshold": 1.0,
            "status": "under_evaluation",
        }
    return {
        "kiu_test": {
            "trigger_test": "pass",
            "fire_test": "pending",
            "boundary_test": "pass",
        },
        "subsets": subsets,
        "key_failure_modes": [
            f"If `{contract['boundary']['do_not_fire_when'][0]}` remains true, defer the skill instead of firing.",
            f"If `{contract['boundary']['fails_when'][0]}` is observed, treat the evidence as conflicting.",
        ],
        "references": {
            "evaluation_root": "../../../evaluation",
            "prefill_mode": "extraction_smoke",
        },
    }


def _build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if not edge.get("from") or not edge.get("to"):
            continue
        adjacency.setdefault(edge["from"], []).append(edge)
        adjacency.setdefault(edge["to"], []).append(edge)
    return adjacency


def _resolve_source_file(
    *,
    source_file: str,
    source_chunks_path: Path,
) -> Path:
    candidate = Path(source_file)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    repo_candidate = REPO_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    sibling_candidate = source_chunks_path.parent / candidate
    if sibling_candidate.exists():
        return sibling_candidate
    raise FileNotFoundError(f"unable to resolve source file for extraction bundle: {source_file}")


def _read_snippet(
    *,
    bundle_root: Path,
    relative_path: str,
    line_start: int,
    line_end: int,
) -> str:
    path = bundle_root / relative_path
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    excerpt = " ".join(
        line.strip()
        for line in lines[line_start - 1 : line_end]
        if line.strip()
    )
    return excerpt[:220] if len(excerpt) > 220 else excerpt


def _slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text).strip("-").lower()
    normalized = normalized.replace("--", "-")
    return normalized or "extraction-candidate"


def _humanize_title(raw: str) -> str:
    text = raw.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in text.split()) or raw


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
