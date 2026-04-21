import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_validator.core import validate_bundle


class BundleValidationTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"

    def test_bundle_validates_without_errors(self) -> None:
        report = validate_bundle(self.bundle_path)

        self.assertEqual(report["errors"], [])
        self.assertEqual(report["manifest"]["bundle_version"], "0.1.0")
        self.assertEqual(len(report["skills"]), 5)
        self.assertEqual(
            {skill["skill_id"] for skill in report["skills"]},
            {
                "circle-of-competence",
                "invert-the-problem",
                "margin-of-safety-sizing",
                "bias-self-audit",
                "opportunity-cost-of-the-next-best-idea",
            },
        )

    def test_bundle_has_shared_graph_trace_and_evaluation_assets(self) -> None:
        report = validate_bundle(self.bundle_path)

        self.assertGreaterEqual(report["graph"]["node_count"], 10)
        self.assertGreaterEqual(report["graph"]["edge_count"], 5)
        self.assertGreaterEqual(report["shared_assets"]["trace_count"], 12)
        self.assertEqual(report["shared_assets"]["evaluation_count"], 50)
        self.assertEqual(
            report["shared_assets"]["evaluation_breakdown"],
            {
                "real_decisions": 20,
                "synthetic_adversarial": 20,
                "out_of_distribution": 10,
            },
        )

    def test_one_skill_demonstrates_revision_plus_one_loop(self) -> None:
        report = validate_bundle(self.bundle_path)
        circle = next(
            skill
            for skill in report["skills"]
            if skill["skill_id"] == "circle-of-competence"
        )

        self.assertEqual(circle["status"], "published")
        self.assertEqual(circle["skill_revision"], 2)
        self.assertGreaterEqual(circle["revision_entry_count"], 2)
        self.assertTrue(circle["has_revision_loop"])

    def test_full_release_marks_all_five_skills_as_published(self) -> None:
        report = validate_bundle(self.bundle_path)

        self.assertEqual(len(report["skills"]), 5)
        for skill in report["skills"]:
            self.assertEqual(skill["status"], "published")
            self.assertGreaterEqual(skill["skill_revision"], 2)
            self.assertGreaterEqual(skill["usage_trace_count"], 3)
            self.assertTrue(skill["all_eval_subsets_pass"])

    def test_validator_rejects_missing_source_anchor_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            anchors_path = (
                tmp_bundle
                / "skills"
                / "circle-of-competence"
                / "anchors.yaml"
            )
            anchors_doc = yaml.safe_load(anchors_path.read_text(encoding="utf-8"))
            anchors_doc["source_anchor_sets"] = []
            anchors_path.write_text(
                yaml.safe_dump(anchors_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any("source/scenario anchor" in error for error in report["errors"])
            )

    def test_validator_rejects_graph_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            manifest_path = tmp_bundle / "manifest.yaml"
            manifest_doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest_doc["graph"]["graph_hash"] = "sha256:deadbeef"
            manifest_path.write_text(
                yaml.safe_dump(manifest_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any("graph_hash" in error for error in report["errors"])
            )

    def test_cli_reports_success_for_reference_bundle(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_bundle.py"),
                str(self.bundle_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALID", result.stdout)

    def test_release_has_usage_guide_with_design_rationale(self) -> None:
        usage_guide = ROOT / "docs" / "usage-guide.md"
        self.assertTrue(usage_guide.exists())

        content = usage_guide.read_text(encoding="utf-8")
        self.assertIn("# KiU v0.1 Usage Guide", content)
        self.assertIn("## Quick Start", content)
        self.assertIn("## Repository Layout", content)
        self.assertIn("## How To Read A Skill", content)
        self.assertIn("## How To Extend The Bundle", content)
        self.assertIn("## Design Rationale", content)


if __name__ == "__main__":
    unittest.main()
