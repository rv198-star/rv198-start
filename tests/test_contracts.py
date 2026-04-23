import unittest

from kiu_pipeline.contracts import build_semantic_contract


class SemanticContractTests(unittest.TestCase):
    def test_circle_of_competence_source_note_uses_family_specific_contract(self) -> None:
        contract = build_semantic_contract(candidate_id="circle-of-competence-source-note")

        self.assertIn(
            "user_claiming_should_be_able_to_figure_it_out",
            contract["trigger"]["patterns"],
        )
        self.assertIn("objective_comparison_request", contract["trigger"]["exclusions"])
        self.assertIn(
            "recommended_action",
            contract["judgment_schema"]["output"]["schema"],
        )
        self.assertEqual(
            contract["judgment_schema"]["output"]["schema"]["verdict"],
            "enum[in_circle|edge_of_circle|outside_circle]",
        )

    def test_bias_self_audit_source_note_uses_research_and_incident_boundaries(self) -> None:
        contract = build_semantic_contract(candidate_id="bias-self-audit-source-note")

        self.assertIn("early_research_only", contract["trigger"]["exclusions"])
        self.assertIn("urgent_incident_response", contract["trigger"]["exclusions"])
        self.assertIn(
            "audit_mode",
            contract["judgment_schema"]["output"]["schema"],
        )
        self.assertIn(
            "mitigation_actions",
            contract["judgment_schema"]["output"]["schema"],
        )
        self.assertIn("next_action", contract["judgment_schema"]["output"]["schema"])

    def test_invert_the_problem_source_note_has_edge_posture_output(self) -> None:
        contract = build_semantic_contract(candidate_id="invert-the-problem-source-note")

        self.assertIn("pure_brainstorming_only", contract["trigger"]["exclusions"])
        self.assertIn("edge_posture", contract["judgment_schema"]["output"]["schema"])
        self.assertIn("avoid_rules", contract["judgment_schema"]["output"]["schema"])

    def test_margin_of_safety_source_note_has_applicability_mode(self) -> None:
        contract = build_semantic_contract(candidate_id="margin-of-safety-sizing-source-note")

        self.assertIn("short_term_trading_request", contract["trigger"]["exclusions"])
        self.assertIn(
            "applicability_mode",
            contract["judgment_schema"]["output"]["schema"],
        )
        self.assertIn("sizing_band", contract["judgment_schema"]["output"]["schema"])
        self.assertIn("next_action", contract["judgment_schema"]["output"]["schema"])


if __name__ == "__main__":
    unittest.main()
