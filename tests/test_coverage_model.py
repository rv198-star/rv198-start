from __future__ import annotations

import unittest

from kiu_pipeline.coverage_model import build_coverage_report


class CoverageModelTests(unittest.TestCase):
    def test_warns_when_multiple_high_density_units_have_narrow_output_without_justification(self) -> None:
        report = build_coverage_report(
            graph_doc=_graph_with_units(
                [
                    ("community::business", "business responsibility", 8),
                    ("community::workflow", "workflow sequencing", 7),
                    ("community::risk", "risk boundary", 6),
                ]
            ),
            published_skill_ids=["business-first-subsystem-decomposition"],
            workflow_candidate_ids=[],
            gateway_routes=[],
            narrow_output_justification="",
        )

        self.assertEqual(report["readiness"]["status"], "warn")
        self.assertEqual(len(report["coverage_units"]), 3)
        self.assertEqual(report["covered_unit_count"], 1)
        self.assertEqual(report["uncovered_unit_count"], 2)
        self.assertIn("narrow_output_without_justification", {f["reason"] for f in report["readiness"]["findings"]})

    def test_single_artifact_can_pass_when_narrow_output_is_model_justified(self) -> None:
        report = build_coverage_report(
            graph_doc=_graph_with_units(
                [
                    ("community::single", "single dominant operating principle", 9),
                    ("community::appendix", "appendix examples", 2),
                ]
            ),
            published_skill_ids=["dominant-operating-principle"],
            workflow_candidate_ids=[],
            gateway_routes=[],
            narrow_output_justification="One high-density unit dominates; lower-density appendix is source context only.",
        )

        self.assertEqual(report["readiness"]["status"], "pass")
        self.assertEqual(report["uncovered_unit_count"], 0)

    def test_workflow_candidates_count_as_coverage_only_with_gateway_route(self) -> None:
        graph_doc = _graph_with_units(
            [
                ("community::agentic", "judgment boundary", 8),
                ("community::workflow", "repeatable workflow", 8),
            ]
        )

        without_gateway = build_coverage_report(
            graph_doc=graph_doc,
            published_skill_ids=["judgment-boundary"],
            workflow_candidate_ids=["repeatable-workflow"],
            gateway_routes=[],
            narrow_output_justification="",
        )
        with_gateway = build_coverage_report(
            graph_doc=graph_doc,
            published_skill_ids=["judgment-boundary"],
            workflow_candidate_ids=["repeatable-workflow"],
            gateway_routes=["repeatable-workflow"],
            narrow_output_justification="",
        )

        self.assertEqual(without_gateway["covered_unit_count"], 1)
        self.assertEqual(without_gateway["readiness"]["status"], "warn")
        self.assertEqual(with_gateway["covered_unit_count"], 2)
        self.assertEqual(with_gateway["readiness"]["status"], "pass")

    def test_artifact_text_anchors_can_cover_source_communities_when_ids_are_abstract(self) -> None:
        report = build_coverage_report(
            graph_doc=_graph_with_units(
                [
                    ("community::xiangyu", "卷七 项羽本纪第七", 8),
                    ("community::role", "角色边界 判断", 8),
                ]
            ),
            published_skill_ids=["historical-analogy-transfer-gate", "role-boundary-before-action"],
            workflow_candidate_ids=[],
            gateway_routes=[],
            artifact_texts={
                "historical-analogy-transfer-gate": "source anchor: 项羽本纪第七 contains action, constraint, and consequence evidence.",
                "role-boundary-before-action": "角色边界 judgment asks whether authority and action boundary match.",
            },
            narrow_output_justification="",
        )

        self.assertEqual(report["covered_unit_count"], 2)
        self.assertEqual(report["readiness"]["status"], "pass")


def _graph_with_units(units: list[tuple[str, str, int]]) -> dict[str, object]:
    return {
        "communities": [
            {"id": community_id, "label": label, "node_ids": [f"{community_id}::node::{i}" for i in range(node_count)]}
            for community_id, label, node_count in units
        ]
    }


if __name__ == "__main__":
    unittest.main()
