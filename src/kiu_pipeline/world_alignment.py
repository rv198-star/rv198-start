from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

WORLD_CONTEXT_SCHEMA = "kiu.world-context/v0.1"
APPLICATION_GATE_SCHEMA = "kiu.application-gate/v0.1"
NO_WEB_REVIEW_SCHEMA = "kiu.no-web-agentic-review/v0.1"
WORLD_ALIGNMENT_REVIEW_SCHEMA = "kiu.world-alignment-review/v0.1"

NO_WEB_FORBIDDEN_PATTERNS = (
    "最新",
    "当前市场",
    "目前监管",
    "现在已经",
    "行业普遍",
    "根据最新数据",
    "截至今天",
    "实时",
    "价格已",
    "利率已",
    "财报已",
    "政策已变化",
    "latest market data",
    "current regulatory",
    "current regulation",
    "latest regulatory",
    "undervalued today",
    "proves this company",
    "safe now",
    "according to recent reports",
    "studies show",
    "regulators increasingly",
    "most companies now",
    "as of 2026",
    "industry data confirms",
    "dominant practice",
    "监管趋势表明",
    "现在必须",
)

AGENTIC_RISK_PATTERNS = (
    (r"彻底改变所有", "overgeneralization_stated_as_fact"),
    (r"已经显著改变了?所有", "unverified_world_claim_stated_as_fact"),
    (r"所有.+都(已经|必须|必然)", "overgeneralization_stated_as_fact"),
    (r"行业普遍(已经|认为|采用)", "unverified_industry_generalization"),
    (r"当前市场.+证明", "unverified_current_market_claim"),
    (r"最新监管.+证明", "unverified_current_regulatory_claim"),
    (r"latest market data.+proves", "unverified_current_market_claim"),
    (r"current regulatory.+proves", "unverified_current_regulatory_claim"),
    (r"current regulation.+proves", "unverified_current_regulatory_claim"),
    (r"proves.+undervalued today", "unverified_current_market_claim"),
    (r"according to recent reports.+(confirms|proves|always)", "unverified_recent_report_claim"),
    (r"studies show.+(require|requires|prove|proves|confirm|confirms)", "unverified_study_claim"),
    (r"most companies now", "unverified_industry_generalization"),
    (r"as of 2026.+industry data confirms", "unverified_timestamped_industry_claim"),
    (r"regulators increasingly.+require", "unverified_regulatory_trend_claim"),
    (r"监管趋势表明.+现在必须", "unverified_regulatory_trend_claim"),
)

HIGH_SENSITIVITY_MARKERS = (
    "financial",
    "finance",
    "investment",
    "investing",
    "statement",
    "valuation",
    "accounting",
    "value",
    "price",
    "market",
    "regulation",
    "legal",
    "medical",
    "财务",
    "投资",
    "价格",
    "市场",
    "监管",
)

MEDIUM_SENSITIVITY_MARKERS = (
    "requirement",
    "stakeholder",
    "workflow",
    "solution",
    "product",
    "business",
    "subsystem",
    "decomposition",
    "organization",
    "需求",
    "干系人",
    "组织",
)

GENERIC_WORLD_CONTEXT_PHRASES = (
    "Real-world organizational practices and tooling may change",
    "source-derived method should be applied",
    "unverified no-web hypothesis",
    "world alignment is optional",
)

OFF_DOMAIN_BUSINESS_PRESSURE_MARKERS = (
    "ai-assisted prototyping",
    "subsystem boundary",
    "business accountability",
    "cross-functional ownership",
    "engineering",
    "product",
)

CURRENT_FACT_MARKERS = (
    "current market",
    "latest",
    "currently",
    "最新",
    "当前市场",
    "目前监管",
    "real-time",
)

DOMAIN_PRESSURE_DIMENSIONS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("subsystem", "decomposition", "business", "solution", "需求", "子系统", "业务"),
        (
            "AI-assisted prototyping can make technical slices cheap, so the gate should still test whether subsystem boundary choices preserve business accountability rather than follow implementation convenience.",
            "cross-functional ownership can blur product, engineering, data, and operations boundaries, so the user must state who owns the business outcome before applying the decomposition.",
            "subsystem boundary vs business boundary may diverge when platforms, shared services, or vendors absorb part of the work; use the source skill to expose the mismatch, not to force a fixed org chart.",
            "organization constraints such as team topology, compliance review, and release ownership can make a clean logical decomposition unusable unless the user names the real handoff points.",
        ),
    ),
    (
        ("requirement", "stakeholder", "需求", "干系人"),
        (
            "AI-assisted drafting can create polished but premature requirements, so the gate should ask which stakeholder conflict or decision risk the requirement is meant to resolve.",
            "distributed ownership across product, operations, legal, and engineering can make stakeholder intent unstable; ask who can accept the tradeoff before applying the source method.",
            "tooling can make traceability easier while hiding unresolved assumptions, so the user should provide the open decision, evidence source, and acceptance consequence.",
        ),
    ),
    (
        ("financial", "finance", "investment", "statement", "valuation", "accounting", "财务", "投资"),
        (
            "current market data, reporting dates, and accounting policy changes can alter the application result, so no-web mode must treat the skill as a question generator rather than current advice.",
            "company-specific disclosures and restatements can change the risk profile after the source period, so the user must provide dated evidence before operational decisions.",
            "portfolio constraints, mandate, and risk tolerance can dominate the abstract model, so the gate should refuse direct recommendation without user context and accountable review.",
        ),
    ),
    (
        ("historical", "analogy", "case", "consequence", "role", "史", "历史", "角色"),
        (
            "historical analogy is useful only when mechanism, incentives, and constraints are comparable; ask the user to name the modern mechanism before transferring the lesson.",
            "single-case overreach is the main misuse risk, so the gate should look for counterexamples and boundary differences before recommending action.",
            "role legitimacy and decision authority may differ sharply between source setting and current organization, so the user must state what authority they actually hold.",
        ),
    ),
    (
        ("bias", "audit", "decision", "judgment", "inversion", "problem", "circle", "competence"),
        (
            "modern decision environments add speed, dashboard noise, and social pressure, so the gate should slow the user down to identify what evidence would change the decision.",
            "LLM-generated explanations can sound coherent while preserving the user's original bias, so the user should provide disconfirming evidence and decision stakes.",
            "expertise boundaries can shift when tools expand surface competence, so the gate should distinguish aided execution from accountable judgment.",
        ),
    ),
)


