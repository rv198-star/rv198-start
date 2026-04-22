from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml

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
    graph_input_path = Path(graph_path)
    output_root = Path(output_root)

    source_chunks_doc = json.loads(source_chunks_input_path.read_text(encoding="utf-8"))
    graph_doc = json.loads(graph_input_path.read_text(encoding="utf-8"))

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

    rewritten_graph_doc = _rewrite_graph_source_paths(
        graph_doc=graph_doc,
        source_snapshot=source_id,
        rewritten_source_file=copied_source_relpath.as_posix(),
    )
    graph_hash = canonical_graph_hash(rewritten_graph_doc)
    rewritten_graph_doc["graph_hash"] = graph_hash
    (bundle_root / "graph" / "graph.json").write_text(
        json.dumps(rewritten_graph_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    persisted_source_chunks = _rewrite_source_chunks_doc(
        source_chunks_doc=source_chunks_doc,
        rewritten_source_file=copied_source_relpath.as_posix(),
    )
    (bundle_root / "ingestion" / "source-chunks-v0.1.json").write_text(
        json.dumps(persisted_source_chunks, ensure_ascii=False, indent=2) + "\n",
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
        _build_trigger_registry(
            graph_doc=rewritten_graph_doc,
            seed_node_types=DEFAULT_SEED_NODE_TYPES,
        ),
    )
    return bundle_root


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


def _build_trigger_registry(
    *,
    graph_doc: dict[str, Any],
    seed_node_types: list[str],
) -> dict[str, Any]:
    trigger_entries = []
    seen_symbols: set[str] = set()
    for node in graph_doc.get("nodes", []):
        if not isinstance(node, dict):
            continue
        if node.get("type") not in seed_node_types:
            continue
        symbol = f"candidate_seed::{node['id']}"
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        humanized = _humanize_title(str(node.get("label", node["id"])))
        trigger_entries.append(
            {
                "symbol": symbol,
                "definition": f"Extraction-derived trigger for {humanized}.",
                "positive_examples": [f"Scenario requires {humanized}."],
                "negative_examples": [f"Scenario does not require {humanized}."],
            }
        )

    for symbol, definition in (
        (
            "evidence_is_too_sparse_for_candidate_review",
            "Candidate evidence is still too sparse to support a stable judgment contract.",
        ),
        (
            "candidate_has_not_been_reviewed_by_human",
            "Candidate has not yet completed human review and boundary confirmation.",
        ),
    ):
        trigger_entries.append(
            {
                "symbol": symbol,
                "definition": definition,
                "positive_examples": [definition],
                "negative_examples": [f"Not {definition.lower()}"],
            }
        )
    return {"triggers": trigger_entries}


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


def _humanize_title(raw: str) -> str:
    text = raw.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in text.split()) or raw


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
