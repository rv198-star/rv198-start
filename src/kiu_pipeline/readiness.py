from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReadinessStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class ReadinessSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    FAIL = "fail"


@dataclass(frozen=True)
class ReadinessFinding:
    model: str
    severity: ReadinessSeverity
    reason: str
    evidence: dict[str, Any]
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "severity": self.severity.value,
            "reason": self.reason,
            "evidence": dict(self.evidence),
            "recommended_action": self.recommended_action,
        }


def aggregate_readiness(
    *,
    model: str,
    score_100: float | None,
    findings: list[ReadinessFinding],
) -> dict[str, Any]:
    failure_count = sum(1 for finding in findings if finding.severity == ReadinessSeverity.FAIL)
    warning_count = sum(1 for finding in findings if finding.severity == ReadinessSeverity.WARN)
    if failure_count:
        status = ReadinessStatus.FAIL
    elif warning_count:
        status = ReadinessStatus.WARN
    elif score_100 is None and not findings:
        status = ReadinessStatus.NOT_APPLICABLE
    else:
        status = ReadinessStatus.PASS
    return {
        "schema_version": "kiu.application-readiness/v0.1",
        "model": model,
        "status": status.value,
        "score_100": None if score_100 is None else round(float(score_100), 1),
        "warning_count": warning_count,
        "failure_count": failure_count,
        "findings": [finding.to_dict() for finding in findings],
        "claim_boundary": "Internal readiness model evidence; not external validation or domain-expert review.",
    }
