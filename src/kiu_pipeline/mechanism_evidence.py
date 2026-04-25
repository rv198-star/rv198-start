from __future__ import annotations

from typing import Any


DIMENSIONS = (
    "actor_present",
    "action_present",
    "constraint_present",
    "consequence_present",
    "counter_signal_present",
    "mechanism_bridge_present",
    "supports_transfer_conditions",
    "supports_anti_conditions",
)


def score_mechanism_evidence(text: str) -> dict[str, Any]:
    normalized = str(text or "").strip().lower()
    dimensions = {
        "actor_present": _has_any(normalized, ("团队", "负责人", "用户", "业务方", "组织", "公司", "管理者", "actor", "team", "user")),
        "action_present": _has_any(normalized, ("调查", "访谈", "识别", "调整", "决定", "行动", "执行", "检查", "apply", "decide")),
        "constraint_present": _has_any(normalized, ("约束", "边界", "条件", "资源", "权限", "限制", "constraint", "boundary")),
        "consequence_present": _has_any(normalized, ("导致", "后果", "下降", "提升", "失败", "风险", "返工", "consequence", "result")),
        "counter_signal_present": _has_any(normalized, ("反证", "反例", "否则", "但", "冲突", "counter", "disconfirm")),
        "mechanism_bridge_present": _has_any(normalized, ("因为", "所以", "再", "后来", "从而", "因此", "therefore", "because")),
        "supports_transfer_conditions": _has_any(normalized, ("条件", "适用", "迁移", "借鉴", "fit", "transfer")),
        "supports_anti_conditions": _has_any(normalized, ("不", "不能", "反证", "边界", "除非", "anti", "misuse")),
    }
    raw_score = sum(1 for value in dimensions.values() if value) / len(DIMENSIONS)
    if _looks_like_context_only(normalized):
        raw_score = min(raw_score, 0.45)
    if not (dimensions["actor_present"] and dimensions["action_present"] and dimensions["mechanism_bridge_present"]):
        raw_score = min(raw_score, 0.65)
    return {
        "schema_version": "kiu.mechanism-evidence/v0.1",
        "mechanism_density_score": round(raw_score, 4),
        "dimensions": dimensions,
        "mechanism_density_reason": _reason(dimensions, raw_score),
    }


def decide_anchor_role(score: dict[str, Any]) -> dict[str, Any]:
    density = float(score.get("mechanism_density_score", 0.0) or 0.0)
    dimensions = score.get("dimensions", {}) if isinstance(score.get("dimensions"), dict) else {}
    if density >= 0.75:
        role = "primary"
        allowed = True
        reason = "mechanism_dense_primary_anchor"
    elif density >= 0.35 and any(dimensions.get(key) for key in ("constraint_present", "consequence_present", "supports_anti_conditions")):
        role = "supporting"
        allowed = False
        reason = "supporting_context_not_primary_proof"
    else:
        role = "source_context_only"
        allowed = False
        reason = "mechanism_density_below_primary_threshold"
    return {
        "schema_version": "kiu.anchor-role/v0.1",
        "primary_anchor_allowed": allowed,
        "anchor_role": role,
        "reason": reason,
        "mechanism_density_score": density,
    }


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _looks_like_context_only(text: str) -> bool:
    stripped = text.strip()
    return bool(
        stripped.startswith("## ")
        or "注释" in stripped
        or "目录" in stripped
        or stripped.count("、") >= 4 and not _has_any(stripped, ("导致", "风险", "约束"))
    )


def _reason(dimensions: dict[str, bool], score: float) -> str:
    present = [key for key, value in dimensions.items() if value]
    if score >= 0.75:
        return "evidence_contains_transferable_mechanism_chain:" + ",".join(present)
    if score >= 0.35:
        return "evidence_supports_context_but_not_full_mechanism:" + ",".join(present)
    return "evidence_is_mechanism_weak:" + ",".join(present)
