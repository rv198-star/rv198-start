import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SRC))

from kiu_graph.merge import merge_bundle_graphs
from kiu_graph.report import generate_graph_report


class W1AuditDeliverableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.poor_charlies_bundle = ROOT / "bundles" / "poor-charlies-almanack-v0.1"
        self.engineering_bundle = ROOT / "bundles" / "engineering-postmortem-v0.1"

    def test_generate_graph_report_lists_source_bundles_for_merged_graph(self) -> None:
        merged = merge_bundle_graphs(
            [self.poor_charlies_bundle, self.engineering_bundle]
        )

        report_text = generate_graph_report(merged)

        self.assertIn("- bundle_count: `2`", report_text)
        self.assertIn("- source_bundles:", report_text)
        self.assertIn("poor-charlies-almanack-v0.1", report_text)
        self.assertIn("engineering-postmortem-v0.1", report_text)
        self.assertIn("support_refs=", report_text)
        self.assertIn("Margin of safety sizing", report_text)
        self.assertIn("Blast radius check", report_text)

    def test_repository_contains_w1_audit_artifacts(self) -> None:
        manifest = yaml.safe_load(
            (self.poor_charlies_bundle / "manifest.yaml").read_text(encoding="utf-8")
        )
        graph_report_meta = manifest.get("graph_report", {})
        graph_report_path = self.poor_charlies_bundle / graph_report_meta.get(
            "path", "GRAPH_REPORT.md"
        )
        merged_report_path = ROOT / "reports" / "w1-merged-graph-report.md"
        audit_path = ROOT / "reports" / "w1-audit.md"

        self.assertTrue(graph_report_path.exists(), graph_report_path)
        self.assertTrue(merged_report_path.exists(), merged_report_path)
        self.assertTrue(audit_path.exists(), audit_path)

        graph_report_text = graph_report_path.read_text(encoding="utf-8")
        self.assertIn("## God Nodes", graph_report_text)
        self.assertIn("## Communities", graph_report_text)
        self.assertIn("## Surprising Connections", graph_report_text)
        self.assertIn("## Suggested Questions", graph_report_text)
        self.assertIn("Circle of competence", graph_report_text)

        merged_report_text = merged_report_path.read_text(encoding="utf-8")
        self.assertIn("poor-charlies-almanack-v0.1", merged_report_text)
        self.assertIn("engineering-postmortem-v0.1", merged_report_text)
        self.assertIn("## Communities", merged_report_text)

        audit_text = audit_path.read_text(encoding="utf-8")
        self.assertIn("Decision: GO", audit_text)
        self.assertIn("W2", audit_text)
        self.assertIn("GRAPH_REPORT.md", audit_text)
        self.assertIn("w1-merged-graph-report.md", audit_text)


if __name__ == "__main__":
    unittest.main()
