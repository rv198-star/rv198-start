from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SourceSkill:
    skill_id: str
    title: str
    manifest_entry: dict[str, Any]
    skill_dir: Path
    sections: dict[str, str]
    identity: dict[str, Any]
    contract: dict[str, Any]
    relations: dict[str, Any]
    anchors: dict[str, Any]
    eval_summary: dict[str, Any]
    revisions: dict[str, Any]
    trace_refs: list[str]
    scenario_families: dict[str, Any]


@dataclass
class SourceBundle:
    root: Path
    domain: str
    manifest: dict[str, Any]
    graph_doc: dict[str, Any]
    profile: dict[str, Any]
    skills: dict[str, SourceSkill]
    evaluation_cases: list[dict[str, Any]]


@dataclass
class NormalizedGraph:
    doc: dict[str, Any]
    nodes: dict[str, dict[str, Any]]
    edges: dict[str, dict[str, Any]]
    adjacency: dict[str, list[dict[str, Any]]]
    communities: dict[str, dict[str, Any]]


@dataclass
class CandidateSeed:
    candidate_id: str
    candidate_kind: str
    primary_node_id: str
    supporting_node_ids: list[str]
    supporting_edge_ids: list[str]
    community_ids: list[str]
    gold_match_hint: str | None
    source_skill: SourceSkill | None
    score: int
    metadata: dict[str, Any]
    seed_content: dict[str, Any]
