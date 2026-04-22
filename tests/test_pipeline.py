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
from kiu_pipeline.extraction import validate_extraction_result_doc, validate_source_chunks_doc
from kiu_pipeline.local_paths import resolve_output_root
from kiu_pipeline.regression import DEFAULT_V06_CHECK_IDS


class CandidatePipelineTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"
        self.engineering_bundle_path = ROOT / "bundles" / "engineering-postmortem-v0.1"
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

    def test_engineering_source_bundle_generates_skill_and_workflow_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_candidates.py"),
                    "--source-bundle",
                    str(self.engineering_bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "engineering-boundary",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)

            run_root = output_root / "engineering-postmortem-v0.1" / "engineering-boundary"
            bundle_root = run_root / "bundle"
            workflow_root = run_root / "workflow_candidates"
            manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
            metrics = json.loads((run_root / "reports" / "metrics.json").read_text(encoding="utf-8"))

            self.assertEqual(
                {entry["skill_id"] for entry in manifest["skills"]},
                {"postmortem-blameless", "blast-radius-check"},
            )
            self.assertEqual(payload["summary"]["workflow_script_candidates"], 1)
            self.assertEqual(metrics["summary"]["workflow_script_candidates"], 1)
            self.assertFalse((bundle_root / "skills" / "reversibility-preflight-checklist").exists())
            workflow_candidate = workflow_root / "reversibility-preflight-checklist" / "candidate.yaml"
            self.assertTrue(workflow_candidate.exists())

            workflow_doc = yaml.safe_load(workflow_candidate.read_text(encoding="utf-8"))
            self.assertEqual(workflow_doc["recommended_execution_mode"], "workflow_script")
            self.assertEqual(workflow_doc["disposition"], "workflow_script_candidate")
            self.assertEqual(workflow_doc["workflow_certainty"], "high")
            self.assertEqual(workflow_doc["context_certainty"], "high")

    def test_engineering_workflow_candidate_emits_minimum_deliverable_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_candidates.py"),
                    "--source-bundle",
                    str(self.engineering_bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "engineering-workflow-deliverable",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            candidate_root = (
                output_root
                / "engineering-postmortem-v0.1"
                / "engineering-workflow-deliverable"
                / "workflow_candidates"
                / "reversibility-preflight-checklist"
            )
            workflow_path = candidate_root / "workflow.yaml"
            checklist_path = candidate_root / "CHECKLIST.md"

            self.assertTrue(workflow_path.exists())
            self.assertTrue(checklist_path.exists())

            workflow_doc = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
            checklist = checklist_path.read_text(encoding="utf-8")

            self.assertEqual(workflow_doc["workflow_id"], "reversibility-preflight-checklist")
            self.assertEqual(workflow_doc["recommended_execution_mode"], "workflow_script")
            self.assertEqual(workflow_doc["disposition"], "workflow_script_candidate")
            self.assertEqual(workflow_doc["source_bundle_id"], "engineering-postmortem-v0.1")
            self.assertTrue(workflow_doc["source_graph_hash"].startswith("sha256:"))
            self.assertEqual(workflow_doc["seed"]["primary_node_id"], "n_reversibility_gate")
            self.assertEqual(
                workflow_doc["seed"]["supporting_edge_ids"],
                ["e_blast_reversibility_constrained_by"],
            )

            self.assertIn("# reversibility-preflight-checklist", checklist)
            self.assertIn("## Scope", checklist)
            self.assertIn("## Rollback", checklist)
            self.assertIn("## Reversibility", checklist)
            self.assertIn("## Evidence Anchors", checklist)

    def test_build_candidates_reports_workflow_boundary_for_engineering_source_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(self.engineering_bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "engineering-build-boundary",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)

            run_root = output_root / "engineering-postmortem-v0.1" / "engineering-build-boundary"
            workflow_candidate = (
                run_root
                / "workflow_candidates"
                / "reversibility-preflight-checklist"
                / "candidate.yaml"
            )

            self.assertEqual(payload["summary"]["workflow_script_candidates"], 1)
            self.assertTrue(workflow_candidate.exists())
            self.assertTrue((run_root / "reports" / "final-decision.json").exists())

    def test_review_generated_run_emits_three_layer_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "generated"
            build = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(self.engineering_bundle_path),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "engineering-review-score",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)

            run_root = output_root / "engineering-postmortem-v0.1" / "engineering-review-score"
            usage_root = run_root / "usage-review"
            usage_root.mkdir(parents=True, exist_ok=True)
            usage_doc = {
                "review_case_id": "engineering-postmortem-blameless",
                "generated_run_root": str(run_root),
                "skill_path": str(
                    run_root / "bundle" / "skills" / "postmortem-blameless" / "SKILL.md"
                ),
                "input_scenario": {
                    "incident_summary": "发布后查询抖动，团队开始追责个人。",
                    "timeline": "审批临时放行，告警延迟触发，runbook 缺失。",
                    "current_blame_narrative": "就是执行人失误。",
                },
                "firing_assessment": {
                    "should_fire": True,
                    "why_this_skill_fired": [
                        "复盘滑向归咎个人。",
                        "时间线尚未被系统化重建。",
                    ],
                },
                "boundary_check": {
                    "status": "pass",
                    "notes": ["事故已受控，且已提供基础时间线。"],
                },
                "structured_output": {
                    "verdict": "blameless_reframe_needed",
                    "next_action": "identify_system_factors",
                    "confidence": "high",
                },
                "analysis_summary": "先回到时间线和系统诱因，而不是先锁定个人责任。",
                "quality_assessment": {
                    "contract_fit": "strong",
                    "evidence_alignment": [
                        "blameless-db-index-rollout",
                        "incident-timeline-gap",
                    ],
                    "caveats": ["如果缺少检测证据，应下调 confidence。"],
                },
            }
            (usage_root / "sample.yaml").write_text(
                yaml.safe_dump(usage_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            foreign_usage_doc = dict(usage_doc)
            foreign_usage_doc["review_case_id"] = "foreign-case"
            foreign_usage_doc["generated_run_root"] = str(output_root / "foreign" / "run")
            (usage_root / "foreign.yaml").write_text(
                yaml.safe_dump(foreign_usage_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            review = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "review_generated_run.py"),
                    "--run-root",
                    str(run_root),
                    "--source-bundle",
                    str(self.engineering_bundle_path),
                    "--usage-review-dir",
                    str(usage_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(review.returncode, 0, review.stdout + review.stderr)

            report_path = run_root / "reports" / "three-layer-review.json"
            self.assertTrue(report_path.exists())

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("source_bundle", report)
            self.assertIn("generated_bundle", report)
            self.assertIn("usage_outputs", report)
            self.assertIn("score_100", report["source_bundle"])
            self.assertIn("score_100", report["generated_bundle"])
            self.assertIn("score_100", report["usage_outputs"])
            self.assertEqual(report["generated_bundle"]["workflow_candidate_count"], 1)
            self.assertEqual(report["usage_outputs"]["sample_count"], 1)
            self.assertIn(
                "workflow_boundary_preserved",
                report["generated_bundle"]["notes"],
            )

    def test_v06_regression_baseline_cli_runs_selected_checks_and_emits_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "baseline"
            expected_checks = [
                "validate-investing-merge",
                "validate-engineering-merge",
                "build-investing",
                "review-investing",
                "build-engineering",
                "review-engineering",
            ]

            self.assertEqual(
                DEFAULT_V06_CHECK_IDS,
                (
                    "unit-tests",
                    "validate-investing-merge",
                    "validate-engineering-merge",
                    "build-investing",
                    "review-investing",
                    "build-engineering",
                    "review-engineering",
                ),
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_v06_regression_baseline.py"),
                    "--output-root",
                    str(output_root),
                    "--python-executable",
                    sys.executable,
                    "--only",
                    expected_checks[0],
                    "--only",
                    expected_checks[1],
                    "--only",
                    expected_checks[2],
                    "--only",
                    expected_checks[3],
                    "--only",
                    expected_checks[4],
                    "--only",
                    expected_checks[5],
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)

            report_path = Path(payload["report_path"])
            self.assertTrue(report_path.exists())

            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["failed"], 0)
            self.assertEqual(report["summary"]["passed"], len(expected_checks))
            self.assertEqual(report["selected_check_ids"], expected_checks)
            self.assertEqual(
                [entry["check_id"] for entry in report["results"]],
                expected_checks,
            )
            self.assertTrue(report["runs"]["investing"]["three_layer_review_exists"])
            self.assertTrue(report["runs"]["engineering"]["three_layer_review_exists"])

    def test_extract_graph_candidates_cli_emits_empty_valid_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_chunks_path = tmp_root / "source-chunks.json"
            output_path = tmp_root / "extraction-result.json"
            source_chunks_doc = {
                "schema_version": "kiu.source-chunks/v0.1",
                "bundle_id": "demo-source-bundle",
                "source_id": "effective-requirements-analysis",
                "source_file": "examples/有效需求分析（第2版）.md",
                "language": "zh-CN",
                "chunks": [
                    {
                        "chunk_id": "chunk-001",
                        "source_id": "effective-requirements-analysis",
                        "source_file": "examples/有效需求分析（第2版）.md",
                        "chapter": "第1章",
                        "section": "1.1",
                        "line_start": 1,
                        "line_end": 5,
                        "chunk_text": "需求分析必须先搞清业务目标与边界。",
                        "token_estimate": 18,
                        "language": "zh-CN",
                    }
                ],
            }
            source_chunks_path.write_text(
                json.dumps(source_chunks_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_graph_candidates.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["output_path"], str(output_path))

            extraction_result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(extraction_result["schema_version"], "kiu.extraction-results/v0.1")
            self.assertEqual(extraction_result["input_chunk_count"], 1)
            self.assertEqual(extraction_result["chunk_ids"], ["chunk-001"])
            self.assertEqual(extraction_result["nodes"], [])
            self.assertEqual(extraction_result["edges"], [])
            self.assertEqual(extraction_result["warnings"], [])

    def test_extract_graph_candidates_cli_supports_section_headings_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"
            source_chunks_path = tmp_root / "source-chunks.json"
            extraction_output_path = tmp_root / "extraction-result.json"

            build_chunks = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_source_chunks.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--output",
                    str(source_chunks_path),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build_chunks.returncode, 0, build_chunks.stdout + build_chunks.stderr)

            extract = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_graph_candidates.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--output",
                    str(extraction_output_path),
                    "--deterministic-pass",
                    "section-headings",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(extract.returncode, 0, extract.stdout + extract.stderr)
            extraction_result = json.loads(extraction_output_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_extraction_result_doc(extraction_result), [])
            self.assertGreaterEqual(len(extraction_result["nodes"]), 3)
            self.assertGreaterEqual(len(extraction_result["edges"]), 2)
            self.assertEqual(extraction_result["nodes"][0]["extraction_kind"], "EXTRACTED")
            self.assertEqual(extraction_result["edges"][0]["confidence"], 1.0)

    def test_extract_graph_candidates_cli_supports_heuristic_extractors_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_chunks_path = tmp_root / "source-chunks.json"
            output_path = tmp_root / "extraction-result.json"
            source_chunks_doc = {
                "schema_version": "kiu.source-chunks/v0.1",
                "bundle_id": "demo-source-bundle",
                "source_id": "financial-analysis-demo",
                "source_file": "examples/demo-financial-analysis.md",
                "language": "zh-CN",
                "section_map": [
                    {
                        "level": 1,
                        "title": "Demo Financial Analysis",
                        "line_start": 1,
                        "path": ["Demo Financial Analysis"],
                    },
                    {
                        "level": 2,
                        "title": "Challenge Price With Value",
                        "line_start": 5,
                        "path": ["Demo Financial Analysis", "Challenge Price With Value"],
                    },
                ],
                "chunks": [
                    {
                        "chunk_id": "chunk-001",
                        "source_id": "financial-analysis-demo",
                        "source_file": "examples/demo-financial-analysis.md",
                        "chapter": "Demo Financial Analysis",
                        "section": "Challenge Price With Value",
                        "line_start": 6,
                        "line_end": 8,
                        "chunk_text": "估值的目的是用独立价值去挑战价格。例如，市场热度不能替代基本价值（fundamental value）。",
                        "token_estimate": 40,
                        "language": "zh-CN",
                    }
                ],
            }
            source_chunks_path.write_text(
                json.dumps(source_chunks_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_graph_candidates.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--output",
                    str(output_path),
                    "--deterministic-pass",
                    "heuristic-extractors",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            extraction_result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_extraction_result_doc(extraction_result), [])
            extractor_kinds = {node.get("extractor_kind") for node in extraction_result["nodes"]}
            self.assertIn("framework", extractor_kinds)
            self.assertIn("principle", extractor_kinds)
            self.assertIn("evidence", extractor_kinds)
            self.assertIn("case", extractor_kinds)
            self.assertIn("term", extractor_kinds)
            self.assertTrue(
                any(edge["type"] == "supported_by_evidence" for edge in extraction_result["edges"])
            )
            self.assertTrue(
                any(edge["type"] == "mentions_term" for edge in extraction_result["edges"])
            )

    def test_extract_graph_candidates_cli_supports_llm_assisted_with_mock_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"
            source_chunks_path = tmp_root / "source-chunks.json"
            output_path = tmp_root / "extraction-result.json"

            build_chunks = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_source_chunks.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--output",
                    str(source_chunks_path),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build_chunks.returncode, 0, build_chunks.stdout + build_chunks.stderr)

            env = os.environ.copy()
            env["KIU_LLM_PROVIDER"] = "mock"
            env["KIU_LLM_MOCK_RESPONSE"] = (
                "nodes:\n"
                "  - id: llm::0001\n"
                "    type: principle_signal\n"
                "    label: 从 mock provider 追加的提炼原则\n"
                "    source_file: examples/sources/effective-requirements-analysis-source.md\n"
                "    extraction_kind: INFERRED\n"
                "edges: []\n"
                "warnings:\n"
                "  - mock_llm_patch_applied\n"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_graph_candidates.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--output",
                    str(output_path),
                    "--deterministic-pass",
                    "heuristic-extractors",
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
            extraction_result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_extraction_result_doc(extraction_result), [])
            self.assertTrue(
                any(node["id"] == "llm::0001" for node in extraction_result["nodes"])
            )
            self.assertIn("mock_llm_patch_applied", extraction_result["warnings"])
            self.assertEqual(extraction_result["llm_drafting"]["provider"], "mock")

    def test_materialize_extraction_graph_cli_emits_graph_v02(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"
            source_chunks_path = tmp_root / "source-chunks.json"
            extraction_output_path = tmp_root / "extraction-result.json"
            graph_output_path = tmp_root / "graph.json"

            build_chunks = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_source_chunks.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--output",
                    str(source_chunks_path),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build_chunks.returncode, 0, build_chunks.stdout + build_chunks.stderr)

            extract = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "extract_graph_candidates.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--output",
                    str(extraction_output_path),
                    "--deterministic-pass",
                    "heuristic-extractors",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(extract.returncode, 0, extract.stdout + extract.stderr)

            materialize = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_extraction_graph.py"),
                    "--extraction-result",
                    str(extraction_output_path),
                    "--output",
                    str(graph_output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(materialize.returncode, 0, materialize.stdout + materialize.stderr)
            graph_doc = json.loads(graph_output_path.read_text(encoding="utf-8"))
            extraction_result = json.loads(extraction_output_path.read_text(encoding="utf-8"))
            self.assertEqual(graph_doc["graph_version"], "kiu.graph/v0.2")
            self.assertEqual(graph_doc["source_snapshot"], "effective-requirements-analysis")
            self.assertTrue(graph_doc["graph_hash"].startswith("sha256:"))
            self.assertEqual(len(graph_doc["nodes"]), len(extraction_result["nodes"]))
            self.assertEqual(len(graph_doc["edges"]), len(extraction_result["edges"]))
            self.assertEqual(graph_doc["communities"], [])
            self.assertIn("source_file", graph_doc["nodes"][0])
            self.assertIn("extraction_kind", graph_doc["edges"][0])
            self.assertIn("confidence", graph_doc["edges"][0])

    def test_build_source_chunks_cli_emits_valid_chunks_for_fixture_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"
            output_path = tmp_root / "source-chunks.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_source_chunks.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--output",
                    str(output_path),
                    "--max-chars",
                    "220",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["output_path"], str(output_path))

            doc = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_source_chunks_doc(doc), [])
            self.assertGreaterEqual(len(doc["chunks"]), 4)
            self.assertEqual(doc["source_file"], "examples/sources/effective-requirements-analysis-source.md")
            target_chunk = next(
                chunk
                for chunk in doc["chunks"]
                if chunk["section"] == "Problem-First Requirements Analysis"
            )
            self.assertEqual(
                target_chunk["chapter"],
                "Effective Requirements Analysis Fixture Source",
            )
            self.assertEqual(
                target_chunk["section"],
                "Problem-First Requirements Analysis",
            )
            self.assertIn("section_map", doc)
            self.assertTrue(
                any(
                    entry["title"] == "Business Interface Analysis"
                    for entry in doc["section_map"]
                )
            )

    def test_build_source_chunks_cli_supports_example_regression_books(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            sample_books = [
                ROOT / "examples" / "有效需求分析（第2版）.md",
                ROOT / "examples" / "财务报表分析_Markdown版.md",
            ]

            for source_path in sample_books:
                with self.subTest(source=source_path.name):
                    output_path = tmp_root / f"{source_path.stem}.chunks.json"
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "build_source_chunks.py"),
                            "--input",
                            str(source_path),
                            "--bundle-id",
                            "example-regression-books",
                            "--source-id",
                            source_path.stem,
                            "--output",
                            str(output_path),
                            "--max-chars",
                            "1200",
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    doc = json.loads(output_path.read_text(encoding="utf-8"))
                    self.assertEqual(validate_source_chunks_doc(doc), [])
                    self.assertGreater(len(doc["chunks"]), 10)
                    self.assertIn("section_map", doc)
                    self.assertGreater(len(doc["section_map"]), 5)

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

    def test_scaffolded_example_bundle_prefers_inherits_from(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            for fixture_path in self.example_fixture_paths:
                with self.subTest(fixture=fixture_path.name):
                    source_root = tmp_root / "sources" / fixture_path.stem
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

                    automation = yaml.safe_load(
                        (source_root / "bundle" / "automation.yaml").read_text(encoding="utf-8")
                    )

                    self.assertIn("inherits_from", automation)
                    self.assertNotIn("inherits", automation)
                    self.assertEqual(automation["inherits_from"], "default")

    def test_preflight_rejects_generated_skill_summary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            _, generated_bundle = self._generate_fixture_bundle(
                fixture_path=ROOT / "examples" / "fixtures" / "effective-requirements-analysis.yaml",
                tmp_root=tmp_root,
            )
            skill_dir = generated_bundle / "skills" / "business-interface-analysis"
            skill_markdown = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            skill_markdown = skill_markdown.replace(
                "boundary_test=`pass`。",
                "boundary_test=`pending`。",
                1,
            )
            skill_markdown = skill_markdown.replace(
                "## Revision Summary\n初版 seed 已把业务接口分析与系统接口设计的边界写入 contract，并补足最小 traces/eval 绑定。",
                "## Revision Summary\nstale revision summary",
                1,
            )
            (skill_dir / "SKILL.md").write_text(skill_markdown, encoding="utf-8")

            report = validate_generated_bundle(generated_bundle)

            self.assertTrue(
                any("Evaluation Summary drift" in error for error in report["errors"]),
                report["errors"],
            )
            self.assertTrue(
                any("Revision Summary drift" in error for error in report["errors"]),
                report["errors"],
            )

    def test_financial_statement_fixture_routes_story_only_into_accounting_anchor_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            _, generated_bundle = self._generate_fixture_bundle(
                fixture_path=ROOT / "examples" / "fixtures" / "financial-statement-analysis.yaml",
                tmp_root=tmp_root,
            )
            skill_dir = generated_bundle / "skills" / "lock-onto-accounting-value"
            sections = parse_sections((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
            contract = extract_yaml_section(sections["Contract"])

            self.assertIn(
                "valuation_depends_only_on_story_or_long_term_guess",
                contract["trigger"]["patterns"],
            )
            self.assertNotIn(
                "valuation_depends_only_on_story_or_long_term_guess",
                contract["trigger"]["exclusions"],
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
