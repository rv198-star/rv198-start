from __future__ import annotations

from copy import deepcopy
import shutil
import tempfile
from pathlib import Path
import re
from typing import Any

from ..models import SourceBundle
from ..preflight import validate_generated_bundle
from .providers import LLMProvider, estimate_tokens


PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"


class LLMBudgetTracker:
    def __init__(self, max_tokens: int | None = None) -> None:
        self.max_tokens = max_tokens
        self.spent_tokens = 0

    @property
    def remaining_tokens(self) -> int | None:
        if self.max_tokens is None:
            return None
        return self.max_tokens - self.spent_tokens

    def can_afford(self, estimated_tokens: int) -> bool:
        if self.max_tokens is None:
            return True
        return self.spent_tokens + estimated_tokens <= self.max_tokens

    def consume(self, total_tokens: int) -> None:
        self.spent_tokens += total_tokens


def apply_llm_drafting(
    *,
    candidate: dict[str, Any],
    source_bundle: SourceBundle,
    run_root: str | Path,
    round_index: int,
    llm_provider: LLMProvider,
    budget_tracker: LLMBudgetTracker,
) -> tuple[dict[str, Any], dict[str, Any], list[str], str | None]:
    field_name = "Rationale"
    prompt_path = PROMPTS_ROOT / "rationale.md"
    prompt = _render_rationale_prompt(
        template=prompt_path.read_text(encoding="utf-8"),
        candidate=candidate,
        source_bundle=source_bundle,
        round_index=round_index,
    )

    estimated_total_tokens = estimate_tokens(prompt) + 256
    if not budget_tracker.can_afford(estimated_total_tokens):
        llm_doc = {
            "provider": llm_provider.provider_name,
            "model": llm_provider.model_name,
            "field": field_name,
            "prompt_path": str(prompt_path),
            "prompt": prompt,
            "response": None,
            "usage": {
                "estimated_total_tokens": estimated_total_tokens,
                "spent_tokens": budget_tracker.spent_tokens,
                "remaining_tokens": budget_tracker.remaining_tokens,
            },
            "accepted": False,
            "status": "budget_exhausted",
        }
        return (
            candidate,
            llm_doc,
            [
                f"{candidate['candidate']['candidate_id']}: llm_budget_exhausted "
                f"(estimated={estimated_total_tokens}, remaining={budget_tracker.remaining_tokens})"
            ],
            "llm_budget_exhausted",
        )

    response = llm_provider.generate(
        field_name=field_name,
        prompt=prompt,
    )
    total_tokens = response.prompt_tokens + response.completion_tokens
    budget_tracker.consume(total_tokens)

    proposed = deepcopy(candidate)
    proposed["skill_markdown"] = _replace_section(
        proposed["skill_markdown"],
        field_name,
        response.content,
    )

    rejections = _precheck_candidate_draft(
        candidate=proposed,
        run_root=run_root,
        field_name=field_name,
    )
    llm_doc = {
        "provider": response.provider,
        "model": response.model,
        "field": field_name,
        "prompt_path": str(prompt_path),
        "prompt": prompt,
        "response": response.content,
        "usage": {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": total_tokens,
            "spent_tokens": budget_tracker.spent_tokens,
            "remaining_tokens": budget_tracker.remaining_tokens,
        },
        "accepted": not rejections,
        "status": "accepted" if not rejections else "rejected",
    }
    if rejections:
        return candidate, llm_doc, rejections, None
    return proposed, llm_doc, [], None


