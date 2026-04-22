from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def scaffold_example_bundle(
    *,
    fixture_path: str | Path,
    output_root: str | Path,
) -> Path:
    fixture_path = Path(fixture_path)
    output_root = Path(output_root)
    fixture = _load_yaml(fixture_path)

    fixture_id = fixture["fixture_id"]
    title = fixture.get("title", fixture_id)
    domain = fixture["domain"]
    language = fixture.get("language", "zh-CN")
    bundle_version = fixture.get("bundle_version", "0.1.0")
    source_markdown = _resolve_repo_path(fixture["source_markdown"])

    bundle_root = output_root / "bundle"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)

    (bundle_root / "graph").mkdir(parents=True, exist_ok=True)
    (bundle_root / "skills").mkdir(parents=True, exist_ok=True)
    (bundle_root / "traces" / "canonical").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "real_decisions").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "synthetic_adversarial").mkdir(parents=True, exist_ok=True)
    (bundle_root / "evaluation" / "out_of_distribution").mkdir(parents=True, exist_ok=True)
    (bundle_root / "sources").mkdir(parents=True, exist_ok=True)

    copied_source_relpath = Path("sources") / source_markdown.name
    shutil.copy2(source_markdown, bundle_root / copied_source_relpath)

    graph_doc = _build_graph_doc(
        fixture=fixture,
        source_relpath=copied_source_relpath.as_posix(),
        bundle_root=bundle_root,
    )
    graph_hash = _canonical_graph_hash(graph_doc)
    graph_doc["graph_hash"] = graph_hash
    (bundle_root / "graph" / "graph.json").write_text(
        json.dumps(graph_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "bundle_id": f"{fixture_id}-source-v0.1",
        "title": title,
        "bundle_version": bundle_version,
        "schema_version": "kiu.bundle.schema/v0.1",
        "skill_spec_version": "kiu.skill-spec/v0.1",
        "relation_enum_version": "kiu.relation-enum/v1",
        "language": language,
        "domain": domain,
        "created_at": date.today().isoformat(),
        "graph": {
            "path": "graph/graph.json",
            "graph_version": graph_doc["graph_version"],
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
    _write_yaml(bundle_root / "automation.yaml", _build_automation_doc(fixture))
    _write_yaml(bundle_root / "triggers.yaml", _build_trigger_registry(fixture))
    _write_yaml(
        bundle_root / "materials.yaml",
        {
            "fixture_id": fixture_id,
            "materials": [
                {
                    "source_id": fixture_id,
                    "kind": "markdown_document",
                    "original_path": source_markdown.as_posix(),
                    "bundle_path": copied_source_relpath.as_posix(),
                    "line_count": len(
                        (bundle_root / copied_source_relpath)
                        .read_text(encoding="utf-8")
                        .splitlines()
                    ),
                }
            ],
        },
    )
    return bundle_root


def _build_graph_doc(
    *,
    fixture: dict[str, Any],
    source_relpath: str,
    bundle_root: Path,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    for node in fixture.get("nodes", []):
        node_doc = {
            "id": node["id"],
            "type": node.get("type", "skill_principle"),
            "label": node["label"],
            "source_anchor": {
                "kind": node.get("source_anchor_kind", "source_excerpt"),
                "path": source_relpath,
                "line_start": int(node["line_start"]),
                "line_end": int(node["line_end"]),
                "provenance_status": node.get("provenance_status", "EXTRACTED"),
            },
        }
        skill_seed = _materialize_skill_seed(
            bundle_root=bundle_root,
            candidate_id=node["candidate_id"],
            raw_seed=node.get("skill_seed"),
        )
        if skill_seed:
            node_doc["skill_seed"] = skill_seed
        nodes.append(
            node_doc
        )
    return {
        "graph_version": "kiu.graph/v0.1",
        "source_snapshot": fixture["fixture_id"],
        "nodes": nodes,
        "edges": list(fixture.get("edges", [])),
        "communities": list(fixture.get("communities", [])),
    }


def _build_automation_doc(fixture: dict[str, Any]) -> dict[str, Any]:
    seed_overrides = {}
    for node in fixture.get("nodes", []):
        override = {
            "candidate_id": node["candidate_id"],
        }
        if node.get("gold_match_hint"):
            override["gold_match_hint"] = node["gold_match_hint"]
        seed_overrides[node["id"]] = override

    automation = {
        "profile_version": "kiu.pipeline-profile/v0.3",
        "inherits": fixture.get("inherits", "default"),
        "trigger_registry": "triggers.yaml",
        "seed_overrides": seed_overrides,
    }
    if fixture.get("candidate_kinds"):
        automation["candidate_kinds"] = fixture["candidate_kinds"]
    if fixture.get("routing_rules"):
        automation["routing_rules"] = fixture["routing_rules"]
    return automation


def _build_trigger_registry(fixture: dict[str, Any]) -> dict[str, Any]:
    trigger_entries = []
    seen_symbols: set[str] = set()
    for node in fixture.get("nodes", []):
        contract = node.get("skill_seed", {}).get("contract", {})
        symbols = _collect_contract_symbols(contract)
        if not symbols:
            symbols = [f"candidate_seed::{node['id']}"]
        for symbol in symbols:
            if symbol in seen_symbols:
                continue
            seen_symbols.add(symbol)
            humanized = _humanize_symbol(symbol)
            trigger_entries.append(
                {
                    "symbol": symbol,
                    "definition": f"Fixture trigger for {humanized}.",
                    "positive_examples": [f"Scenario matches {humanized}."],
                    "negative_examples": [f"Scenario does not match {humanized}."],
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


def _materialize_skill_seed(
    *,
    bundle_root: Path,
    candidate_id: str,
    raw_seed: dict[str, Any] | None,
) -> dict[str, Any]:
    if not raw_seed:
        return {}
    skill_seed = deepcopy(raw_seed)

    trace_refs: list[str] = []
    for trace_doc in skill_seed.pop("traces", []):
        trace_id = trace_doc["trace_id"]
        trace_path = Path("traces") / "canonical" / f"{trace_id}.yaml"
        persisted_trace = dict(trace_doc)
        persisted_trace.setdefault("related_skills", [candidate_id])
        _write_yaml(bundle_root / trace_path, persisted_trace)
        trace_refs.append(trace_path.as_posix())
    if trace_refs:
        skill_seed["trace_refs"] = trace_refs

    eval_cases = skill_seed.pop("evaluation_cases", {})
    eval_prefill = skill_seed.pop("eval_prefill", {})
    if eval_cases or eval_prefill:
        skill_seed["eval_summary"] = _materialize_eval_summary(
            bundle_root=bundle_root,
            candidate_id=candidate_id,
            eval_cases=eval_cases,
            eval_prefill=eval_prefill,
        )

    skill_seed.setdefault(
        "relations",
        {
            "depends_on": [],
            "delegates_to": [],
            "constrained_by": [],
            "complements": [],
            "contradicts": [],
        },
    )
    return skill_seed


def _materialize_eval_summary(
    *,
    bundle_root: Path,
    candidate_id: str,
    eval_cases: dict[str, list[dict[str, Any]]],
    eval_prefill: dict[str, Any],
) -> dict[str, Any]:
    subsets: dict[str, Any] = {}
    subset_prefill = eval_prefill.get("subsets", {})
    for subset_name in (
        "real_decisions",
        "synthetic_adversarial",
        "out_of_distribution",
    ):
        case_refs: list[str] = []
        for case_doc in eval_cases.get(subset_name, []):
            case_id = case_doc["case_id"]
            case_path = Path("evaluation") / subset_name / f"{case_id}.yaml"
            persisted_case = dict(case_doc)
            persisted_case.setdefault("subset", subset_name)
            persisted_case.setdefault("primary_skill", candidate_id)
            persisted_case.setdefault("related_skills", [])
            _write_yaml(bundle_root / case_path, persisted_case)
            case_refs.append((Path("..") / ".." / ".." / case_path).as_posix())

        prefill_doc = subset_prefill.get(subset_name, {})
        subsets[subset_name] = {
            "cases": case_refs,
            "passed": prefill_doc.get("passed", 0),
            "total": len(case_refs),
            "threshold": prefill_doc.get("threshold", 0.0),
            "status": prefill_doc.get("status", "pending"),
        }

    return {
        "kiu_test": {
            "trigger_test": eval_prefill.get("kiu_test", {}).get("trigger_test", "pending"),
            "fire_test": eval_prefill.get("kiu_test", {}).get("fire_test", "pending"),
            "boundary_test": eval_prefill.get("kiu_test", {}).get("boundary_test", "pending"),
        },
        "subsets": subsets,
        "key_failure_modes": eval_prefill.get(
            "key_failure_modes",
            ["Fixture seed still needs more evaluation depth before publication."],
        ),
        "references": {
            "evaluation_root": "../../../evaluation",
            "coverage_mode": "fixture_seed_cases",
            "prefill_source": "example_fixture",
        },
    }


def _collect_contract_symbols(contract: dict[str, Any]) -> list[str]:
    symbols: list[str] = []
    trigger = contract.get("trigger", {})
    boundary = contract.get("boundary", {})
    for field_name in ("patterns", "exclusions"):
        for symbol in trigger.get(field_name, []):
            if isinstance(symbol, str):
                symbols.append(symbol)
    for field_name in ("fails_when", "do_not_fire_when"):
        for symbol in boundary.get(field_name, []):
            if isinstance(symbol, str):
                symbols.append(symbol)
    return symbols


def _humanize_symbol(symbol: str) -> str:
    return symbol.replace("::", " ").replace("_", " ")


def _canonical_graph_hash(graph_doc: dict[str, Any]) -> str:
    canonical_doc = dict(graph_doc)
    canonical_doc.pop("graph_hash", None)
    encoded = json.dumps(canonical_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _resolve_repo_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    primary = REPO_ROOT / path
    if primary.exists():
        return primary
    if REPO_ROOT.parent.name == ".worktrees":
        fallback = REPO_ROOT.parent.parent / path
        if fallback.exists():
            return fallback
    return primary


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
