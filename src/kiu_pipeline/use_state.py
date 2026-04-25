from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UseState(str, Enum):
    SOURCE_UNDERSTANDING = "source_understanding"
    LOW_RISK_REFLECTION = "low_risk_reflection"
    BOUNDED_APPLICATION = "bounded_application"
    CONTEXT_INSUFFICIENT = "context_insufficient"
    TRANSFER_CANDIDATE = "transfer_candidate"
    TRANSFER_ABUSE_RISK = "transfer_abuse_risk"
    CURRENT_FACT_REQUIRED = "current_fact_required"


@dataclass(frozen=True)
class UseStateDecision:
    use_state: UseState
    reasons: list[str]
    confidence: str = "medium"

    def to_dict(self) -> dict[str, object]:
        return {
            "use_state": self.use_state.value,
            "reasons": list(self.reasons),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class EvidenceState:
    direct_apply_allowed: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "direct_apply_allowed": self.direct_apply_allowed,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class FinalVerdict:
    final_verdict: str
    use_state: UseState
    world_intervention_level: str
    reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "final_verdict": self.final_verdict,
            "use_state": self.use_state.value,
            "world_intervention_level": self.world_intervention_level,
            "reasons": list(self.reasons),
        }


def classify_use_state(prompt: str) -> UseStateDecision:
    text = _normalize(prompt)
    reasons: list[str] = []

    if _has_any(text, _TRANSFER_ABUSE_MARKERS):
        reasons.append("transfer_abuse_marker")
        return UseStateDecision(UseState.TRANSFER_ABUSE_RISK, reasons, "high")

    if _has_any(text, _SOURCE_UNDERSTANDING_MARKERS):
        reasons.append("source_understanding_marker")
        return UseStateDecision(UseState.SOURCE_UNDERSTANDING, reasons, "high")

    if _has_any(text, _LOW_RISK_REFLECTION_MARKERS):
        reasons.append("low_risk_reflection_marker")
        return UseStateDecision(UseState.LOW_RISK_REFLECTION, reasons, "high")

    if _has_any(text, _CURRENT_FACT_MARKERS):
        reasons.append("current_fact_marker")
        return UseStateDecision(UseState.CURRENT_FACT_REQUIRED, reasons, "high")

    if _has_any(text, _CONTEXT_INSUFFICIENT_MARKERS):
        reasons.append("context_insufficient_marker")
        return UseStateDecision(UseState.CONTEXT_INSUFFICIENT, reasons, "high")

    if _has_any(text, _TRANSFER_CANDIDATE_MARKERS):
        reasons.append("transfer_candidate_marker")
        return UseStateDecision(UseState.TRANSFER_CANDIDATE, reasons, "high")

    if _has_any(text, _BOUNDED_APPLICATION_MARKERS):
        reasons.append("bounded_application_marker")
        return UseStateDecision(UseState.BOUNDED_APPLICATION, reasons, "medium")

    reasons.append("default_context_insufficient")
    return UseStateDecision(UseState.CONTEXT_INSUFFICIENT, reasons, "low")


def evaluate_evidence_sufficiency(
    *,
    use_state: UseState,
    mechanism_mapping_present: bool,
    transfer_conditions_present: bool,
    anti_conditions_present: bool,
    verified_current_fact_present: bool,
) -> EvidenceState:
    reasons: list[str] = []
    if use_state == UseState.TRANSFER_CANDIDATE:
        if not mechanism_mapping_present:
            reasons.append("mechanism_mapping_missing")
        if not transfer_conditions_present:
            reasons.append("transfer_conditions_missing")
        if not anti_conditions_present:
            reasons.append("anti_conditions_missing")
    if use_state == UseState.CURRENT_FACT_REQUIRED and not verified_current_fact_present:
        reasons.append("verified_current_fact_missing")
    if use_state in {
        UseState.SOURCE_UNDERSTANDING,
        UseState.CONTEXT_INSUFFICIENT,
        UseState.TRANSFER_ABUSE_RISK,
    }:
        reasons.append(f"{use_state.value}_blocks_direct_apply")
    return EvidenceState(direct_apply_allowed=not reasons, reasons=reasons)


