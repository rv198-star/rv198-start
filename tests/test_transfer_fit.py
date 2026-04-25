from __future__ import annotations

import unittest

from kiu_pipeline.transfer_fit import build_transfer_fit_report
from kiu_pipeline.use_state import UseState


class TransferFitTests(unittest.TestCase):
    def test_transfer_candidate_gets_specific_constraint_questions(self) -> None:
        report = build_transfer_fit_report(
            use_state=UseState.TRANSFER_CANDIDATE,
            mechanism_summary="A team borrowed a past case only after matching incentives, authority, constraints, and downside evidence.",
            transfer_conditions=["same incentive structure", "similar authority boundary"],
            anti_conditions=["single case overreach", "missing disconfirming evidence"],
        )

        questions = report["fit_questions"] + report["mismatch_questions"] + report["disconfirming_evidence_questions"]
        self.assertEqual(report["transfer_readiness"], "ask_more_context")
        self.assertGreaterEqual(len(questions), 3)
        self.assertTrue(any("mechanism" in question.lower() or "机制" in question for question in questions))
        self.assertTrue(any("incentive" in question.lower() or "激励" in question for question in questions))
        self.assertTrue(any("disconfirm" in question.lower() or "反证" in question for question in questions))

    def test_ready_transfer_requires_conditions_and_anti_conditions(self) -> None:
        report = build_transfer_fit_report(
            use_state=UseState.TRANSFER_CANDIDATE,
            mechanism_summary="Actor, action, constraint, and consequence are mapped to the current decision.",
            transfer_conditions=["same actor authority", "same consequence path"],
            anti_conditions=["no single-case overreach", "counter-evidence checked"],
            current_context={"mechanism_fit": True, "anti_conditions_checked": True},
        )

        self.assertEqual(report["transfer_readiness"], "ready")

    def test_low_risk_reflection_is_not_forced_into_transfer_fit(self) -> None:
        report = build_transfer_fit_report(
            use_state=UseState.LOW_RISK_REFLECTION,
            mechanism_summary="A principle helps the user reflect on personal boundaries.",
            transfer_conditions=[],
            anti_conditions=[],
        )

        self.assertEqual(report["transfer_readiness"], "not_applicable")
        self.assertEqual(report["fit_questions"], [])
        self.assertEqual(report["intervention_level"], "minimal")


if __name__ == "__main__":
    unittest.main()
