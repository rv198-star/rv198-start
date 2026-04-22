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
from kiu_pipeline.load import extract_yaml_section, parse_sections
from kiu_pipeline.local_paths import resolve_output_root


class CandidatePipelineTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"
        self.example_fixture_paths = [
            ROOT / "examples" / "fixtures" / "effective-requirements-analysis.yaml",
            ROOT / "examples" / "fixtures" / "financial-statement-analysis.yaml",
        ]

    def _generate_fixture_bundle(
        self,
        *,
        fixture_path: Path,
        tmp_root: Path,
    ) -> tuple[dict, Path]:
        source_root = tmp_root / "sources" / fixture_path.stem
        output_root = tmp_root / "generated"
        scaffold = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "scaffold_example_bundle.py"),
                "--fixture",
                str(fixture_path),
                "--output-root",
                str(source_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)

        bundle_root = source_root / "bundle"
        source_manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
        generated = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "generate_candidates.py"),
                "--source-bundle",
                str(bundle_root),
                "--output-root",
                str(output_root),
                "--run-id",
                fixture_path.stem,
                "--drafting-mode",
                "deterministic",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)

        generated_bundle = (
            output_root
            / source_manifest["bundle_id"]
            / fixture_path.stem
            / "bundle"
        )
        fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
        return fixture, generated_bundle

    def test_local_output_root_resolver_uses_fixed_default_and_env_override(self) -> None:
        self.assertEqual(
            resolve_output_root(None, bucket="generated"),
            Path("/tmp/kiu-local-artifacts/generated"),
        )
        original = os.environ.get("KIU_LOCAL_OUTPUT_ROOT")
        try:
            os.environ["KIU_LOCAL_OUTPUT_ROOT"] = "/tmp/kiu-custom-root"
            self.assertEqual(
                resolve_output_root(None, bucket="sources"),
                Path("/tmp/kiu-custom-root/sources"),
            )
        finally:
            if original is None:
                os.environ.pop("KIU_LOCAL_OUTPUT_ROOT", None)
            else:
                os.environ["KIU_LOCAL_OUTPUT_ROOT"] = original

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

    def test_example_fixtures_can_generate_independent_candidate_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            for fixture_path in self.example_fixture_paths:
                with self.subTest(fixture=fixture_path.name):
                    _, generated_bundle = self._generate_fixture_bundle(
                        fixture_path=fixture_path,
                        tmp_root=tmp_root,
                    )
                    report = validate_generated_bundle(generated_bundle)
                    self.assertEqual(report["errors"], [], report["errors"])

                    manifest = yaml.safe_load(
                        (generated_bundle / "manifest.yaml").read_text(encoding="utf-8")
                    )
                    self.assertGreaterEqual(len(manifest["skills"]), 2)

                    first_skill_dir = generated_bundle / manifest["skills"][0]["path"]
                    anchors = yaml.safe_load(
                        (first_skill_dir / "anchors.yaml").read_text(encoding="utf-8")
                    )
                    self.assertTrue(anchors["source_anchor_sets"], fixture_path.name)

    def test_example_fixture_candidates_use_seeded_quality_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            for fixture_path in self.example_fixture_paths:
                with self.subTest(fixture=fixture_path.name):
                    fixture, generated_bundle = self._generate_fixture_bundle(
                        fixture_path=fixture_path,
                        tmp_root=tmp_root,
                    )
                    report = validate_generated_bundle(generated_bundle)
                    self.assertEqual(report["errors"], [], report["errors"])
                    self.assertEqual(report["warnings"], [], report["warnings"])

                    for node in fixture["nodes"]:
                        with self.subTest(skill=node["candidate_id"]):
                            skill_seed = node["skill_seed"]
                            skill_dir = generated_bundle / "skills" / node["candidate_id"]
                            skill_markdown = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                            sections = parse_sections(skill_markdown)
                            contract = extract_yaml_section(sections["Contract"])
                            relations = extract_yaml_section(sections["Relations"])
                            usage_summary = sections["Usage Summary"]
                            eval_summary = yaml.safe_load(
                                (skill_dir / "eval" / "summary.yaml").read_text(encoding="utf-8")
                            )

                            self.assertEqual(contract, skill_seed["contract"])
                            self.assertEqual(relations, skill_seed["relations"])
                            self.assertEqual(sections["Rationale"], skill_seed["rationale"].strip())
                            self.assertEqual(
                                sections["Evidence Summary"],
                                skill_seed["evidence_summary"].strip(),
                            )
                            self.assertNotIn("candidate_seed::", skill_markdown)
                            self.assertNotIn("pending_review", skill_markdown)
                            self.assertNotIn(
                                "Representative cases are still pending curation.",
                                usage_summary,
                            )

                            for note in skill_seed.get("usage_notes", []):
                                self.assertIn(note, usage_summary)
                            for trace in skill_seed.get("traces", []):
                                self.assertIn(
                                    f"traces/canonical/{trace['trace_id']}.yaml",
                                    usage_summary,
                                )

                            self.assertEqual(
                                eval_summary["kiu_test"],
                                skill_seed["eval_prefill"]["kiu_test"],
                            )
                            self.assertEqual(
                                eval_summary["key_failure_modes"],
                                skill_seed["eval_prefill"]["key_failure_modes"],
                            )
                            for subset_name, subset_prefill in skill_seed["eval_prefill"]["subsets"].items():
                                actual_subset = eval_summary["subsets"][subset_name]
                                self.assertEqual(actual_subset["passed"], subset_prefill["passed"])
                                self.assertEqual(actual_subset["threshold"], subset_prefill["threshold"])
                                self.assertEqual(actual_subset["status"], subset_prefill["status"])
                                self.assertEqual(
                                    actual_subset["total"],
                                    len(skill_seed["evaluation_cases"][subset_name]),
                                )
                                self.assertEqual(
                                    len(actual_subset["cases"]),
                                    len(skill_seed["evaluation_cases"][subset_name]),
                                )
                                for case in skill_seed["evaluation_cases"][subset_name]:
                                    self.assertIn(
                                        f"../../../evaluation/{subset_name}/{case['case_id']}.yaml",
                                        actual_subset["cases"],
                                    )

    def test_build_candidates_cli_runs_refinement_scheduler_and_emits_terminal_state(self) -> None:
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

    def test_build_candidates_cli_supports_example_fixtures_without_gold_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            for fixture_path in self.example_fixture_paths:
                with self.subTest(fixture=fixture_path.name):
                    source_root = tmp_root / "sources" / fixture_path.stem
                    output_root = tmp_root / "generated"
                    scaffold = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "scaffold_example_bundle.py"),
                            "--fixture",
                            str(fixture_path),
                            "--output-root",
                            str(source_root),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "build_candidates.py"),
                            "--source-bundle",
                            str(source_root / "bundle"),
                            "--output-root",
                            str(output_root),
                            "--run-id",
                            fixture_path.stem,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                    source_manifest = yaml.safe_load(
                        (source_root / "bundle" / "manifest.yaml").read_text(encoding="utf-8")
                    )
                    run_root = output_root / source_manifest["bundle_id"] / fixture_path.stem
                    self.assertTrue((run_root / "reports" / "final-decision.json").exists())

    def test_build_candidates_cli_emits_good_or_better_production_quality_for_example_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            for fixture_path in self.example_fixture_paths:
                with self.subTest(fixture=fixture_path.name):
                    source_root = tmp_root / "sources" / fixture_path.stem
                    output_root = tmp_root / "generated"
                    scaffold = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "scaffold_example_bundle.py"),
                            "--fixture",
                            str(fixture_path),
                            "--output-root",
                            str(source_root),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)

                    build = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "build_candidates.py"),
                            "--source-bundle",
                            str(source_root / "bundle"),
                            "--output-root",
                            str(output_root),
                            "--run-id",
                            fixture_path.stem,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(build.returncode, 0, build.stdout + build.stderr)

                    source_manifest = yaml.safe_load(
                        (source_root / "bundle" / "manifest.yaml").read_text(encoding="utf-8")
                    )
                    run_root = output_root / source_manifest["bundle_id"] / fixture_path.stem
                    quality_report = json.loads(
                        (run_root / "reports" / "production-quality.json").read_text(encoding="utf-8")
                    )

                    self.assertTrue(quality_report["release_ready"], quality_report)
                    self.assertIn(quality_report["bundle_quality_grade"], {"good", "excellent"})
                    self.assertGreaterEqual(quality_report["minimum_production_quality"], 0.78)
                    for entry in quality_report["skills"]:
                        self.assertIn(entry["quality_grade"], {"good", "excellent"})
                        self.assertGreaterEqual(entry["artifact_quality"], 0.74)
                        self.assertGreaterEqual(entry["production_quality"], 0.78)

    def test_cli_can_default_to_fixed_local_output_root_via_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = os.environ.copy()
            env["KIU_LOCAL_OUTPUT_ROOT"] = tmp_dir

            scaffold = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "scaffold_example_bundle.py"),
                    "--fixture",
                    str(self.example_fixture_paths[0]),
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)
            scaffold_payload = json.loads(scaffold.stdout)
            scaffold_root = Path(scaffold_payload["bundle_root"])
            self.assertEqual(
                scaffold_root,
                Path(tmp_dir) / "sources" / self.example_fixture_paths[0].stem / "bundle",
            )

            generated = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_candidates.py"),
                    "--source-bundle",
                    str(scaffold_root),
                    "--run-id",
                    "env-default-root",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            generated_payload = json.loads(generated.stdout)
            generated_bundle_root = Path(generated_payload["bundle_root"])
            self.assertTrue(
                str(generated_bundle_root).startswith(str(Path(tmp_dir) / "generated"))
            )

            built = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(scaffold_root),
                    "--run-id",
                    "env-default-build-root",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            built_payload = json.loads(built.stdout)
            built_bundle_root = Path(built_payload["bundle_root"])
            self.assertTrue(
                str(built_bundle_root).startswith(str(Path(tmp_dir) / "generated"))
            )

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
            skill_doc = skill_doc.replace("skill_revision: 4", "skill_revision: 1")
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
