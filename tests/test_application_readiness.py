from __future__ import annotations

import unittest

from kiu_pipeline.readiness import (
    ReadinessFinding,
    ReadinessSeverity,
    ReadinessStatus,
    aggregate_readiness,
)


class ApplicationReadinessTests(unittest.TestCase):
    def test_readiness_schema_serializes_findings(self) -> None:
        finding = ReadinessFinding(
            model="coverage_model",
            severity=ReadinessSeverity.WARN,
            reason="narrow_output_without_justification",
            evidence={"coverage_unit_count": 3, "covered_unit_count": 1},
            recommended_action="run_second_seed_pass_or_record_justification",
        )

        self.assertEqual(
            finding.to_dict(),
            {
                "model": "coverage_model",
                "severity": "warn",
                "reason": "narrow_output_without_justification",
                "evidence": {"coverage_unit_count": 3, "covered_unit_count": 1},
                "recommended_action": "run_second_seed_pass_or_record_justification",
            },
        )

    def test_aggregate_keeps_warnings_visible_with_high_score(self) -> None:
        summary = aggregate_readiness(
            model="application_readiness",
            score_100=96.0,
            findings=[
                ReadinessFinding(
                    model="coverage_model",
                    severity=ReadinessSeverity.WARN,
                    reason="narrow_output_without_justification",
                    evidence={},
                    recommended_action="explain_or_expand_coverage",
                )
            ],
        )

        self.assertEqual(summary["status"], ReadinessStatus.WARN.value)
        self.assertEqual(summary["score_100"], 96.0)
        self.assertEqual(summary["warning_count"], 1)
        self.assertEqual(summary["failure_count"], 0)

    def test_aggregate_failure_dominates_warning_and_score(self) -> None:
        summary = aggregate_readiness(
            model="application_readiness",
            score_100=99.0,
            findings=[
                ReadinessFinding(
                    model="mechanism_evidence_model",
                    severity=ReadinessSeverity.FAIL,
                    reason="primary_anchor_mechanism_weak",
                    evidence={"mechanism_density_score": 0.2},
                    recommended_action="choose_stronger_primary_anchor",
                )
            ],
        )

        self.assertEqual(summary["status"], ReadinessStatus.FAIL.value)
        self.assertEqual(summary["failure_count"], 1)

    def test_aggregate_not_applicable_when_no_score_or_findings(self) -> None:
        summary = aggregate_readiness(model="transfer_fit_model", score_100=None, findings=[])

        self.assertEqual(summary["status"], ReadinessStatus.NOT_APPLICABLE.value)


if __name__ == "__main__":
    unittest.main()