def _render_rationale_prompt(
    *,
    template: str,
    candidate: dict[str, Any],
    source_bundle: SourceBundle,
    round_index: int,
) -> str:
    skill_id = candidate["candidate"]["candidate_id"]
    source_skill = source_bundle.skills.get(skill_id)
    title = source_skill.title if source_skill else skill_id.replace("-", " ").title()
    density = source_bundle.profile.get("content_density", {}).get("rationale", {})
    current_rationale = _extract_section(candidate["skill_markdown"], "Rationale")
    evidence_summary = _extract_section(candidate["skill_markdown"], "Evidence Summary")
    usage_summary = _extract_section(candidate["skill_markdown"], "Usage Summary")
    trace_refs = source_skill.trace_refs if source_skill else []
    anchors = source_skill.anchors if source_skill else {}
    source_anchors = anchors.get("source_anchor_sets", [])
    graph_anchors = anchors.get("graph_anchor_sets", [])

    replacements = {
        "skill_id": skill_id,
        "title": title,
        "round_index": str(round_index),
        "min_chars": str(density.get("warning_min_chars", 180)),
        "min_anchor_refs": str(density.get("min_anchor_refs", 1)),
        "current_rationale": current_rationale,
        "evidence_summary": evidence_summary,
        "usage_summary": usage_summary,
        "source_anchor_list": "\n".join(
            f"- {anchor.get('anchor_id')}: {anchor.get('kind')} @ {anchor.get('path')}:{anchor.get('line_start')}-{anchor.get('line_end')}"
            for anchor in source_anchors
        )
        or "- none",
        "graph_anchor_list": "\n".join(
            f"- {anchor.get('anchor_id')}: nodes={anchor.get('node_ids', [])}, edges={anchor.get('edge_ids', [])}, communities={anchor.get('community_ids', [])}"
            for anchor in graph_anchors
        )
        or "- none",
        "trace_ref_list": "\n".join(f"- {trace_ref}" for trace_ref in trace_refs) or "- none",
    }

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _extract_section(markdown: str, section_name: str) -> str:
    match = re.search(
        rf"## {re.escape(section_name)}\n(.*?)(?:\n## |\Z)",
        markdown,
        re.DOTALL,
    )
    if not match:
        return ""
    return match.group(1).strip()


def _replace_section(markdown: str, section_name: str, replacement: str) -> str:
    pattern = rf"(## {re.escape(section_name)}\n)(.*?)(?=\n## |\Z)"
    match = re.search(pattern, markdown, re.DOTALL)
    if not match:
        return markdown.rstrip() + f"\n\n## {section_name}\n{replacement.strip()}\n"
    return re.sub(
        pattern,
        lambda item: item.group(1) + replacement.strip() + "\n",
        markdown,
        count=1,
        flags=re.DOTALL,
    )


def _precheck_candidate_draft(
    *,
    candidate: dict[str, Any],
    run_root: str | Path,
    field_name: str,
) -> list[str]:
    skill_id = candidate["candidate"]["candidate_id"]
    skill_dir = candidate.get("skill_dir")
    if skill_dir is None:
        return [f"{skill_id}: llm_precheck_missing_skill_dir"]

    skill_dir = Path(skill_dir)
    bundle_root = skill_dir.parents[1]
    runtime_root = Path(run_root)

    with tempfile.TemporaryDirectory(dir=runtime_root, prefix="llm-precheck-") as tmp_dir:
        tmp_bundle = Path(tmp_dir) / "bundle"
        shutil.copytree(bundle_root, tmp_bundle)
        manifest_path = tmp_bundle / "manifest.yaml"
        manifest_doc = _load_yaml(manifest_path)
        for entry in manifest_doc.get("skills", []):
            if entry.get("skill_id") == skill_id:
                entry["skill_revision"] = candidate["revisions"]["current_revision"]
                entry["status"] = "under_evaluation"
                break
        _write_yaml(manifest_path, manifest_doc)
        tmp_skill_dir = tmp_bundle / "skills" / skill_id
        tmp_skill_dir.joinpath("SKILL.md").write_text(
            candidate["skill_markdown"],
            encoding="utf-8",
        )
        _write_yaml(tmp_skill_dir / "anchors.yaml", candidate["anchors"])
        _write_yaml(tmp_skill_dir / "eval" / "summary.yaml", candidate["eval_summary"])
        _write_yaml(tmp_skill_dir / "iterations" / "revisions.yaml", candidate["revisions"])
        _write_yaml(tmp_skill_dir / "candidate.yaml", candidate["candidate"])

        report = validate_generated_bundle(tmp_bundle)

    rejections = [
        item
        for item in report.get("errors", [])
        if item.startswith(f"{skill_id}:") or item.startswith("bundle:")
    ]
    if field_name == "Rationale":
        rejections.extend(
            warning
            for warning in report.get("warnings", [])
            if warning.startswith(f"{skill_id}: rationale_below_density_threshold")
        )
    return rejections


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    import yaml

    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
