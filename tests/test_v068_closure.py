import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from kiu_pipeline.extraction_bundle import _build_scenario_families

ROOT = Path(__file__).resolve().parents[1]


class V068ClosureTests(unittest.TestCase):
    def test_historical_consequence_scenario_families_cover_positive_edge_refusal(self) -> None:
        families = _build_scenario_families(
            candidate_id="historical-case-consequence-judgment",
            title="Historical Case Consequence Judgment",
            descriptors=[{"anchor_id": "a1"}],
        )
        total = sum(len(items) for items in families.values())
        self.assertGreaterEqual(total, 5)
        self.assertGreaterEqual(len(families.get("should_trigger", [])), 2)
        self.assertGreaterEqual(len(families.get("edge_case", [])), 1)
        self.assertGreaterEqual(len(families.get("refusal", [])), 2)
        scenario_ids = {item["scenario_id"] for items in families.values() for item in items}
        self.assertIn("short-gain-long-cost-stress-test", scenario_ids)
        self.assertIn("workflow-or-template-request", scenario_ids)

    def test_control_style_pack_is_cangjie_redacted(self) -> None:
        root = ROOT / "reports" / "blind-review-packs" / "v0.6.7-shiji-control-style-B"
        self.assertTrue(root.exists())
        for path in root.iterdir():
            if path.is_file():
                self.assertNotIn("cangjie", path.read_text(encoding="utf-8").lower(), path.name)

    def test_audit_boundary_coverage_reports_pass_for_clean_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out = Path(tmp_dir) / "coverage.md"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "audit_boundary_coverage.py"),
                    "--review-cases",
                    str(ROOT / "tests" / "fixtures" / "v067-blind-review-cases.yaml"),
                    "--review-pack",
                    str(ROOT / "reports" / "blind-review-packs" / "v0.6.7-multimodel-clean" / "clean-pack.json"),
                    "--output",
                    str(out),
                    "--min-coverage",
                    "0.85",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertGreaterEqual(payload["coverage_ratio"], 0.85)
            self.assertTrue(out.exists())

    def test_run_blind_review_reference_source_modes(self) -> None:
        for mode in ("internal-mock", "upstream-cangjie", "none"):
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_blind_review.py"), "--reference-source", mode],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["reference_source"], mode)
            self.assertTrue(payload["ready"])


if __name__ == "__main__":
    unittest.main()
