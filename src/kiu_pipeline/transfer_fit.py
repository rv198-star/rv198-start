from __future__ import annotations

from typing import Any

from .use_state import UseState


TRANSFER_FIT_SCHEMA = "kiu.transfer-fit/v0.1"


def build_transfer_fit_report(
    *,
    use_state: UseState | str,
    mechanism_summary: str,
    transfer_conditions: list[str],
    anti_conditions: list[str],
    current_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = UseState(use_state)
    if state == UseState.LOW_RISK_REFLECTION:
        return _not_applicable(intervention_level="minimal")
    if state not in {UseState.TRANSFER_CANDIDATE, UseState.TRANSFER_ABUSE_RISK}:
        return _not_applicable(intervention_level="light")

    context = current_context or {}
    dimensions = _transfer_dimensions(
        mechanism_summary=mechanism_summary,
        transfer_conditions=transfer_conditions,
        anti_conditions=anti_conditions,
    )
    ready = bool(context.get("mechanism_fit")) and bool(context.get("anti_conditions_checked"))
    intervention_level = "moderate" if state == UseState.TRANSFER_CANDIDATE else "strong_gate"
    return {
        "schema_version": TRANSFER_FIT_SCHEMA,
        "use_state": state.value,
        "transfer_readiness": "ready" if ready else "ask_more_context",
        "intervention_level": intervention_level,
        "dimensions": dimensions,
        "fit_questions": [] if ready else _fit_questions(dimensions),
        "mismatch_questions": [] if ready else _mismatch_questions(dimensions),
        "disconfirming_evidence_questions": [] if ready else _disconfirming_questions(dimensions),
        "claim_boundary": "Internal transfer-fit prompting model; not external validation or factual verification.",
    }


def _not_applicable(*, intervention_level: str) -> dict[str, Any]:
    return {
        "schema_version": TRANSFER_FIT_SCHEMA,
        "transfer_readiness": "not_applicable",
        "intervention_level": intervention_level,
        "dimensions": {},
        "fit_questions": [],
        "mismatch_questions": [],
        "disconfirming_evidence_questions": [],
        "claim_boundary": "Transfer-fit checks are skipped for this use state.",
    }


def _transfer_dimensions(
    *,
    mechanism_summary: str,
    transfer_conditions: list[str],
    anti_conditions: list[str],
) -> dict[str, bool]:
    text = " ".join([mechanism_summary, *transfer_conditions, *anti_conditions]).lower()
    return {
        "mechanism_mapping": _has_any(text, ("mechanism", "机制", "actor", "action", "consequence", "因果")),
        "incentive_fit": _has_any(text, ("incentive", "激励", "利益", "motivation")),
        "authority_fit": _has_any(text, ("authority", "权限", "授权", "role", "boundary", "边界")),
        "constraint_fit": _has_any(text, ("constraint", "约束", "resource", "资源", "condition", "条件")),
        "time_horizon_fit": _has_any(text, ("time", "horizon", "长期", "短期", "周期")),
        "anti_condition_coverage": bool(anti_conditions),
        "disconfirming_evidence": _has_any(text, ("disconfirm", "反证", "counter", "counter-evidence", "反例")),
    }


def _fit_questions(dimensions: dict[str, bool]) -> list[str]:
    questions = ["Which current mechanism matches the source mechanism chain, and which step is only superficially similar?"]
    if dimensions.get("incentive_fit"):
        questions.append("Do the current incentives match the source incentives, or would actors respond differently?")
    else:
        questions.append("What incentive structure must be checked before transferring this source lesson?")
    if dimensions.get("authority_fit") or dimensions.get("constraint_fit"):
        questions.append("What authority, resource, and constraint boundaries are the same or different in the current context?")
    return questions


def _mismatch_questions(dimensions: dict[str, bool]) -> list[str]:
    questions = ["Which mechanism, incentive, authority, or constraint mismatch would make the transfer unsafe?"]
    if not dimensions.get("time_horizon_fit"):
        questions.append("What time horizon could change the expected consequence path?")
    if dimensions.get("anti_condition_coverage"):
        questions.append("Which anti-condition is most likely to apply here, and what evidence would show it?")
    return questions


def _disconfirming_questions(dimensions: dict[str, bool]) -> list[str]:
    if dimensions.get("disconfirming_evidence"):
        return ["What disconfirming evidence or counterexample has been checked before using this analogy?"]
    return ["What disconfirming evidence would make this transfer a warning only rather than an action guide?"]


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