def compose_final_verdict(
    *,
    use_state: UseState,
    source_verdict: str,
    evidence_state: EvidenceState,
    verified_current_fact_present: bool,
) -> FinalVerdict:
    reasons = list(evidence_state.reasons)
    if use_state == UseState.SOURCE_UNDERSTANDING:
        return FinalVerdict("do_not_apply", use_state, "minimal", reasons or ["source_understanding_routes_to_source_layer"])
    if use_state == UseState.CURRENT_FACT_REQUIRED:
        if verified_current_fact_present and evidence_state.direct_apply_allowed:
            return FinalVerdict("apply_with_caveats", use_state, "strong_gate", reasons or ["verified_current_fact_present"])
        return FinalVerdict("ask_more_context", use_state, "strong_gate", reasons or ["verified_current_fact_required"])
    if use_state == UseState.TRANSFER_ABUSE_RISK:
        return FinalVerdict("refuse", use_state, "strong_gate", reasons or ["transfer_abuse_risk"])
    if use_state == UseState.CONTEXT_INSUFFICIENT:
        return FinalVerdict("ask_more_context", use_state, "moderate", reasons or ["context_insufficient"])
    if use_state == UseState.TRANSFER_CANDIDATE and not evidence_state.direct_apply_allowed:
        return FinalVerdict("ask_more_context", use_state, "moderate", reasons or ["transfer_evidence_incomplete"])
    if use_state == UseState.LOW_RISK_REFLECTION:
        return FinalVerdict("apply_with_caveats", use_state, "light", reasons or ["low_risk_reflection_non_dilution"])
    if use_state == UseState.BOUNDED_APPLICATION and evidence_state.direct_apply_allowed and source_verdict == "apply":
        return FinalVerdict("apply", use_state, "minimal", reasons or ["bounded_application_evidence_sufficient"])
    if evidence_state.direct_apply_allowed and source_verdict == "apply":
        return FinalVerdict("apply_with_caveats", use_state, "light", reasons or ["default_caveated_apply"])
    return FinalVerdict("ask_more_context", use_state, "moderate", reasons or ["default_ask_more_context"])


def _normalize(prompt: str) -> str:
    return prompt.strip().lower()


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker.lower() in text for marker in markers)


_SOURCE_UNDERSTANDING_MARKERS = (
    "总结",
    "翻译",
    "解释一下",
    "解释",
    "什么意思",
    "人物介绍",
    "主要观点",
    "定义",
)

_CURRENT_FACT_MARKERS = (
    "最新",
    "当前政策",
    "当前法规",
    "法规现在",
    "现在是否",
    "成交量",
    "该买吗",
    "该买",
    "该卖",
    "目标价",
    "是否已经生效",
)

_TRANSFER_ABUSE_MARKERS = (
    "照做",
    "照搬",
    "直接复制",
    "直接按书执行",
    "不用再分析",
    "不要再分析",
    "大公司都这么做",
    "竞品这样做成功",
    "书里这样做成功",
)

_CONTEXT_INSUFFICIENT_MARKERS = (
    "没有调查",
    "今天拍板",
    "不要问上下文",
    "直接替我决定",
    "只有一个粗",
    "还不知道",
    "能直接",
    "证据互相冲突",
    "急着要结论",
    "上下文不完整",
)

_LOW_RISK_REFLECTION_MARKERS = (
    "有什么启发",
    "帮助我反思",
    "借古自省",
    "日常思考",
    "不需要做现实决策",
)

_TRANSFER_CANDIDATE_MARKERS = (
    "能不能借鉴",
    "能否迁移",
    "迁移到",
    "像不像",
    "历史案例",
    "这个故事",
    "这个案例",
    "借鉴到",
)

_BOUNDED_APPLICATION_MARKERS = (
    "具体决策",
    "明显取舍",
    "是否应该采用这个原则",
    "下一步是否应该采用",
    "是否应该调整",
    "是否应该先",
    "下一步该如何",
    "下一步分析",
    "估值论证",
    "应该检查哪些证据",
    "独立经营事实",
    "挑战这个说法",
    "已经列出",
    "责任不清",
    "用户和失败后果已经明确",
    "已有完整",
    "已有一线访谈",
    "已列出",
    "风险边界",
    "下一步如何",
)