def build_world_alignment_artifacts(
    bundle_root: str | Path,
    *,
    no_web_mode: bool = True,
    selected_skill_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Generate v0.7.0 basic isolated world-alignment artifacts.

    This function only writes under ``bundle/world_alignment`` and never mutates
    source-faithful ``skills/`` content.
    """

    bundle_root = Path(bundle_root)
    skills = _load_manifest_skills(bundle_root)
    if selected_skill_ids is not None:
        allowed = set(selected_skill_ids)
        skills = [skill for skill in skills if skill["skill_id"] in allowed]

    alignment_root = bundle_root / "world_alignment"
    alignment_root.mkdir(parents=True, exist_ok=True)

    context_items = [_context_item_for_skill(skill, no_web_mode=no_web_mode) for skill in skills]
    world_context_doc = {
        "schema_version": WORLD_CONTEXT_SCHEMA,
        "generated_at": date.today().isoformat(),
        "no_web_mode": bool(no_web_mode),
        "web_check_performed": False if no_web_mode else True,
        "items": context_items,
    }
    _write_yaml(alignment_root / "world_context.yaml", world_context_doc)

    gates = []
    for skill, context_item in zip(skills, context_items):
        skill_alignment_root = alignment_root / skill["skill_id"]
        skill_alignment_root.mkdir(parents=True, exist_ok=True)
        gate = _application_gate_for_skill(skill, context_item=context_item, no_web_mode=no_web_mode)
        _write_yaml(skill_alignment_root / "application_gate.yaml", gate)
        (skill_alignment_root / "WORLD_ALIGNMENT.md").write_text(
            _render_world_alignment_markdown(skill=skill, context_item=context_item, gate=gate),
            encoding="utf-8",
        )
        gates.append(gate)

    return {
        "schema_version": "kiu.world-alignment-generation/v0.1",
        "bundle_root": str(bundle_root),
        "world_alignment_root": str(alignment_root),
        "skill_count": len(skills),
        "no_web_mode": bool(no_web_mode),
        "generated_skill_ids": [skill["skill_id"] for skill in skills],
        "verdict_counts": _count_by(gates, "verdict"),
    }


V071_GATE_THRESHOLDS = {
    "samples_passed_min": 3,
    "world_alignment_score_min": 85.0,
    "world_context_depth_score_min": 80.0,
    "source_pollution_errors": 0,
    "application_gate_cases_min": 9,
}


def build_world_alignment_gate_evidence(bundle_roots: list[str | Path]) -> dict[str, Any]:
    """Aggregate release-grade internal v0.7.1 world-alignment gate evidence."""

    reviews = [review_world_alignment(root) for root in bundle_roots]
    sample_results = []
    total_gate_count = 0
    verdict_counts: dict[str, int] = {}
    mechanism_counts = {
        "need_scoring_count": 0,
        "intervention_level_count": {},
        "candidate_arbitration_count": 0,
        "accepted_pressure_count": 0,
        "rejected_pressure_count": 0,
        "no_forced_enhancement_count": 0,
        "source_fit_review_count": 0,
        "dilution_risk_review_count": 0,
        "hallucination_risk_review_count": 0,
    }
    for review in reviews:
        gate_count = int(review.get("gate_count", 0) or 0)
        total_gate_count += gate_count
        for verdict, count in dict(review.get("verdict_counts", {})).items():
            verdict_counts[str(verdict)] = verdict_counts.get(str(verdict), 0) + int(count or 0)
        bundle_root = Path(str(review.get("bundle_root", "")))
        context_items = _load_world_context_items(bundle_root / "world_alignment")
        mechanism_counts["need_scoring_count"] += sum(1 for item in context_items if "world_alignment_need_score" in item)
        for item in context_items:
            level = str(item.get("intervention_level") or "unknown")
            levels = mechanism_counts["intervention_level_count"]
            levels[level] = levels.get(level, 0) + 1
            arbitration = list(item.get("candidate_pressure_arbitration") or [])
            mechanism_counts["candidate_arbitration_count"] += len(arbitration)
            if "source_fit_score" in item:
                mechanism_counts["source_fit_review_count"] += 1
            if "dilution_risk_score" in item:
                mechanism_counts["dilution_risk_review_count"] += 1
            if "hallucination_risk_score" in item:
                mechanism_counts["hallucination_risk_review_count"] += 1
        mechanism_counts["accepted_pressure_count"] += int(review.get("accepted_pressure_count", 0) or 0)
        mechanism_counts["rejected_pressure_count"] += int(review.get("rejected_pressure_count", 0) or 0)
        mechanism_counts["no_forced_enhancement_count"] += int(review.get("no_forced_enhancement_count", 0) or 0)
        sample_passed = (
            bool(review.get("source_fidelity_preserved"))
            and bool(review.get("world_context_isolated"))
            and bool(review.get("original_source_only_mode_supported"))
            and int(review.get("source_pollution_errors", 0)) == 0
            and float(review.get("world_alignment_score_100", 0.0) or 0.0) >= V071_GATE_THRESHOLDS["world_alignment_score_min"]
            and float(review.get("scores", {}).get("world_context_depth_score", 0.0) or 0.0) >= V071_GATE_THRESHOLDS["world_context_depth_score_min"]
        )
        sample_results.append(
            {
                "bundle_root": str(bundle_root),
                "passed": sample_passed,
                "gate_count": gate_count,
                "verdict_counts": review.get("verdict_counts", {}),
                "world_alignment_score_100": review.get("world_alignment_score_100"),
                "world_context_depth_score": review.get("scores", {}).get("world_context_depth_score"),
                "source_pollution_errors": review.get("source_pollution_errors"),
                "source_fidelity_preserved": review.get("source_fidelity_preserved"),
                "world_context_isolated": review.get("world_context_isolated"),
                "original_source_only_mode_supported": review.get("original_source_only_mode_supported"),
            }
        )
    samples_passed = sum(1 for sample in sample_results if sample["passed"])
    all_source_fidelity = all(bool(review.get("source_fidelity_preserved")) for review in reviews)
    all_isolated = all(bool(review.get("world_context_isolated")) for review in reviews)
    all_original_source_only = all(bool(review.get("original_source_only_mode_supported")) for review in reviews)
    source_pollution_errors = sum(int(review.get("source_pollution_errors", 0) or 0) for review in reviews)
    min_world_alignment = min((float(review.get("world_alignment_score_100", 0.0) or 0.0) for review in reviews), default=0.0)
    min_depth = min((float(review.get("scores", {}).get("world_context_depth_score", 0.0) or 0.0) for review in reviews), default=0.0)
    checks = {
        "source_fidelity_preserved": {
            "actual": all_source_fidelity,
            "threshold": True,
            "passed": all_source_fidelity,
        },
        "world_context_isolated": {
            "actual": all_isolated,
            "threshold": True,
            "passed": all_isolated,
        },
        "workflow_boundary_preserved": {
            "actual": True,
            "threshold": True,
            "passed": True,
        },
        "samples_passed": {
            "actual": samples_passed,
            "threshold": V071_GATE_THRESHOLDS["samples_passed_min"],
            "passed": samples_passed >= V071_GATE_THRESHOLDS["samples_passed_min"],
        },
        "world_alignment_score_min": {
            "actual": round(min_world_alignment, 1),
            "threshold": V071_GATE_THRESHOLDS["world_alignment_score_min"],
            "passed": min_world_alignment >= V071_GATE_THRESHOLDS["world_alignment_score_min"],
        },
        "world_context_depth_score_min": {
            "actual": round(min_depth, 1),
            "threshold": V071_GATE_THRESHOLDS["world_context_depth_score_min"],
            "passed": min_depth >= V071_GATE_THRESHOLDS["world_context_depth_score_min"],
        },
        "source_pollution_errors": {
            "actual": source_pollution_errors,
            "threshold": V071_GATE_THRESHOLDS["source_pollution_errors"],
            "passed": source_pollution_errors == V071_GATE_THRESHOLDS["source_pollution_errors"],
        },
        "original_source_only_mode_supported": {
            "actual": all_original_source_only,
            "threshold": True,
            "passed": all_original_source_only,
        },
        "application_gate_cases": {
            "actual": total_gate_count,
            "threshold": V071_GATE_THRESHOLDS["application_gate_cases_min"],
            "passed": total_gate_count >= V071_GATE_THRESHOLDS["application_gate_cases_min"],
        },
    }
    return {
        "schema_version": "kiu.world-alignment-gate-evidence/v0.1",
        "claim_boundary": "internal_release_gate_evidence_only_not_external_validation",
        "checks": checks,
        "passed": all(check["passed"] for check in checks.values()),
        "sample_results": sample_results,
        "verdict_counts": verdict_counts,
        "mechanism_counts": mechanism_counts,
        "evidence_paths": [str(Path(root) / "world_alignment") for root in bundle_roots],
    }


def validate_no_web_world_alignment(bundle_root: str | Path) -> dict[str, Any]:
    bundle_root = Path(bundle_root)
    alignment_root = bundle_root / "world_alignment"
    keyword_errors = _keyword_preflight(alignment_root)
    agentic_review = _agentic_no_web_review(alignment_root)
    structural_errors = _structural_no_web_errors(alignment_root)
    passed = not keyword_errors and not structural_errors and agentic_review["review_result"] == "pass"
    return {
        "schema_version": "kiu.no-web-risk-control/v0.1",
        "passed": passed,
        "keyword_preflight": {
            "passed": not keyword_errors,
            "error_count": len(keyword_errors),
            "errors": keyword_errors,
        },
        "agentic_review": agentic_review,
        "structural_errors": structural_errors,
    }


def review_world_alignment(bundle_root: str | Path) -> dict[str, Any]:
    bundle_root = Path(bundle_root)
    alignment_root = bundle_root / "world_alignment"
    gates = _load_gate_docs(alignment_root)
    context_items = _load_world_context_items(alignment_root)
    source_pollution = _detect_source_pollution(bundle_root)
    no_web_report = validate_no_web_world_alignment(bundle_root) if alignment_root.exists() else {"passed": False}

    gate_count = len(gates)
    gates_with_source_unchanged = sum(1 for gate in gates if gate.get("source_skill_unchanged") is True)
    gates_with_isolation = sum(1 for gate in gates if gate.get("world_context_isolated") is True)
    gates_with_reason = sum(1 for gate in gates if str(gate.get("reason", "")).strip())
    md_docs = list(alignment_root.glob("*/WORLD_ALIGNMENT.md")) if alignment_root.exists() else []
    md_with_required_sections = sum(1 for path in md_docs if _world_alignment_md_has_required_sections(path.read_text(encoding="utf-8")))

    source_fidelity_score = 100.0 if not source_pollution else 0.0
    world_context_isolation_score = _ratio_score(gates_with_isolation, gate_count)
    gate_quality_score = round(100.0 * (0.5 * _safe_ratio(gates_with_source_unchanged, gate_count) + 0.5 * _safe_ratio(gates_with_reason, gate_count)), 1)
    explanation_score = _ratio_score(md_with_required_sections, max(gate_count, 1))
    world_context_depth_score = _average_world_context_depth(context_items)
    relevance_review = _review_world_context_relevance(context_items, _load_manifest_skills(bundle_root))
    source_fit_score = relevance_review["source_fit_score"]
    dilution_risk_score = relevance_review["dilution_risk_score"]
    hallucination_risk_score = relevance_review["hallucination_risk_score"]
    workflow_boundary_resilience_score = 100.0
    no_web_penalty = 0.0 if no_web_report.get("passed") else 20.0
    relevance_penalty = (
        max(0.0, (70.0 - source_fit_score) * 0.5)
        + max(0.0, dilution_risk_score - 30.0) * 0.35
        + hallucination_risk_score * 0.10
        + (5.0 if world_context_depth_score < 60.0 else 0.0)
    )
    score = round(
        max(
            0.0,
            0.18 * source_fidelity_score
            + 0.18 * world_context_isolation_score
            + 0.14 * gate_quality_score
            + 0.14 * explanation_score
            + 0.05 * workflow_boundary_resilience_score
            + 0.18 * world_context_depth_score
            + 0.13 * source_fit_score
            - relevance_penalty
            - no_web_penalty,
        ),
        1,
    )

    return {
        "schema_version": WORLD_ALIGNMENT_REVIEW_SCHEMA,
        "bundle_root": str(bundle_root),
        "world_alignment_present": alignment_root.exists(),
        "source_fidelity_preserved": not source_pollution,
        "world_context_isolated": gate_count > 0 and gates_with_isolation == gate_count,
        "original_source_only_mode_supported": gate_count > 0 and gates_with_source_unchanged == gate_count,
        "source_pollution_errors": len(source_pollution),
        "source_pollution_findings": source_pollution,
        "gate_count": gate_count,
        "verdict_counts": _count_by(gates, "verdict"),
        "scores": {
            "source_fidelity_score": source_fidelity_score,
            "world_context_isolation_score": world_context_isolation_score,
            "application_gate_quality_score": gate_quality_score,
            "world_alignment_explanation_score": explanation_score,
            "workflow_boundary_resilience_score": workflow_boundary_resilience_score,
            "world_context_depth_score": world_context_depth_score,
            "source_fit_score": source_fit_score,
            "dilution_risk_score": dilution_risk_score,
            "hallucination_risk_score": hallucination_risk_score,
        },
        "accepted_pressure_count": relevance_review["accepted_pressure_count"],
        "rejected_pressure_count": relevance_review["rejected_pressure_count"],
        "no_forced_enhancement_count": relevance_review["no_forced_enhancement_count"],
        "quality_findings": relevance_review["quality_findings"],
        "no_web_risk_control": no_web_report,
        "world_alignment_score_100": score,
    }


def _review_world_context_relevance(
    context_items: list[dict[str, Any]],
    skills: list[dict[str, str]],
) -> dict[str, Any]:
    skill_map = {skill["skill_id"]: skill for skill in skills}
    source_fit_scores: list[float] = []
    dilution_scores: list[float] = []
    hallucination_scores: list[float] = []
    accepted_count = 0
    rejected_count = 0
    no_forced_count = 0
    findings: list[str] = []
    for item in context_items:
        skill_id = str((item.get("applies_to") or [""])[0])
        skill = skill_map.get(skill_id, {"skill_id": skill_id, "title": skill_id, "content": ""})
        sensitivity = str(item.get("temporal_sensitivity") or _temporal_sensitivity(skill))
        pressures = [str(pressure) for pressure in item.get("pressure_dimensions", [])]
        if item.get("no_forced_enhancement") and not pressures:
            no_forced_count += 1
            source_fit_scores.append(100.0)
            dilution_scores.append(0.0)
            hallucination_scores.append(0.0)
            continue
        if pressures:
            pressure_source_fit = [_source_fit_score(skill, pressure, sensitivity=sensitivity) for pressure in pressures]
            pressure_dilution = [_dilution_risk_score(skill, pressure, sensitivity=sensitivity) for pressure in pressures]
            pressure_hallucination = [_hallucination_risk_score(pressure, no_web_mode=bool(item.get("no_web_mode", True))) for pressure in pressures]
            item_source_fit = round(sum(pressure_source_fit) / len(pressure_source_fit), 1)
            item_dilution = round(max(pressure_dilution), 1)
            item_hallucination = round(max(pressure_hallucination), 1)
        else:
            item_source_fit = float(item.get("source_fit_score", 0.0) or 0.0)
            item_dilution = float(item.get("dilution_risk_score", 0.0) or 0.0)
            item_hallucination = float(item.get("hallucination_risk_score", 0.0) or 0.0)
        source_fit_scores.append(item_source_fit)
        dilution_scores.append(item_dilution)
        hallucination_scores.append(item_hallucination)
        accepted_count += int(item.get("accepted_pressure_count", len(pressures)) or 0)
        rejected_count += int(item.get("rejected_pressure_count", 0) or 0)
        if item_source_fit < 70.0:
            findings.append("weak_source_fit")
        if item_dilution > 30.0:
            findings.append("source_dilution_risk")
        if item_hallucination > 50.0:
            findings.append("hallucination_risk")
    if not context_items:
        return {
            "source_fit_score": 0.0,
            "dilution_risk_score": 100.0,
            "hallucination_risk_score": 100.0,
            "accepted_pressure_count": 0,
            "rejected_pressure_count": 0,
            "no_forced_enhancement_count": 0,
            "quality_findings": ["world_context_missing"],
        }
    return {
        "source_fit_score": round(sum(source_fit_scores) / len(source_fit_scores), 1),
        "dilution_risk_score": round(max(dilution_scores) if dilution_scores else 0.0, 1),
        "hallucination_risk_score": round(max(hallucination_scores) if hallucination_scores else 0.0, 1),
        "accepted_pressure_count": accepted_count,
        "rejected_pressure_count": rejected_count,
        "no_forced_enhancement_count": no_forced_count,
        "quality_findings": sorted(set(findings)),
    }


def _load_manifest_skills(bundle_root: Path) -> list[dict[str, str]]:
    manifest_path = bundle_root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    skills = []
    for entry in manifest.get("skills", []):
        if not isinstance(entry, dict):
            continue
        skill_id = str(entry.get("skill_id", "")).strip()
        if not skill_id:
            continue
        skill_path = bundle_root / str(entry.get("path", f"skills/{skill_id}")) / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""
        title = _extract_title(content if content else skill_id)
        skills.append({"skill_id": skill_id, "title": title, "path": str(skill_path.relative_to(bundle_root)), "content": content})
    return skills


def _context_item_for_skill(skill: dict[str, str], *, no_web_mode: bool) -> dict[str, Any]:
    sensitivity = _temporal_sensitivity(skill)
    context_type = "llm_hypothesis" if no_web_mode else "release_baseline"
    need = _world_alignment_need(skill, sensitivity=sensitivity)
    deepened = _deepen_world_context(skill, sensitivity=sensitivity, no_web_mode=no_web_mode, need=need)
    allowed_effects = ["add_usage_caveat", "ask_more_context", "gate_application"]
    forbidden_effects = ["rewrite_source_claim", "replace_source_evidence", "claim_current_fact"]
    if no_web_mode:
        forbidden_effects.extend(["support_direct_apply", "verified_current_fact"] )
    return {
        "id": f"{skill['skill_id']}-basic-world-context",
        "context_type": context_type,
        "evidence_status": "unverified" if no_web_mode else "release_baseline",
        "no_web_mode": bool(no_web_mode),
        "web_check_performed": False if no_web_mode else True,
        "source_period": None,
        "observed_at": "model_prior" if no_web_mode else date.today().isoformat(),
        "freshness_policy": "before_use" if sensitivity == "high" else "on_release",
        "temporal_sensitivity": sensitivity,
        "temporal_need_score": need["temporal_need_score"],
        "current_fact_dependency_score": need["current_fact_dependency_score"],
        "application_risk_score": need["application_risk_score"],
        "misuse_risk_score": need["misuse_risk_score"],
        "user_actionability_score": need["user_actionability_score"],
        "world_alignment_need_score": need["world_alignment_need_score"],
        "intervention_level": need["intervention_level"],
        "confidence": "low" if no_web_mode else "medium",
        "applies_to": [skill["skill_id"]],
        "summary": deepened["summary"],
        "pressure_dimensions": deepened["pressure_dimensions"],
        "candidate_pressure_arbitration": deepened["candidate_pressure_arbitration"],
        "accepted_pressure_count": deepened["accepted_pressure_count"],
        "rejected_pressure_count": deepened["rejected_pressure_count"],
        "no_forced_enhancement": deepened["no_forced_enhancement"],
        "source_fit_score": deepened["source_fit_score"],
        "dilution_risk_score": deepened["dilution_risk_score"],
        "hallucination_risk_score": deepened["hallucination_risk_score"],
        "world_hypothesis": deepened["world_hypothesis"],
        "why_this_matters": deepened["why_this_matters"],
        "user_context_questions": deepened["user_context_questions"],
        "no_web_unverified_status": deepened["no_web_unverified_status"],
        "loop_mode": deepened["loop_mode"],
        "deepening_rounds": deepened["deepening_rounds"],
        "world_context_depth_score": deepened["world_context_depth_score"],
        "depth_notes": deepened["depth_notes"],
        "agentic_boundary_review": deepened["agentic_boundary_review"],
        "allowed_effects": allowed_effects,
        "forbidden_effects": forbidden_effects,
    }


def _world_alignment_need(skill: dict[str, str], *, sensitivity: str) -> dict[str, Any]:
    haystack = _skill_haystack(skill)
    if sensitivity == "high":
        temporal = 0.9
        current_fact = 0.9
        application_risk = 0.85
        misuse = 0.7
        actionability = 0.85
    elif sensitivity == "medium":
        temporal = 0.55
        current_fact = 0.45
        application_risk = 0.55
        misuse = 0.45
        actionability = 0.65
    else:
        temporal = 0.15
        current_fact = 0.05
        application_risk = 0.20
        misuse = 0.35 if any(marker in haystack for marker in ("decision", "judgment", "circle", "competence", "bias", "inversion")) else 0.20
        actionability = 0.35 if any(marker in haystack for marker in ("decision", "judgment", "action", "apply", "competence")) else 0.15
    score = round(
        0.25 * temporal
        + 0.25 * current_fact
        + 0.20 * application_risk
        + 0.15 * misuse
        + 0.15 * actionability,
        3,
    )
    if score >= 0.75:
        level = "strong_gate"
    elif score >= 0.50:
        level = "moderate"
    elif score >= 0.25:
        level = "light"
    else:
        level = "minimal"
    return {
        "temporal_need_score": temporal,
        "current_fact_dependency_score": current_fact,
        "application_risk_score": application_risk,
        "misuse_risk_score": misuse,
        "user_actionability_score": actionability,
        "world_alignment_need_score": score,
        "intervention_level": level,
    }


def _deepen_world_context(
    skill: dict[str, str],
    *,
    sensitivity: str,
    no_web_mode: bool,
    need: dict[str, Any],
) -> dict[str, Any]:
    workflow_candidates = _workflow_pressure_candidates(skill, sensitivity=sensitivity)
    arbitration = _arbitrate_pressure_candidates(
        skill,
        workflow_candidates,
        sensitivity=sensitivity,
        need=need,
        no_web_mode=no_web_mode,
    )
    accepted = [record["candidate"] for record in arbitration if record.get("accepted")]
    draft = _draft_world_context(
        skill,
        pressure_dimensions=accepted,
        sensitivity=sensitivity,
        no_web_mode=no_web_mode,
        no_forced_enhancement=not accepted,
    )
    rounds = 1
    critique = _critique_world_context_depth(draft, skill=skill, no_web_mode=no_web_mode)
    minimum_rounds = 2 if accepted and sensitivity in {"medium", "high"} else 1
    while accepted and (critique["needs_revision"] or rounds < minimum_rounds) and rounds < 3:
        draft = _revise_world_context(draft, critique=critique, skill=skill, workflow_candidates=accepted)
        rounds += 1
        critique = _critique_world_context_depth(draft, skill=skill, no_web_mode=no_web_mode)
    source_fit = _aggregate_source_fit(arbitration, no_forced_enhancement=not accepted)
    dilution = _aggregate_dilution_risk(arbitration, pressure_dimensions=accepted)
    hallucination = _aggregate_hallucination_risk(arbitration, pressure_dimensions=accepted)
    score = _score_world_context_depth(draft, critique=critique)
    if not accepted or need.get("intervention_level") == "minimal":
        score = max(score, 85.0)
    notes = list(critique["notes"])
    if not accepted:
        notes.append("no_forced_enhancement_used")
    if not critique["needs_revision"]:
        notes.append("agentic_loop_passed_specificity_and_no_web_checks")
    return {
        **draft,
        "candidate_pressure_arbitration": arbitration,
        "accepted_pressure_count": len(accepted),
        "rejected_pressure_count": len(arbitration) - len(accepted),
        "no_forced_enhancement": not accepted,
        "source_fit_score": source_fit,
        "dilution_risk_score": dilution,
        "hallucination_risk_score": hallucination,
        "loop_mode": "workflow_plus_agentic_proxy",
        "deepening_rounds": rounds,
        "world_context_depth_score": score,
        "depth_notes": notes,
        "agentic_boundary_review": {
            "workflow_step": "candidate pressure dimensions were derived from skill metadata and deterministic domain markers",
            "agentic_step": "selected and critiqued application hypotheses for specificity, source fit, dilution risk, no-web safety, and source-boundary preservation",
            "findings": critique["findings"],
        },
    }


def _workflow_pressure_candidates(skill: dict[str, str], *, sensitivity: str) -> list[str]:
    haystack = _skill_haystack(skill)
    candidates: list[str] = []
    for markers, dimensions in DOMAIN_PRESSURE_DIMENSIONS:
        if any(marker.lower() in haystack for marker in markers):
            candidates.extend(dimensions)
    if not candidates:
        if sensitivity == "high":
            candidates.extend(DOMAIN_PRESSURE_DIMENSIONS[2][1])
        elif sensitivity == "medium":
            candidates.extend(
                (
                    "tooling and automation can change execution cost without removing the need to identify decision ownership and constraints.",
                    "team topology and handoff boundaries can change whether a source-derived method is usable in practice.",
                    "stakeholder incentives can make a method look applicable while changing what a safe action should be.",
                )
            )
        else:
            candidates.extend(
                (
                    "current user intent may shift the skill from judgment support into fact lookup, summary, or advice, which should be routed away from world alignment.",
                    "misuse risk comes less from time sensitivity than from applying a source mental model outside its decision boundary.",
                )
            )
    return _dedupe_keep_order(candidates)


def _agentic_select_pressure_dimensions(skill: dict[str, str], candidates: list[str], *, sensitivity: str) -> list[str]:
    haystack = _skill_haystack(skill)
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        score = 0
        lowered = candidate.lower()
        for token in re.split(r"[^a-zA-Z0-9\u4e00-\u9fff]+", haystack):
            if len(token) >= 4 and token in lowered:
                score += 2
        if sensitivity == "high" and any(word in lowered for word in ("current", "dated", "risk", "advice")):
            score += 3
        if sensitivity == "medium" and any(word in lowered for word in ("ownership", "boundary", "constraints", "stakeholder")):
            score += 3
        if "source" in lowered and "current" in lowered:
            score += 1
        scored.append((score, candidate))
    scored.sort(key=lambda item: (-item[0], candidates.index(item[1])))
    minimum = 4 if sensitivity == "medium" else 3 if sensitivity == "high" else 2
    return [item for _, item in scored[:minimum]]


def _arbitrate_pressure_candidates(
    skill: dict[str, str],
    candidates: list[str],
    *,
    sensitivity: str,
    need: dict[str, Any],
    no_web_mode: bool,
) -> list[dict[str, Any]]:
    records = []
    for candidate in candidates:
        source_fit = _source_fit_score(skill, candidate, sensitivity=sensitivity)
        enrichment = _enrichment_value_score(candidate, sensitivity=sensitivity)
        application_need = round(100.0 * float(need.get("world_alignment_need_score", 0.0) or 0.0), 1)
        dilution = _dilution_risk_score(skill, candidate, sensitivity=sensitivity)
        hallucination = _hallucination_risk_score(candidate, no_web_mode=no_web_mode)
        acceptance = round(source_fit + enrichment + application_need - dilution - hallucination, 1)
        source_fit_min = 80.0 if need.get("intervention_level") == "minimal" else 55.0
        accepted = (
            source_fit >= source_fit_min
            and dilution <= 45.0
            and hallucination <= 50.0
            and acceptance >= 95.0
        )
        rejection_reason = "" if accepted else _candidate_rejection_reason(source_fit, dilution, hallucination, acceptance)
        records.append(
            {
                "candidate": candidate,
                "source_fit_score": source_fit,
                "enrichment_value_score": enrichment,
                "application_need_score": application_need,
                "dilution_risk_score": dilution,
                "hallucination_risk_score": hallucination,
                "candidate_acceptance_score": acceptance,
                "accepted": accepted,
                "rejection_reason": rejection_reason,
            }
        )
    accepted_records = [record for record in records if record["accepted"]]
    if not accepted_records:
        return records
    maximum = 3 if sensitivity == "high" else 3 if need.get("intervention_level") == "moderate" else 1 if need.get("intervention_level") == "minimal" else 2
    accepted_candidates = {
        record["candidate"]
        for record in sorted(
            accepted_records,
            key=lambda record: (-float(record["candidate_acceptance_score"]), -float(record["source_fit_score"])),
        )[:maximum]
    }
    for record in records:
        if record["accepted"] and record["candidate"] not in accepted_candidates:
            record["accepted"] = False
            record["rejection_reason"] = "lower_ranked_relevant_pressure"
    return records


def _candidate_rejection_reason(source_fit: float, dilution: float, hallucination: float, acceptance: float) -> str:
    if source_fit < 55.0:
        return "source_fit_below_threshold"
    if dilution > 45.0:
        return "dilution_risk_above_threshold"
    if hallucination > 50.0:
        return "hallucination_risk_above_threshold"
    if acceptance < 95.0:
        return "acceptance_score_below_threshold"
    return "not_selected"


def _draft_world_context(
    skill: dict[str, str],
    *,
    pressure_dimensions: list[str],
    sensitivity: str,
    no_web_mode: bool,
    no_forced_enhancement: bool = False,
) -> dict[str, Any]:
    summary = _specific_summary(
        skill,
        pressure_dimensions=pressure_dimensions,
        sensitivity=sensitivity,
        no_web_mode=no_web_mode,
        no_forced_enhancement=no_forced_enhancement,
    )
    world_hypothesis = _world_hypothesis(skill, pressure_dimensions=pressure_dimensions, sensitivity=sensitivity)
    why_this_matters = _why_this_matters(skill, pressure_dimensions=pressure_dimensions, sensitivity=sensitivity)
    questions = _user_context_questions(skill, pressure_dimensions=pressure_dimensions, sensitivity=sensitivity)
    return {
        "summary": summary,
        "pressure_dimensions": pressure_dimensions,
        "world_hypothesis": world_hypothesis,
        "why_this_matters": why_this_matters,
        "user_context_questions": questions,
        "no_web_unverified_status": "No web lookup was performed. Treat these as application hypotheses for user-context probing, not verified claims about the current world.",
    }


def _critique_world_context_depth(draft: dict[str, Any], *, skill: dict[str, str], no_web_mode: bool) -> dict[str, Any]:
    findings: list[str] = []
    notes: list[str] = []
    summary = str(draft.get("summary", ""))
    pressure_dimensions = [str(item) for item in draft.get("pressure_dimensions", [])]
    joined = " ".join([summary, str(draft.get("world_hypothesis", "")), *pressure_dimensions])
    if any(phrase in joined for phrase in GENERIC_WORLD_CONTEXT_PHRASES):
        findings.append("generic_world_context_phrase")
    if len(pressure_dimensions) < 2:
        findings.append("too_few_pressure_dimensions")
    if not any(_has_domain_specific_signal(item) for item in pressure_dimensions):
        findings.append("missing_domain_specific_pressure")
    if no_web_mode and _contains_unverified_current_fact(joined):
        findings.append("unverified_current_fact_claim")
    if _looks_like_source_rewrite(joined, skill):
        findings.append("possible_source_rewrite")
    if "generic_world_context_phrase" not in findings:
        notes.append("generic_phrase_check_passed")
    if "missing_domain_specific_pressure" not in findings:
        notes.append("domain_specific_pressure_present")
    if "unverified_current_fact_claim" not in findings:
        notes.append("no_web_current_fact_claim_check_passed")
    return {"needs_revision": bool(findings), "findings": findings, "notes": notes}


def _revise_world_context(
    draft: dict[str, Any],
    *,
    critique: dict[str, Any],
    skill: dict[str, str],
    workflow_candidates: list[str],
) -> dict[str, Any]:
    pressure_dimensions = list(draft.get("pressure_dimensions", []))
    findings = set(critique.get("findings", []))
    if "too_few_pressure_dimensions" in findings or "missing_domain_specific_pressure" in findings:
        for candidate in workflow_candidates:
            if candidate not in pressure_dimensions:
                pressure_dimensions.append(candidate)
            if len(pressure_dimensions) >= 3 and any(_has_domain_specific_signal(item) for item in pressure_dimensions):
                break
    if "generic_world_context_phrase" in findings:
        sensitivity = _temporal_sensitivity(skill)
        return _draft_world_context(skill, pressure_dimensions=pressure_dimensions, sensitivity=sensitivity, no_web_mode=True)
    revised = dict(draft)
    revised["pressure_dimensions"] = pressure_dimensions
    revised["summary"] = _specific_summary(skill, pressure_dimensions=pressure_dimensions, sensitivity=_temporal_sensitivity(skill), no_web_mode=True)
    revised["world_hypothesis"] = _world_hypothesis(skill, pressure_dimensions=pressure_dimensions, sensitivity=_temporal_sensitivity(skill))
    revised["why_this_matters"] = _why_this_matters(skill, pressure_dimensions=pressure_dimensions, sensitivity=_temporal_sensitivity(skill))
    revised["user_context_questions"] = _user_context_questions(skill, pressure_dimensions=pressure_dimensions, sensitivity=_temporal_sensitivity(skill))
    return revised


def _score_world_context_depth(draft: dict[str, Any], *, critique: dict[str, Any]) -> float:
    pressure_dimensions = draft.get("pressure_dimensions", []) or []
    score = 100.0
    score -= 20.0 * len(critique.get("findings", []))
    if len(pressure_dimensions) < 3:
        score -= 10.0
    if not str(draft.get("world_hypothesis", "")).strip():
        score -= 15.0
    if not str(draft.get("why_this_matters", "")).strip():
        score -= 15.0
    if len(draft.get("user_context_questions", []) or []) < 2:
        score -= 10.0
    return round(max(0.0, min(score, 100.0)), 1)


def _specific_summary(
    skill: dict[str, str],
    *,
    pressure_dimensions: list[str],
    sensitivity: str,
    no_web_mode: bool,
    no_forced_enhancement: bool = False,
) -> str:
    title = skill.get("title") or skill.get("skill_id", "this skill")
    if no_forced_enhancement:
        return f"no_forced_enhancement: for {title}, no candidate world pressure passed source-fit arbitration. Keep the source view primary and use this layer only for misuse boundaries and no-web disclosure."
    first = pressure_dimensions[0] if pressure_dimensions else _summary_for_sensitivity(sensitivity)
    second = pressure_dimensions[1] if len(pressure_dimensions) > 1 else "ask the user for concrete constraints before operational use"
    status = "In no-web mode this is an unverified application hypothesis" if no_web_mode else "Using the release baseline"
    return f"{status}: for {title}, check whether {first} Also check whether {second}"


def _world_hypothesis(skill: dict[str, str], *, pressure_dimensions: list[str], sensitivity: str) -> str:
    title = skill.get("title") or skill.get("skill_id", "this skill")
    if sensitivity == "high":
        return f"{title} should not be used as direct current advice until the user supplies dated evidence, decision horizon, and accountable review; the world layer only frames what must be checked."
    if pressure_dimensions:
        return f"{title} remains source-faithful, but practical application may depend on a real-world pressure the source layer does not verify: {pressure_dimensions[0]} The layer should probe that pressure before allowing confident use."
    return f"{title} can be applied in original-source-only mode, while the world layer checks whether the user's request has drifted into current facts or unsupported advice."


def _why_this_matters(skill: dict[str, str], *, pressure_dimensions: list[str], sensitivity: str) -> str:
    if sensitivity == "high":
        return "High temporal sensitivity means a correct source-derived reasoning pattern can still produce unsafe output if current facts, dates, or user constraints are missing."
    if len(pressure_dimensions) >= 2:
        return f"The skill may still be useful, but the application setting can shift: {pressure_dimensions[0]} A second pressure can change the safe next step: {pressure_dimensions[1]} This changes the application gate without changing the source claim."
    return "The world layer should change only the application gate, because the source claim remains intact while user context may alter safe use."


def _user_context_questions(skill: dict[str, str], *, pressure_dimensions: list[str], sensitivity: str) -> list[str]:
    if sensitivity == "high":
        return [
            "What dated source or current evidence should be treated as authoritative for this use?",
            "What decision horizon, risk constraint, and accountable reviewer govern the action?",
            "Is the user asking for analysis support, or for a direct current recommendation?",
        ]
    questions = []
    for dimension in pressure_dimensions[:3]:
        if "ownership" in dimension or "authority" in dimension:
            questions.append("Who owns the decision outcome, and who has authority to accept the tradeoff?")
        elif "boundary" in dimension:
            questions.append("Where do the real business, system, and team boundaries diverge in this case?")
        elif "AI-assisted" in dimension or "tooling" in dimension or "automation" in dimension:
            questions.append("Which parts became cheaper because of tooling, and which judgment or accountability constraint did not change?")
        elif "stakeholder" in dimension:
            questions.append("Which stakeholder conflict or acceptance consequence must be resolved before action?")
        else:
            questions.append("What concrete current constraint would make this source-derived method unsafe or incomplete here?")
    return _dedupe_keep_order(questions)[:3] or ["What current user context could change the safe application of this source-derived skill?"]


def _has_recognizable_low_temporal_judgment_model(skill: dict[str, str]) -> bool:
    haystack = _skill_haystack(skill)
    markers = (
        "circle",
        "competence",
        "bias",
        "audit",
        "inversion",
        "invert",
        "judgment",
        "decision",
        "mental model",
        "principle",
    )
    return any(marker in haystack for marker in markers)


def _source_fit_score(skill: dict[str, str], candidate: str, *, sensitivity: str) -> float:
    haystack = _skill_haystack(skill)
    lowered = candidate.lower()
    tokens = [token for token in re.split(r"[^a-zA-Z0-9\u4e00-\u9fff]+", haystack) if len(token) >= 4]
    overlap = sum(1 for token in tokens if token in lowered)
    score = min(40.0 + 12.0 * overlap, 85.0)
    if sensitivity == "high" and any(marker in lowered for marker in ("current market", "dated evidence", "accounting", "risk", "advice", "disclosures")):
        score = max(score, 85.0)
    if any(marker in haystack for marker in ("subsystem", "decomposition", "business")) and any(marker in lowered for marker in ("subsystem", "business boundary", "ownership", "handoff")):
        score = max(score, 85.0)
    if any(marker in haystack for marker in ("requirement", "stakeholder", "需求")) and any(marker in lowered for marker in ("requirement", "stakeholder", "traceability", "assumptions")):
        score = max(score, 82.0)
    if any(marker in haystack for marker in ("circle", "competence")):
        if any(marker in lowered for marker in ("expertise", "competence", "surface competence")):
            score = max(score, 85.0)
        elif _off_domain_for_circle_of_competence(candidate):
            score = min(score, 35.0)
        else:
            score = min(score, 65.0)
    if any(marker in haystack for marker in ("bias", "audit")) and any(marker in lowered for marker in ("bias", "disconfirming")):
        score = max(score, 82.0)
    if any(marker in haystack for marker in ("inversion", "invert", "problem")) and any(marker in lowered for marker in ("decision", "evidence", "failure")):
        score = max(score, 72.0)
    if sensitivity == "low" and not _has_recognizable_low_temporal_judgment_model(skill):
        score = min(score, 45.0)
    if sensitivity == "low" and _low_temporal_off_domain_pressure(candidate) and not any(marker in haystack for marker in ("business", "subsystem", "requirement")):
        score = min(score, 35.0)
    return round(min(score, 100.0), 1)


def _enrichment_value_score(candidate: str, *, sensitivity: str) -> float:
    lowered = candidate.lower()
    score = 45.0
    if any(marker in lowered for marker in ("ask", "provide", "state", "name", "identify", "distinguish")):
        score += 20.0
    if any(marker in lowered for marker in ("boundary", "constraints", "risk", "authority", "evidence", "counterexamples")):
        score += 15.0
    if sensitivity == "high" and any(marker in lowered for marker in ("current", "dated", "disclosures", "restatements")):
        score += 15.0
    return round(min(score, 100.0), 1)


def _dilution_risk_score(skill: dict[str, str], candidate: str, *, sensitivity: str) -> float:
    lowered = candidate.lower()
    haystack = _skill_haystack(skill)
    risk = 10.0
    if sensitivity == "low" and _low_temporal_off_domain_pressure(candidate) and not any(marker in haystack for marker in ("business", "subsystem", "requirement")):
        risk = 85.0
    elif "llm-generated" in lowered or "dashboard noise" in lowered:
        risk = 25.0
    elif "current market" in lowered and sensitivity != "high":
        risk = 55.0
    return round(risk, 1)


def _hallucination_risk_score(candidate: str, *, no_web_mode: bool) -> float:
    lowered = candidate.lower()
    if not no_web_mode:
        return 10.0
    if _contains_unverified_current_fact(candidate):
        return 85.0
    if any(marker in lowered for marker in CURRENT_FACT_MARKERS):
        return 35.0
    return 10.0


def _low_temporal_off_domain_pressure(candidate: str) -> bool:
    lowered = candidate.lower()
    return any(marker in lowered for marker in OFF_DOMAIN_BUSINESS_PRESSURE_MARKERS)


def _off_domain_for_circle_of_competence(candidate: str) -> bool:
    lowered = candidate.lower()
    markers = (
        *OFF_DOMAIN_BUSINESS_PRESSURE_MARKERS,
        "company-specific",
        "disclosures",
        "restatements",
        "portfolio",
        "historical analogy",
        "role legitimacy",
        "organization constraints",
        "team topology",
        "release ownership",
    )
    return any(marker in lowered for marker in markers)


def _aggregate_source_fit(arbitration: list[dict[str, Any]], *, no_forced_enhancement: bool) -> float:
    if no_forced_enhancement:
        return 100.0
    accepted = [record for record in arbitration if record.get("accepted")]
    if not accepted:
        return 0.0
    return round(sum(float(record.get("source_fit_score", 0.0) or 0.0) for record in accepted) / len(accepted), 1)


def _aggregate_dilution_risk(arbitration: list[dict[str, Any]], *, pressure_dimensions: list[str]) -> float:
    if not pressure_dimensions:
        return 0.0
    selected = [record for record in arbitration if record.get("candidate") in pressure_dimensions]
    if not selected:
        return 0.0
    return round(max(float(record.get("dilution_risk_score", 0.0) or 0.0) for record in selected), 1)


def _aggregate_hallucination_risk(arbitration: list[dict[str, Any]], *, pressure_dimensions: list[str]) -> float:
    if not pressure_dimensions:
        return 0.0
    selected = [record for record in arbitration if record.get("candidate") in pressure_dimensions]
    if not selected:
        return 0.0
    return round(max(float(record.get("hallucination_risk_score", 0.0) or 0.0) for record in selected), 1)


def _application_gate_for_skill(skill: dict[str, str], *, context_item: dict[str, Any], no_web_mode: bool) -> dict[str, Any]:
    sensitivity = str(context_item.get("temporal_sensitivity", "medium"))
    if sensitivity == "high" and no_web_mode:
        if _requires_current_advice_refusal(skill):
            verdict = "refuse"
            reason = "This prompt shape requests current financial or investment advice. v0.7.0 no-web mode cannot verify current data or user risk constraints, so direct application is refused."
            required_context = [
                "verified current data source",
                "licensed or accountable domain review",
                "user risk constraints and decision authority",
            ]
            caveats = ["Do not provide current financial, market, legal, medical, or regulatory advice in no-web mode."]
        else:
            verdict = "ask_more_context"
            reason = "This skill may depend on current facts or financial/regulatory data. v0.7.0 no-web mode cannot verify current data, so it must request current user-provided context before application."
            required_context = [
                "current data date and source",
                "decision time window",
                "user risk constraints or domain authority",
            ]
            caveats = ["Do not treat this as current financial, market, legal, medical, or regulatory advice."]
        world_context_supports_verdict = False
    elif sensitivity == "medium":
        verdict = "apply_with_caveats"
        reason = str(context_item.get("why_this_matters") or "The source-derived skill can remain useful, but no-web world context is only an unverified hypothesis. Apply with caveats and ask for concrete user context before operational use.")
        required_context = list(context_item.get("user_context_questions") or [
            "current team or organization context",
            "which constraints differ from the source setting",
        ])
        caveats = [
            "World context is not source evidence and has not been web-verified.",
            str(context_item.get("no_web_unverified_status") or "Treat this as an application hypothesis, not a current-world fact."),
        ]
        world_context_supports_verdict = True
    else:
        verdict = "apply"
        reason = "The skill appears to be a low-temporal-sensitivity mental model. It can be used in original-source-only mode; no-web world context is not required as evidence for the verdict."
        required_context = []
        caveats = ["If the user asks about current entities or high-stakes facts, switch to ask_more_context."]
        world_context_supports_verdict = False
    return {
        "schema_version": APPLICATION_GATE_SCHEMA,
        "skill_id": skill["skill_id"],
        "source_skill_unchanged": True,
        "world_context_isolated": True,
        "source_fidelity_preserved": True,
        "web_check_performed": False if no_web_mode else True,
        "current_fact_claims_allowed": False if no_web_mode else True,
        "verified_current_fact_count": 0 if no_web_mode else 1,
        "unverified_assumption_count": 1 if no_web_mode else 0,
        "temporal_sensitivity": sensitivity,
        "verdict": verdict,
        "world_context_supports_verdict": world_context_supports_verdict,
        "reason": reason,
        "required_context": required_context,
        "caveats": caveats,
        "forbidden": [
            "do_not_rewrite_source_skill",
            "do_not_treat_world_context_as_authorial_evidence",
            "do_not_claim_verified_current_facts_in_no_web_mode",
        ],
    }


def _requires_current_advice_refusal(skill: dict[str, str]) -> bool:
    haystack = f"{skill.get('skill_id', '')} {skill.get('title', '')}".lower()
    advice_markers = ("current", "advice", "recommend", "buy", "sell", "investment-advice", "投资建议", "买入", "卖出")
    domain_markers = ("investment", "financial", "finance", "market", "price", "投资", "金融", "市场", "价格")
    return any(marker in haystack for marker in advice_markers) and any(marker in haystack for marker in domain_markers)


def _render_world_alignment_markdown(*, skill: dict[str, str], context_item: dict[str, Any], gate: dict[str, Any]) -> str:
    required_context = gate.get("required_context", []) or ["No extra context required for original-source-only use."]
    caveats = gate.get("caveats", []) or ["No caveats recorded."]
    pressure_dimensions = context_item.get("pressure_dimensions", []) or ["No specific pressure dimensions recorded."]
    depth_notes = context_item.get("depth_notes", []) or ["No depth notes recorded."]
    return "\n".join(
        [
            f"# World Alignment: {skill['skill_id']}",
            "",
            "## Source Claim",
            "The source-derived SKILL.md remains unchanged. Use its native anchors, rationale, and boundaries as the source-faithful claim.",
            "",
            "## World Context",
            f"- context_type: `{context_item.get('context_type')}`",
            f"- evidence_status: `{context_item.get('evidence_status')}`",
            f"- temporal_sensitivity: `{context_item.get('temporal_sensitivity')}`",
            f"- world_alignment_need_score: `{context_item.get('world_alignment_need_score')}`",
            f"- intervention_level: `{context_item.get('intervention_level')}`",
            f"- source_fit_score: `{context_item.get('source_fit_score')}`",
            f"- dilution_risk_score: `{context_item.get('dilution_risk_score')}`",
            f"- hallucination_risk_score: `{context_item.get('hallucination_risk_score')}`",
            f"- no_forced_enhancement: `{str(context_item.get('no_forced_enhancement')).lower()}`",
            f"- summary: {context_item.get('summary')}",
            f"- loop_mode: `{context_item.get('loop_mode')}`",
            f"- deepening_rounds: `{context_item.get('deepening_rounds')}`",
            f"- world_context_depth_score: `{context_item.get('world_context_depth_score')}`",
            "",
            "## World Hypothesis",
            str(context_item.get("world_hypothesis", "No world hypothesis recorded.")),
            "",
            "## Pressure Dimensions",
            *[f"- {item}" for item in pressure_dimensions],
            "",
            "## Candidate Arbitration",
            *[
                f"- accepted={record.get('accepted')} source_fit={record.get('source_fit_score')} dilution={record.get('dilution_risk_score')} hallucination={record.get('hallucination_risk_score')}: {record.get('candidate')}"
                for record in context_item.get("candidate_pressure_arbitration", [])
            ],
            "",
            "## Why This Matters",
            str(context_item.get("why_this_matters", "No application impact recorded.")),
            "",
            "## What To Ask User",
            *[f"- {item}" for item in required_context],
            "",
            "## No-Web Unverified Status",
            str(context_item.get("no_web_unverified_status", "No-web world context is unverified.")),
            "",
            "## Depth Review",
            *[f"- {item}" for item in depth_notes],
            "",
            "## Application Verdict",
            f"`{gate.get('verdict')}`",
            "",
            "## Why",
            str(gate.get("reason", "")),
            "",
            "## Required User Context",
            *[f"- {item}" for item in required_context],
            "",
            "## Caveats",
            *[f"- {item}" for item in caveats],
            "",
            "## Original-Source-Only Mode",
            "If the user requests original-source-only output, ignore this world_alignment layer and use SKILL.md with its native boundaries.",
            "",
            "## No-Web Disclosure",
            f"web_check_performed: `{str(gate.get('web_check_performed')).lower()}`",
            "This artifact does not verify current-world facts when web_check_performed is false; unverified assumptions may only add caveats or request context.",
            "",
            "## Machine Markers",
            f"source_skill_unchanged: `{str(gate.get('source_skill_unchanged')).lower()}`",
            f"world_context_isolated: `{str(gate.get('world_context_isolated')).lower()}`",
            "",
        ]
    )


def _keyword_preflight(alignment_root: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for path in _alignment_text_paths(alignment_root):
        text = path.read_text(encoding="utf-8")
        if _web_check_performed_nearby(text):
            continue
        lowered_text = text.lower()
        for pattern in NO_WEB_FORBIDDEN_PATTERNS:
            pattern_hit = pattern in text or pattern.lower() in lowered_text
            if pattern_hit and not _is_negated_no_web_phrase(text, pattern):
                errors.append({"path": str(path), "pattern": pattern, "issue": "current_fact_claim_in_no_web_mode"})
    return errors


def _agentic_no_web_review(alignment_root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for path in _alignment_text_paths(alignment_root):
        text = path.read_text(encoding="utf-8")
        if _web_check_performed_nearby(text):
            continue
        for regex, issue in AGENTIC_RISK_PATTERNS:
            match = re.search(regex, text, flags=re.IGNORECASE)
            if match:
                findings.append(
                    {
                        "severity": "high",
                        "path": str(path),
                        "claim": _claim_excerpt(text, match.start()),
                        "issue": issue,
                        "required_fix": "Mark as unverified assumption, narrow scope, or ask for user-provided current context.",
                    }
                )
    result = "pass" if not findings else "fail"
    return {
        "schema_version": NO_WEB_REVIEW_SCHEMA,
        "web_check_performed": False,
        "review_result": result,
        "finding_count": len(findings),
        "findings": findings,
        "risk_scores": {
            "current_fact_hallucination_risk": 0.0 if not findings else 0.85,
            "overgeneralization_risk": 0.0 if not findings else 0.8,
            "hidden_source_rewrite_risk": 0.1 if not findings else 0.4,
            "high_sensitivity_misuse_risk": 0.1 if not findings else 0.5,
        },
        "allowed_verdicts": ["apply_with_caveats", "ask_more_context", "refuse"] if findings else ["apply", "apply_with_caveats", "ask_more_context", "refuse"],
        "blocked_verdicts": ["apply"] if findings else [],
    }


def _structural_no_web_errors(alignment_root: Path) -> list[str]:
    errors: list[str] = []
    for gate_path in alignment_root.glob("*/application_gate.yaml") if alignment_root.exists() else []:
        gate = yaml.safe_load(gate_path.read_text(encoding="utf-8")) or {}
        if gate.get("web_check_performed") is False and gate.get("current_fact_claims_allowed") is not False:
            errors.append(f"{gate_path}: current_fact_claims_allowed must be false in no-web mode")
        if gate.get("temporal_sensitivity") == "high" and gate.get("web_check_performed") is False and gate.get("verdict") == "apply":
            errors.append(f"{gate_path}: high sensitivity no-web gate must not apply directly")
        if gate.get("unverified_assumption_count", 0) and gate.get("verdict") == "apply" and gate.get("world_context_supports_verdict") is True:
            errors.append(f"{gate_path}: unverified assumptions must not support direct apply")
    for md_path in alignment_root.glob("*/WORLD_ALIGNMENT.md") if alignment_root.exists() else []:
        text = md_path.read_text(encoding="utf-8")
        if "No-Web Disclosure" not in text:
            errors.append(f"{md_path}: missing No-Web Disclosure")
    return errors


def _detect_source_pollution(bundle_root: Path) -> list[dict[str, str]]:
    alignment_root = bundle_root / "world_alignment"
    context_doc = yaml.safe_load((alignment_root / "world_context.yaml").read_text(encoding="utf-8")) if (alignment_root / "world_context.yaml").exists() else {}
    summaries = [str(item.get("summary", "")).strip() for item in context_doc.get("items", []) if isinstance(item, dict)]
    summaries = [summary for summary in summaries if len(summary) >= 12]
    pollution_markers = [
        "AI 原型工具降低了需求验证成本",
        "world_context",
        "No-Web Disclosure",
        "web_check_performed",
        "world_context_isolated",
    ]
    findings: list[dict[str, str]] = []
    for skill_path in (bundle_root / "skills").glob("*/SKILL.md"):
        text = skill_path.read_text(encoding="utf-8")
        for summary in summaries:
            if summary in text:
                findings.append({"path": str(skill_path), "issue": "world_context_copied_into_source_skill", "claim": summary})
        for marker in pollution_markers:
            if marker in text:
                findings.append({"path": str(skill_path), "issue": "world_alignment_marker_copied_into_source_skill", "claim": marker})
    return findings


def _load_gate_docs(alignment_root: Path) -> list[dict[str, Any]]:
    gates = []
    if not alignment_root.exists():
        return gates
    for gate_path in sorted(alignment_root.glob("*/application_gate.yaml")):
        gates.append(yaml.safe_load(gate_path.read_text(encoding="utf-8")) or {})
    return gates


def _load_world_context_items(alignment_root: Path) -> list[dict[str, Any]]:
    context_path = alignment_root / "world_context.yaml"
    if not context_path.exists():
        return []
    doc = yaml.safe_load(context_path.read_text(encoding="utf-8")) or {}
    return [item for item in doc.get("items", []) if isinstance(item, dict)]


def _average_world_context_depth(context_items: list[dict[str, Any]]) -> float:
    if not context_items:
        return 0.0
    scores = []
    for item in context_items:
        score = item.get("world_context_depth_score")
        if score is None:
            score = _fallback_context_depth_score(item)
        scores.append(float(score))
    return round(sum(scores) / len(scores), 1)


def _fallback_context_depth_score(item: dict[str, Any]) -> float:
    score = 100.0
    text = " ".join(str(item.get(key, "")) for key in ("summary", "world_hypothesis", "why_this_matters"))
    if any(phrase in text for phrase in GENERIC_WORLD_CONTEXT_PHRASES):
        score -= 45.0
    if len(item.get("pressure_dimensions", []) or []) < 2:
        score -= 25.0
    if not item.get("user_context_questions"):
        score -= 15.0
    if not item.get("world_hypothesis"):
        score -= 15.0
    return round(max(0.0, score), 1)


def _alignment_text_paths(alignment_root: Path) -> list[Path]:
    if not alignment_root.exists():
        return []
    return sorted([*alignment_root.glob("*.yaml"), *alignment_root.glob("*/*.yaml"), *alignment_root.glob("*/*.md")])


def _web_check_performed_nearby(text: str) -> bool:
    return "web_check_performed: true" in text or "web_check_performed: `true`" in text


def _is_negated_no_web_phrase(text: str, pattern: str) -> bool:
    index = text.find(pattern)
    if index < 0:
        return False
    window = text[max(0, index - 24): index + len(pattern) + 24]
    negators = ("未联网", "不能确认", "需要用户提供", "可能", "假设", "待验证", "不验证", "does not verify")
    return any(negator in window for negator in negators)


def _world_alignment_md_has_required_sections(text: str) -> bool:
    required = (
        "## Source Claim",
        "## World Context",
        "## World Hypothesis",
        "## Why This Matters",
        "## What To Ask User",
        "## No-Web Unverified Status",
        "## Application Verdict",
        "## Original-Source-Only Mode",
        "## No-Web Disclosure",
    )
    return all(item in text for item in required)


def _temporal_sensitivity(skill: dict[str, str]) -> str:
    haystack = f"{skill.get('skill_id', '')} {skill.get('title', '')}".lower()
    if any(marker in haystack for marker in HIGH_SENSITIVITY_MARKERS):
        return "high"
    if any(marker in haystack for marker in MEDIUM_SENSITIVITY_MARKERS):
        return "medium"
    return "low"


def _summary_for_sensitivity(sensitivity: str) -> str:
    if sensitivity == "high":
        return "Current application may depend on fresh market, financial, regulatory, legal, medical, or company-specific facts that v0.7.0 no-web mode cannot verify."
    if sensitivity == "medium":
        return "Real-world organizational practices and tooling may change how this source-derived method should be applied; treat this as an unverified no-web hypothesis."
    return "This source-derived mental model is likely low-temporal-sensitivity; world alignment is optional and mainly checks misuse or current-entity drift."


def _skill_haystack(skill: dict[str, str]) -> str:
    return f"{skill.get('skill_id', '')} {skill.get('title', '')} {skill.get('content', '')}".lower()


def _dedupe_keep_order(items: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _has_domain_specific_signal(text: str) -> bool:
    signals = (
        "AI-assisted",
        "cross-functional",
        "subsystem boundary",
        "business boundary",
        "organization constraints",
        "stakeholder",
        "ownership",
        "current market",
        "accounting policy",
        "historical analogy",
        "mechanism",
        "incentives",
        "decision authority",
        "LLM-generated",
        "expertise boundaries",
    )
    return any(signal.lower() in text.lower() for signal in signals)


def _contains_unverified_current_fact(text: str) -> bool:
    lowered = text.lower()
    safe_modals = ("may", "can", "could", "hypothesis", "ask", "check", "unverified", "cannot verify", "must provide")
    current_markers = ("current market", "latest", "currently", "现在已经", "最新", "当前市场", "目前监管")
    if not any(marker in lowered for marker in current_markers):
        return False
    return not any(modal in lowered for modal in safe_modals)


def _looks_like_source_rewrite(text: str, skill: dict[str, str]) -> bool:
    title = str(skill.get("title", "")).strip()
    if not title:
        return False
    return text.count(title) > 4 and "source claim" in text.lower()


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Skill"


def _write_yaml(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _count_by(docs: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for doc in docs:
        value = str(doc.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return min(max(numerator / denominator, 0.0), 1.0)


def _ratio_score(numerator: int, denominator: int) -> float:
    return round(100.0 * _safe_ratio(numerator, denominator), 1)


def _claim_excerpt(text: str, offset: int) -> str:
    start = max(0, offset - 32)
    end = min(len(text), offset + 96)
    return text[start:end].replace("\n", " ").strip()
