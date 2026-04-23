from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import SourceBundle, SourceSkill
from .profile_resolver import resolve_profile


def load_source_bundle(
    bundle_path: str | Path,
    profile_override: str | Path | None = None,
) -> SourceBundle:
    root = Path(bundle_path)
    manifest = _load_yaml(root / "manifest.yaml")
    graph_doc = json.loads((root / manifest["graph"]["path"]).read_text(encoding="utf-8"))
    if profile_override is not None:
        profile = _load_yaml(Path(profile_override))
    else:
        profile = resolve_profile(root)
    skills = {
        entry["skill_id"]: _load_skill(root, entry)
        for entry in manifest.get("skills", [])
    }
    evaluation_cases = _load_evaluation_cases(root)
    return SourceBundle(
        root=root,
        domain=manifest["domain"],
        manifest=manifest,
        graph_doc=graph_doc,
        profile=profile,
        skills=skills,
        evaluation_cases=evaluation_cases,
    )


def _load_skill(bundle_root: Path, entry: dict[str, Any]) -> SourceSkill:
    skill_dir = bundle_root / entry["path"]
    skill_doc = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    sections = parse_sections(skill_doc)
    identity = extract_yaml_section(sections.get("Identity", ""))
    contract = extract_yaml_section(sections.get("Contract", ""))
    relations = extract_yaml_section(sections.get("Relations", ""))
    anchors = _load_yaml(skill_dir / "anchors.yaml")
    eval_summary = _load_yaml(skill_dir / "eval" / "summary.yaml")
    revisions = _load_yaml(skill_dir / "iterations" / "revisions.yaml")
    scenario_families = _load_optional_yaml(skill_dir / "usage" / "scenarios.yaml")
    trace_refs = re.findall(r"traces/[\w./-]+\.yaml", sections.get("Usage Summary", ""))
    return SourceSkill(
        skill_id=entry["skill_id"],
        title=identity.get("title", entry["skill_id"]),
        manifest_entry=entry,
        skill_dir=skill_dir,
        sections=sections,
        identity=identity,
        contract=contract,
        relations=relations,
        anchors=anchors,
        eval_summary=eval_summary,
        revisions=revisions,
        trace_refs=trace_refs,
        scenario_families=scenario_families,
    )


def _load_evaluation_cases(bundle_root: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    evaluation_root = bundle_root / "evaluation"
    for subset_dir in sorted(evaluation_root.iterdir()):
        if not subset_dir.is_dir():
            continue
        for path in sorted(subset_dir.glob("*.yaml")):
            doc = _load_yaml(path)
            doc["_path"] = path
            cases.append(doc)
    return cases


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or {}


def _load_optional_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_yaml(path)


def parse_sections(markdown: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", markdown, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[name] = markdown[start:end].strip()
    return sections


def extract_yaml_section(section_text: str) -> dict[str, Any]:
    match = re.search(r"```ya?ml\n(.*?)```", section_text, flags=re.DOTALL)
    if not match:
        return {}
    loaded = yaml.safe_load(match.group(1))
    return loaded or {}
