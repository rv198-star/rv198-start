import json
import os
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

from kiu_pipeline.preflight import validate_generated_bundle
from kiu_pipeline.seed import derive_candidate_metadata


class CandidatePipelineTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"

    def test_cli_generates_candidate_bundle_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_candidates.py"),
                    "--source-bundle",
                    str(self.bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "test-run",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run_root = output_root / "poor-charlies-almanack-v0.1" / "test-run"
            bundle_root = run_root / "bundle"
            manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
            metrics = json.loads((run_root / "reports" / "metrics.json").read_text(encoding="utf-8"))

            self.assertEqual(len(manifest["skills"]), 5)
            self.assertEqual(
                {entry["status"] for entry in manifest["skills"]},
                {"under_evaluation"},
            )
            self.assertEqual(metrics["summary"]["matched_gold_skills"], 5)
            self.assertEqual(metrics["summary"]["missing_gold_skills"], 0)
            self.assertEqual(metrics["summary"]["workflow_script_candidates"], 0)

            first_skill = bundle_root / manifest["skills"][0]["path"]
            self.assertTrue((first_skill / "SKILL.md").exists())
            self.assertTrue((first_skill / "anchors.yaml").exists())
            self.assertTrue((first_skill / "eval" / "summary.yaml").exists())
            self.assertTrue((first_skill / "iterations" / "revisions.yaml").exists())
            self.assertTrue((first_skill / "candidate.yaml").exists())

    def test_preflight_accepts_generated_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_candidates.py"),
                    "--source-bundle",
                    str(self.bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "preflight",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            bundle_root = output_root / "poor-charlies-almanack-v0.1" / "preflight" / "bundle"
            report = validate_generated_bundle(bundle_root)

            self.assertEqual(report["errors"], [])
            self.assertEqual(report["summary"]["skill_candidates"], 5)

    def test_build_candidates_cli_runs_autonomous_refiner_and_emits_terminal_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(self.bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "phase2-e2e",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run_root = output_root / "poor-charlies-almanack-v0.1" / "phase2-e2e"
            bundle_root = run_root / "bundle"
            candidate_doc = yaml.safe_load(
                (
                    bundle_root
                    / "skills"
                    / "circle-of-competence"
                    / "candidate.yaml"
                ).read_text(encoding="utf-8")
            )

            self.assertIn(
                candidate_doc["terminal_state"],
                {"ready_for_review", "do_not_publish", "max_rounds_reached"},
            )
            self.assertTrue((run_root / "reports" / "final-decision.json").exists())

    def test_build_candidates_cli_supports_llm_assisted_with_mock_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            env = os.environ.copy()
            env["KIU_LLM_PROVIDER"] = "mock"
            env["KIU_LLM_MOCK_RESPONSE"] = (
                "A publishable rationale should keep the refusal contract explicit and tie user confidence to a"
                " demonstrable understanding gap.[^anchor:circle-source-note] The dotcom refusal trace remains the"
                " canonical reminder that enthusiasm without decision-grade understanding is still outside the circle,"
                " and the evaluator should preserve that refusal stance even when narrative pressure or recent price"
                " action makes immediate action feel socially validated.[^trace:canonical/dotcom-refusal.yaml]"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(self.bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "phase3-llm",
                    "--drafting-mode",
                    "llm-assisted",
                    "--llm-budget-tokens",
                    "4000",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            run_root = output_root / "poor-charlies-almanack-v0.1" / "phase3-llm"
            bundle_root = run_root / "bundle"
            skill_markdown = (
                bundle_root / "skills" / "circle-of-competence" / "SKILL.md"
            ).read_text(encoding="utf-8")
            round_report = json.loads(
                (
                    run_root
                    / "reports"
                    / "rounds"
                    / "circle-of-competence-round-01.json"
                ).read_text(encoding="utf-8")
            )

            self.assertIn("publishable rationale should keep the refusal contract explicit", skill_markdown)
            self.assertEqual(round_report["llm_drafting"]["provider"], "mock")
            self.assertEqual(round_report["llm_rejections"], [])

    def test_preflight_rejects_workflow_script_candidate_inside_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            manifest_path = tmp_bundle / "manifest.yaml"
            manifest_doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest_doc["skills"][0]["status"] = "under_evaluation"
            manifest_doc["skills"][0]["skill_revision"] = 1
            manifest_path.write_text(
                yaml.safe_dump(manifest_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            skill_dir = tmp_bundle / "skills" / "circle-of-competence"
            skill_doc = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            skill_doc = skill_doc.replace("status: published", "status: under_evaluation")
            skill_doc = skill_doc.replace("skill_revision: 2", "skill_revision: 1")
            (skill_dir / "SKILL.md").write_text(skill_doc, encoding="utf-8")

            eval_path = skill_dir / "eval" / "summary.yaml"
            eval_doc = yaml.safe_load(eval_path.read_text(encoding="utf-8"))
            eval_doc["status"] = "under_evaluation"
            eval_doc["skill_revision"] = 1
            eval_path.write_text(
                yaml.safe_dump(eval_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            rev_path = skill_dir / "iterations" / "revisions.yaml"
            rev_doc = yaml.safe_load(rev_path.read_text(encoding="utf-8"))
            rev_doc["current_revision"] = 1
            rev_doc["history"] = rev_doc["history"][:1]
            rev_path.write_text(
                yaml.safe_dump(rev_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            candidate_path = skill_dir / "candidate.yaml"
            candidate_doc = {
                "candidate_id": "circle-of-competence",
                "source_bundle_id": "poor-charlies-almanack-v0.1",
                "source_graph_hash": manifest_doc["graph"]["graph_hash"],
                "candidate_kind": "workflow_script",
                "workflow_certainty": "high",
                "context_certainty": "high",
                "recommended_execution_mode": "workflow_script",
                "disposition": "workflow_script_candidate",
                "drafting_mode": "deterministic",
                "seed": {
                    "primary_node_id": "n_circle_principle",
                    "supporting_node_ids": [],
                    "supporting_edge_ids": [],
                    "community_ids": [],
                },
            }
            candidate_path.write_text(
                yaml.safe_dump(candidate_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            report = validate_generated_bundle(tmp_bundle)

            self.assertTrue(
                any("workflow_script_candidate" in error for error in report["errors"])
            )

    def test_high_high_certainty_downgrades_to_workflow_candidate(self) -> None:
        metadata = derive_candidate_metadata(
            candidate_id="synthetic-task",
            seed_node_id="n_synthetic",
            candidate_kind="workflow_script",
            graph_hash="sha256:test",
            bundle_id="synthetic",
            routing_profile={
                "candidate_kinds": {
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    }
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    }
                ],
            },
        )

        self.assertEqual(metadata["workflow_certainty"], "high")
        self.assertEqual(metadata["context_certainty"], "high")
        self.assertEqual(metadata["recommended_execution_mode"], "workflow_script")
        self.assertEqual(metadata["disposition"], "workflow_script_candidate")


if __name__ == "__main__":
    unittest.main()
