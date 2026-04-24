import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.preflight import validate_generated_bundle
from kiu_pipeline.seed import derive_candidate_metadata
from kiu_pipeline.load import extract_yaml_section, load_source_bundle, parse_sections
from kiu_pipeline.extraction import validate_extraction_result_doc, validate_source_chunks_doc
from kiu_pipeline.extraction_bundle import scaffold_extraction_bundle
from kiu_pipeline.local_paths import resolve_output_root
from kiu_pipeline.normalize import normalize_graph
from kiu_pipeline.regression import DEFAULT_V06_CHECK_IDS
from kiu_pipeline.reference_benchmark import _evaluate_kiu_usage_case
from kiu_pipeline.seed import mine_candidate_seeds, mine_candidate_seed_assessment


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

            self.assertEqual(len(manifest["skills"]), 6)
            self.assertEqual(
                {entry["skill_id"] for entry in manifest["skills"]},
                {
                    "circle-of-competence",
                    "bias-self-audit",
                    "margin-of-safety-sizing",
                    "invert-the-problem",
                    "opportunity-cost-of-the-next-best-idea",
                    "value-assessment-source-note",
                },
            )
            self.assertEqual(metrics["summary"]["skill_candidates"], 6)
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
            self.assertEqual(report["summary"]["skill_candidates"], 6)

    def test_generated_investing_bundle_carries_scenario_families_into_usage_summary(self) -> None:
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
                    "usage-scenarios",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            bundle_root = output_root / "poor-charlies-almanack-v0.1" / "usage-scenarios" / "bundle"
            manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))

            for entry in manifest["skills"]:
                with self.subTest(skill=entry["skill_id"]):
                    skill_dir = bundle_root / entry["path"]
                    scenario_families = yaml.safe_load(
                        (skill_dir / "usage" / "scenarios.yaml").read_text(encoding="utf-8")
                    ) or {}
                    sections = parse_sections(
                        (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                    )
                    usage_summary = sections["Usage Summary"]

                    self.assertTrue(
                        any(bool(items) for items in scenario_families.values()),
                        scenario_families,
                    )
                    self.assertIn("Scenario families:", usage_summary)
                    self.assertIn("next:", usage_summary)

    def test_generated_bundle_keeps_concept_query_boundary_for_invert_and_margin(self) -> None:
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
                    "concept-boundary",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            generated_bundle = output_root / "poor-charlies-almanack-v0.1" / "concept-boundary" / "bundle"
            generated = load_source_bundle(generated_bundle)

            invert_review = _evaluate_kiu_usage_case(
                skill=generated.skills["invert-the-problem"],
                case={
                    "type": "should_not_trigger",
                    "prompt": "逆向思维是什么意思？能给我解释一下这个概念吗",
                    "expected_behavior": "不应激活本 skill，因为用户只是在询问概念定义，不需要将逆向思维应用于实际决策",
                    "notes": "纯知识查询。",
                },
                alignment_strength=0.9,
            )
            margin_review = _evaluate_kiu_usage_case(
                skill=generated.skills["margin-of-safety-sizing"],
                case={
                    "type": "should_not_trigger",
                    "prompt": "什么是安全边际？芒格和巴菲特是怎么定义内在价值的？",
                    "expected_behavior": "不应激活, 因为这是纯概念查询，不是在面临一个需要做价值判断的真实投资决策",
                    "notes": "纯概念查询。",
                },
                alignment_strength=0.65,
            )

            self.assertNotIn("boundary_leak", invert_review["failure_analysis"]["tags"])
            self.assertNotIn("boundary_leak", margin_review["failure_analysis"]["tags"])
            self.assertGreaterEqual(invert_review["overall_score_100"], 75.0)
            self.assertGreaterEqual(margin_review["overall_score_100"], 75.0)

    def test_generated_bundle_adds_value_assessment_parent_for_margin_family(self) -> None:
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
                    "value-parent-topology",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            generated_bundle = (
                output_root
                / "poor-charlies-almanack-v0.1"
                / "value-parent-topology"
                / "bundle"
            )
            generated = load_source_bundle(generated_bundle)
            parent_skill = generated.skills["value-assessment-source-note"]
            parent_candidate = yaml.safe_load(
                (
                    generated_bundle
                    / "skills"
                    / "value-assessment-source-note"
                    / "candidate.yaml"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(parent_candidate["gold_match_hint"], "value-assessment")
            self.assertEqual(parent_skill.relations["delegates_to"], ["margin-of-safety-sizing"])

    def test_generated_value_assessment_parent_reaches_good_quality_and_has_eval_coverage(self) -> None:
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
                    "value-parent-quality",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            quality_doc = json.loads(
                (
                    output_root
                    / "poor-charlies-almanack-v0.1"
                    / "value-parent-quality"
                    / "reports"
                    / "production-quality.json"
                ).read_text(encoding="utf-8")
            )
            entry = next(
                item
                for item in quality_doc["skills"]
                if item["candidate_id"] == "value-assessment-source-note"
            )

            self.assertGreaterEqual(entry["signals"]["eval_cases_total"], 3)
            self.assertGreaterEqual(entry["signals"]["passed_kiu_tests"], 2)
            self.assertIn(entry["quality_grade"], {"good", "excellent"})
            self.assertGreaterEqual(entry["production_quality"], 0.82)

    def test_generated_value_assessment_parent_hardens_price_vs_value_next_step(self) -> None:
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
                    "value-parent-next-step",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            generated_bundle = (
                output_root
                / "poor-charlies-almanack-v0.1"
                / "value-parent-next-step"
                / "bundle"
            )
            generated = load_source_bundle(generated_bundle)
            review = _evaluate_kiu_usage_case(
                skill=generated.skills["value-assessment-source-note"],
                case={
                    "type": "should_trigger",
                    "prompt": "我在考虑要不要买一只消费股，市盈率25倍不算便宜，但品牌很强，这个价格合理吗？安全边际够不够？",
                    "expected_behavior": "应激活 value-assessment, 并从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估",
                    "notes": "正面场景：先做 value-anchor judgment，再决定是否交给 sizing。",
                },
                alignment_strength=1.0,
            )

            self.assertNotEqual(
                review["failure_analysis"]["primary_gap"],
                "next_step_blunt",
            )
            self.assertGreaterEqual(review["overall_score_100"], 97.0)

    def test_generated_value_assessment_parent_avoids_generic_pricing_power_reasoning(self) -> None:
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
                    "value-parent-pricing-power",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            generated_bundle = (
                output_root
                / "poor-charlies-almanack-v0.1"
                / "value-parent-pricing-power"
                / "bundle"
            )
            generated = load_source_bundle(generated_bundle)
            review = _evaluate_kiu_usage_case(
                skill=generated.skills["value-assessment-source-note"],
                case={
                    "type": "should_trigger",
                    "prompt": "这家公司看起来护城河很宽，产品提价客户也不会跑，这种公司和其他公司到底差在哪？",
                    "expected_behavior": "应激活 value-assessment, 并重点分析定价权——芒格认为'尚未利用的提价能力'是伟大企业最可靠的标志",
                    "notes": "正面场景：要求解释 pricing power 为什么会转成更高质量的价值锚点。",
                },
                alignment_strength=1.0,
            )

            self.assertNotIn("generic_reasoning", review["failure_analysis"]["tags"])
            self.assertGreaterEqual(review["overall_score_100"], 96.0)

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
            usage_docs = sorted((run_root / "usage-review").glob("*.yaml"))
            self.assertTrue(usage_docs)
            usage_doc = yaml.safe_load(usage_docs[0].read_text(encoding="utf-8"))
            self.assertIn("structured_output", usage_doc)
            self.assertNotEqual(
                usage_doc["structured_output"].get("next_action"),
                "collect_more_info",
            )

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
            usage_root = Path(tmp_dir) / "manual-usage-review"
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
            weak_usage_doc = {
                "review_case_id": "engineering-postmortem-weak-next-step",
                "generated_run_root": str(run_root),
                "skill_path": str(
                    run_root / "bundle" / "skills" / "postmortem-blameless" / "SKILL.md"
                ),
                "input_scenario": {
                    "incident_summary": "团队想直接总结经验，但没有明确时间线，也没有系统诱因证据。",
                },
                "firing_assessment": {
                    "should_fire": True,
                    "why_this_skill_fired": [
                        "大家在泛泛讨论复盘。",
                    ],
                },
                "boundary_check": {
                    "status": "warning",
                    "notes": ["时间线还不完整。"],
                },
                "structured_output": {
                    "verdict": "review_more",
                    "next_action": "collect_more_info",
                },
                "analysis_summary": "先再看看。",
                "quality_assessment": {
                    "contract_fit": "weak",
                    "evidence_alignment": [],
                    "caveats": ["缺少可执行下一步。"],
                },
            }
            (usage_root / "weak.yaml").write_text(
                yaml.safe_dump(weak_usage_doc, sort_keys=False, allow_unicode=True),
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
            review_cli_payload = json.loads(review.stdout)
            self.assertIn("release_gate_overall_ready", review_cli_payload)
            self.assertIn("release_gate_reasons", review_cli_payload)

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
            self.assertEqual(report["usage_outputs"]["sample_count"], 2)
            self.assertIn("failure_tag_counts", report["usage_outputs"])
            self.assertIn("usage_gate_ready", report["usage_outputs"])
            self.assertIn("release_gate", report)
            self.assertIn("overall_ready", report["release_gate"])
            self.assertIn("reasons", report["release_gate"])
            self.assertFalse(report["release_gate"]["overall_ready"])
            self.assertIn("usage_gate_not_ready", report["release_gate"]["reasons"])
            self.assertIn(
                "workflow_boundary_preserved",
                report["generated_bundle"]["notes"],
            )

            production_quality = json.loads(
                (run_root / "reports" / "production-quality.json").read_text(encoding="utf-8")
            )
            self.assertTrue(production_quality["artifact_release_ready"])
            self.assertFalse(production_quality["behavior_release_ready"])
            self.assertFalse(production_quality["release_ready"])
            self.assertIn("usage_gate_not_ready", production_quality["release_gate_reasons"])
            self.assertIn("next_step_quality_weak", production_quality["release_gate_reasons"])

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

    def test_scaffold_extraction_bundle_adds_value_assessment_parent_candidate_for_margin_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = tmp_root / "source.md"
            source_path.write_text(
                "# Demo Source\n\n估值的核心是用价值去挑战价格，再决定是否投入资本。\n",
                encoding="utf-8",
            )
            source_chunks_path = tmp_root / "source-chunks.json"
            source_chunks_path.write_text(
                json.dumps(
                    {
                        "schema_version": "kiu.source-chunks/v0.1",
                        "bundle_id": "demo-source-bundle",
                        "source_id": "demo-source",
                        "source_file": str(source_path),
                        "language": "zh-CN",
                        "chunks": [
                            {
                                "chunk_id": "chunk-001",
                                "source_id": "demo-source",
                                "source_file": str(source_path),
                                "chapter": "第1章",
                                "section": "1.1",
                                "line_start": 1,
                                "line_end": 3,
                                "chunk_text": "估值的核心是用价值去挑战价格，再决定是否投入资本。",
                                "token_estimate": 24,
                                "language": "zh-CN",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            graph_path = tmp_root / "graph.json"
            graph_path.write_text(
                json.dumps(
                    {
                        "graph_version": "kiu.graph/v0.2",
                        "source_snapshot": "demo-source",
                        "graph_hash": "sha256:demo",
                        "nodes": [
                            {
                                "id": "principle::0001",
                                "type": "principle_signal",
                                "label": "Margin Of Safety Sizing Source Note",
                                "source_file": str(source_path),
                                "source_location": {"line_start": 2, "line_end": 2},
                                "extraction_kind": "EXTRACTED",
                            },
                            {
                                "id": "evidence::0001",
                                "type": "chunk_evidence",
                                "label": "估值的核心是用价值去挑战价格，再决定是否投入资本。",
                                "source_file": str(source_path),
                                "source_location": {"line_start": 2, "line_end": 2},
                                "extraction_kind": "EXTRACTED",
                            },
                        ],
                        "edges": [
                            {
                                "id": "supported-by::principle::0001->evidence::0001",
                                "type": "supported_by_evidence",
                                "from": "principle::0001",
                                "to": "evidence::0001",
                                "source_file": str(source_path),
                                "source_location": {"line_start": 2, "line_end": 2},
                                "extraction_kind": "EXTRACTED",
                                "confidence": 1.0,
                            }
                        ],
                        "communities": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            bundle_root = scaffold_extraction_bundle(
                source_chunks_path=source_chunks_path,
                graph_path=graph_path,
                output_root=tmp_root / "source-bundle",
                inherits_from="default",
            )

            bundle_graph = json.loads((bundle_root / "graph" / "graph.json").read_text(encoding="utf-8"))
            principle_node = next(node for node in bundle_graph["nodes"] if node["id"] == "principle::0001")
            additional_candidates = principle_node["skill_seed"].get("additional_candidates", [])

            self.assertEqual(len(additional_candidates), 1)
            self.assertEqual(
                additional_candidates[0]["candidate_id"],
                "value-assessment-source-note",
            )
            self.assertEqual(
                additional_candidates[0]["skill_seed"]["title"],
                "Value Assessment Source Note",
            )
            self.assertEqual(
                additional_candidates[0]["skill_seed"]["contract"]["judgment_schema"]["output"]["schema"]["applicability_mode"],
                "enum[full_valuation|partial_applicability|refuse]",
            )
            self.assertTrue(
                any(
                    "尚未利用的提价能力" in note
                    for note in additional_candidates[0]["skill_seed"]["usage_notes"]
                )
            )
            self.assertTrue(
                any(
                    "长期持有" in note
                    for note in additional_candidates[0]["skill_seed"]["usage_notes"]
                )
            )
            self.assertTrue(
                any(
                    "scale-advantage-analysis" in note
                    for note in additional_candidates[0]["skill_seed"]["usage_notes"]
                )
            )
            self.assertTrue(
                any(
                    "能力圈检验" in note
                    for note in additional_candidates[0]["skill_seed"]["usage_notes"]
                )
            )

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
                        "chunk_text": "估值的目的是用独立价值去挑战价格。例如，市场热度不能替代基本价值（fundamental value）。反例是只看涨幅和热度就上调估值，这会把价格偷偷塞回价值模型。",
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
            self.assertIn("counter-example", extractor_kinds)
            extractor_run_log = extraction_result.get("extractor_run_log")
            self.assertIsInstance(extractor_run_log, list)
            logged_extractors = {
                stage.get("extractor_kind")
                for stage in extractor_run_log
                if isinstance(stage, dict)
            }
            self.assertTrue(
                {
                    "framework",
                    "principle",
                    "evidence",
                    "case",
                    "counter-example",
                    "term",
                }.issubset(logged_extractors)
            )
            framework_stage = next(
                stage
                for stage in extractor_run_log
                if stage.get("extractor_kind") == "framework"
            )
            self.assertEqual(framework_stage["pass_kind"], "deterministic")
            self.assertEqual(framework_stage["prompt_key"], "heuristic-framework")
            self.assertEqual(framework_stage["input_chunk_ids"], ["chunk-001"])
            self.assertTrue(framework_stage["output_node_ids"])
            extraction_kinds = {
                entity.get("extraction_kind")
                for entity in [*extraction_result["nodes"], *extraction_result["edges"]]
            }
            self.assertEqual(
                extraction_kinds,
                {"EXTRACTED", "INFERRED", "AMBIGUOUS"},
            )
            self.assertTrue(
                any(edge["type"] == "supported_by_evidence" for edge in extraction_result["edges"])
            )
            self.assertTrue(
                any(edge["type"] == "mentions_term" for edge in extraction_result["edges"])
            )
            self.assertTrue(
                any(edge["type"] == "flags_counter_example" for edge in extraction_result["edges"])
            )
            self.assertTrue(
                any(
                    edge["type"] == "derives_counter_example_signal"
                    and edge["extraction_kind"] == "INFERRED"
                    for edge in extraction_result["edges"]
                )
            )
            self.assertTrue(
                any(
                    node["type"] == "counter_example_signal"
                    and node["extraction_kind"] == "AMBIGUOUS"
                    and node.get("inference_basis") == "negative_outcome_heuristic"
                    for node in extraction_result["nodes"]
                )
            )

    def test_extract_graph_candidates_marks_business_first_boundary_regression_as_tri_state(self) -> None:
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
            self.assertTrue(
                any(
                    node["type"] == "counter_example_signal"
                    and node.get("section_title") == "Business-First Subsystem Decomposition"
                    for node in extraction_result["nodes"]
                ),
                extraction_result["nodes"],
            )
            self.assertTrue(
                any(
                    edge["type"] == "derives_counter_example_signal"
                    and edge["from"] == "principle::0003"
                    for edge in extraction_result["edges"]
                ),
                extraction_result["edges"],
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
            llm_stage = extraction_result["extractor_run_log"][-1]
            self.assertEqual(llm_stage["pass_kind"], "llm_patch")
            self.assertEqual(llm_stage["extractor_kind"], "llm-patch")
            self.assertEqual(llm_stage["prompt_key"], "llm-extraction-patch")
            self.assertIn("llm::0001", llm_stage["output_node_ids"])

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

    def test_mine_candidate_seeds_infers_workflow_candidate_from_extraction_routing_hints(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["principle_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "principle::0001",
                        "type": "principle_signal",
                        "label": "Problem-First Requirements Analysis",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 5, "line_end": 5},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "workflow_cues": 2,
                            "context_cues": 1,
                            "matched_keywords": ["第一步", "先"],
                            "evidence_chunk_ids": ["synthetic:0001"],
                        },
                    },
                    {
                        "id": "evidence::0001",
                        "type": "chunk_evidence",
                        "label": "需求分析的第一步是确认业务问题，先确认目标再决定方案。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 8},
                        "extraction_kind": "EXTRACTED",
                    },
                ],
                "edges": [
                    {
                        "id": "supported-by::principle::0001->evidence::0001",
                        "type": "supported_by_evidence",
                        "from": "principle::0001",
                        "to": "evidence::0001",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 8},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    }
                ],
                "communities": [],
            }
        )

        seeds = mine_candidate_seeds(bundle, graph)

        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0].candidate_kind, "workflow_script")
        self.assertEqual(seeds[0].metadata["disposition"], "workflow_script_candidate")
        self.assertEqual(seeds[0].metadata["recommended_execution_mode"], "workflow_script")
        self.assertEqual(
            seeds[0].metadata["routing_evidence"]["inference_mode"],
            "extraction_derived",
        )
        self.assertEqual(
            seeds[0].metadata["routing_evidence"]["workflow_cues"],
            2,
        )

    def test_mine_candidate_seeds_keeps_tri_state_heavy_candidate_on_agentic_path(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["principle_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "principle::0001",
                        "type": "principle_signal",
                        "label": "Boundary-Heavy Checklist",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 5, "line_end": 5},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "workflow_cues": 3,
                            "context_cues": 2,
                            "matched_keywords": ["第一步", "清单", "边界"],
                            "evidence_chunk_ids": ["synthetic:0001"],
                        },
                    },
                    {
                        "id": "evidence::0001",
                        "type": "chunk_evidence",
                        "label": "先检查输入，再执行后续步骤。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                    },
                    {
                        "id": "counter-example::0002",
                        "type": "counter_example_signal",
                        "label": "如果边界缺失，流程会把错误前提固化进执行。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 8, "line_end": 9},
                        "extraction_kind": "AMBIGUOUS",
                    },
                    {
                        "id": "counter-example::0003",
                        "type": "counter_example_signal",
                        "label": "当约束不清时，清单本身会制造误导。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 10, "line_end": 11},
                        "extraction_kind": "AMBIGUOUS",
                    },
                ],
                "edges": [
                    {
                        "id": "supported-by::principle::0001->evidence::0001",
                        "type": "supported_by_evidence",
                        "from": "principle::0001",
                        "to": "evidence::0001",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    },
                    {
                        "id": "derives_counter_example_signal::principle::0001->counter-example::0002",
                        "type": "derives_counter_example_signal",
                        "from": "principle::0001",
                        "to": "counter-example::0002",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 8, "line_end": 9},
                        "extraction_kind": "INFERRED",
                        "confidence": 0.7,
                    },
                    {
                        "id": "derives_counter_example_signal::principle::0001->counter-example::0003",
                        "type": "derives_counter_example_signal",
                        "from": "principle::0001",
                        "to": "counter-example::0003",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 10, "line_end": 11},
                        "extraction_kind": "INFERRED",
                        "confidence": 0.7,
                    },
                ],
                "communities": [],
            }
        )

        seeds = mine_candidate_seeds(bundle, graph)

        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0].candidate_kind, "general_agentic")
        self.assertEqual(seeds[0].metadata["recommended_execution_mode"], "llm_agentic")
        self.assertEqual(seeds[0].metadata["disposition"], "skill_candidate")
        self.assertGreater(
            seeds[0].metadata["routing_evidence"]["tri_state_support_ratio"],
            0.5,
        )
        self.assertTrue(
            seeds[0].metadata["routing_evidence"]["workflow_promotion_blocked_by_evidence"]
        )

    def test_mine_candidate_seeds_emits_additional_candidate_from_skill_seed(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["principle_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "principle::0004",
                        "type": "principle_signal",
                        "label": "Margin Of Safety Sizing Source Note",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 5, "line_end": 5},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "context_cues": 1,
                            "matched_keywords": ["价格", "价值"],
                            "evidence_chunk_ids": ["synthetic:0004"],
                        },
                        "skill_seed": {
                            "title": "Margin Of Safety Sizing Source Note",
                            "trace_refs": ["traces/canonical/margin.yaml"],
                            "eval_summary": {
                                "kiu_test": {
                                    "trigger_test": "pass",
                                    "fire_test": "pending",
                                    "boundary_test": "pass",
                                }
                            },
                            "additional_candidates": [
                                {
                                    "candidate_id": "value-assessment-source-note",
                                    "skill_seed": {
                                        "title": "Value Assessment Source Note",
                                        "trace_refs": ["traces/canonical/value.yaml"],
                                        "eval_summary": {
                                            "kiu_test": {
                                                "trigger_test": "pass",
                                                "fire_test": "pending",
                                                "boundary_test": "pass",
                                            }
                                        },
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "id": "evidence::0004",
                        "type": "chunk_evidence",
                        "label": "先评估价值，再判断价格是否有足够安全边际。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                    },
                ],
                "edges": [
                    {
                        "id": "supported-by::principle::0004->evidence::0004",
                        "type": "supported_by_evidence",
                        "from": "principle::0004",
                        "to": "evidence::0004",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    }
                ],
                "communities": [],
            }
        )

        seeds = mine_candidate_seeds(bundle, graph)
        seed_map = {seed.candidate_id: seed for seed in seeds}

        self.assertEqual(
            set(seed_map),
            {"margin-of-safety-sizing-source-note", "value-assessment-source-note"},
        )
        self.assertEqual(
            seed_map["value-assessment-source-note"].primary_node_id,
            "principle::0004",
        )
        self.assertEqual(
            seed_map["value-assessment-source-note"].metadata["disposition"],
            "skill_candidate",
        )
        self.assertEqual(
            seed_map["value-assessment-source-note"].metadata["recommended_execution_mode"],
            "llm_agentic",
        )
        self.assertEqual(
            seed_map["value-assessment-source-note"].seed_content["title"],
            "Value Assessment Source Note",
        )

    def test_mine_candidate_seeds_merges_duplicate_candidate_ids_and_preserves_support(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["counter_example_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "counter-example::0002",
                        "type": "counter_example_signal",
                        "label": "Blindly Shipping Requirement Lists",
                        "candidate_id": "problem-first-requirements-analysis-counter-example",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 12, "line_end": 13},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "context_cues": 1,
                            "matched_keywords": ["反例"],
                            "evidence_chunk_ids": ["synthetic:0002"],
                        },
                    },
                    {
                        "id": "counter-example::0003",
                        "type": "counter_example_signal",
                        "label": "Symptoms-Only Ticket Intake",
                        "candidate_id": "problem-first-requirements-analysis-counter-example",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 20, "line_end": 21},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "context_cues": 1,
                            "matched_keywords": ["误判"],
                            "evidence_chunk_ids": ["synthetic:0003"],
                        },
                    },
                    {
                        "id": "evidence::0002",
                        "type": "chunk_evidence",
                        "label": "只看需求列表而不先确认问题，会让方案从一开始就跑偏。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 14, "line_end": 16},
                        "extraction_kind": "EXTRACTED",
                    },
                    {
                        "id": "evidence::0003",
                        "type": "chunk_evidence",
                        "label": "症状驱动的工单整理会掩盖真实目标，后续设计无法对准业务问题。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 22, "line_end": 24},
                        "extraction_kind": "EXTRACTED",
                    },
                    {
                        "id": "evidence::0004",
                        "type": "chunk_evidence",
                        "label": "反例越多，越能逼出触发条件和边界。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 25, "line_end": 26},
                        "extraction_kind": "EXTRACTED",
                    },
                ],
                "edges": [
                    {
                        "id": "supported-by::counter-example::0002->evidence::0002",
                        "type": "supported_by_evidence",
                        "from": "counter-example::0002",
                        "to": "evidence::0002",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 14, "line_end": 16},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    },
                    {
                        "id": "supported-by::counter-example::0003->evidence::0003",
                        "type": "supported_by_evidence",
                        "from": "counter-example::0003",
                        "to": "evidence::0003",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 22, "line_end": 24},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    },
                    {
                        "id": "supported-by::counter-example::0003->evidence::0004",
                        "type": "supported_by_evidence",
                        "from": "counter-example::0003",
                        "to": "evidence::0004",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 25, "line_end": 26},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    },
                ],
                "communities": [
                    {
                        "id": "community::counter-examples",
                        "label": "Counter Examples",
                        "node_ids": [
                            "counter-example::0002",
                            "counter-example::0003",
                            "evidence::0002",
                            "evidence::0003",
                            "evidence::0004",
                        ],
                    }
                ],
            }
        )

        seeds = mine_candidate_seeds(bundle, graph)

        self.assertEqual(len(seeds), 1)
        self.assertEqual(
            seeds[0].candidate_id,
            "problem-first-requirements-analysis-counter-example",
        )
        self.assertEqual(seeds[0].primary_node_id, "counter-example::0003")
        self.assertEqual(
            seeds[0].supporting_node_ids,
            [
                "counter-example::0002",
                "evidence::0002",
                "evidence::0003",
                "evidence::0004",
            ],
        )
        self.assertEqual(
            seeds[0].metadata["seed"]["merged_primary_node_ids"],
            ["counter-example::0002", "counter-example::0003"],
        )
        self.assertEqual(
            seeds[0].metadata["routing_evidence"]["inference_mode"],
            "merged_seed_support",
        )
        self.assertEqual(
            seeds[0].metadata["routing_evidence"]["evidence_chunk_ids"],
            ["synthetic:0002", "synthetic:0003"],
        )

    def test_mine_candidate_seeds_downgrades_workflow_when_verification_not_ready(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["principle_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "principle::0010",
                        "type": "principle_signal",
                        "label": "Fast Checklist",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 5, "line_end": 5},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "workflow_cues": 3,
                            "context_cues": 2,
                            "matched_keywords": ["第一步", "清单"],
                            "evidence_chunk_ids": ["synthetic:0010"],
                        },
                    },
                    {
                        "id": "evidence::0010",
                        "type": "chunk_evidence",
                        "label": "先检查输入，再决定是否执行后续步骤。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                    },
                ],
                "edges": [
                    {
                        "id": "supported-by::principle::0010->evidence::0010",
                        "type": "supported_by_evidence",
                        "from": "principle::0010",
                        "to": "evidence::0010",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    }
                ],
                "communities": [],
            }
        )

        seeds = mine_candidate_seeds(bundle, graph)

        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0].candidate_kind, "general_agentic")
        self.assertEqual(seeds[0].metadata["recommended_execution_mode"], "llm_agentic")
        self.assertEqual(seeds[0].metadata["disposition"], "skill_candidate")
        self.assertTrue(
            seeds[0].metadata["routing_evidence"]["workflow_promotion_blocked_by_verification"]
        )
        self.assertFalse(seeds[0].metadata["verification"]["workflow_ready"])

    def test_mine_candidate_seeds_does_not_promote_single_checklist_cue_to_workflow(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["principle_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "principle::0011",
                        "type": "principle_signal",
                        "label": "Bias Audit Checklist Note",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 5, "line_end": 5},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "workflow_cues": 1,
                            "context_cues": 1,
                            "matched_keywords": ["checklist"],
                            "evidence_chunk_ids": ["synthetic:0011"],
                        },
                    },
                    {
                        "id": "evidence::0011a",
                        "type": "chunk_evidence",
                        "label": "列出偏误清单，但仍需要判断当下情境是否真的适用。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                    },
                    {
                        "id": "evidence::0011b",
                        "type": "chunk_evidence",
                        "label": "如果约束条件不完整，这类审计不能直接退化成脚本步骤。",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 8, "line_end": 9},
                        "extraction_kind": "EXTRACTED",
                    },
                ],
                "edges": [
                    {
                        "id": "supported-by::principle::0011->evidence::0011a",
                        "type": "supported_by_evidence",
                        "from": "principle::0011",
                        "to": "evidence::0011a",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 6, "line_end": 7},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    },
                    {
                        "id": "supported-by::principle::0011->evidence::0011b",
                        "type": "supported_by_evidence",
                        "from": "principle::0011",
                        "to": "evidence::0011b",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 8, "line_end": 9},
                        "extraction_kind": "EXTRACTED",
                        "confidence": 1.0,
                    },
                ],
                "communities": [],
            }
        )

        seeds = mine_candidate_seeds(bundle, graph)

        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0].candidate_kind, "general_agentic")
        self.assertEqual(seeds[0].metadata["recommended_execution_mode"], "llm_agentic")
        self.assertEqual(seeds[0].metadata["disposition"], "skill_candidate")
        self.assertFalse(
            seeds[0].metadata["routing_evidence"]["workflow_requires_multi_signal"]
        )

    def test_mine_candidate_seed_assessment_rejects_weak_extraction_before_promotion(self) -> None:
        bundle = SimpleNamespace(
            profile={
                "seed_node_types": ["principle_signal"],
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    },
                    "workflow_script": {
                        "workflow_certainty": "high",
                        "context_certainty": "high",
                    },
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "high",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "workflow_script",
                        "disposition": "workflow_script_candidate",
                    },
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    },
                ],
            },
            skills={},
            manifest={
                "bundle_id": "synthetic-extraction-bundle",
                "graph": {"graph_hash": "sha256:synthetic"},
            },
        )
        graph = normalize_graph(
            {
                "graph_version": "kiu.graph/v0.2",
                "source_snapshot": "synthetic-source",
                "graph_hash": "sha256:synthetic",
                "nodes": [
                    {
                        "id": "principle::0009",
                        "type": "principle_signal",
                        "label": "Verbose Checklist Without Evidence",
                        "source_file": "sources/synthetic.md",
                        "source_location": {"line_start": 5, "line_end": 5},
                        "extraction_kind": "EXTRACTED",
                        "routing_hints": {
                            "workflow_cues": 3,
                            "context_cues": 1,
                            "matched_keywords": ["步骤", "清单"],
                            "evidence_chunk_ids": ["synthetic:0009"],
                        },
                    }
                ],
                "edges": [],
                "communities": [],
            }
        )

        assessment = mine_candidate_seed_assessment(bundle, graph)

        self.assertEqual(assessment["summary"]["accepted_candidate_count"], 0)
        self.assertEqual(assessment["summary"]["rejected_candidate_count"], 1)
        self.assertEqual(mine_candidate_seeds(bundle, graph), [])
        rejection = assessment["rejected"][0]
        self.assertEqual(rejection["candidate_id"], "verbose-checklist-without-evidence")
        self.assertIn("missing_extracted_evidence", rejection["reasons"])
        self.assertFalse(rejection["verification"]["passed"])

    def test_scaffold_extraction_bundle_cli_connects_extracted_graph_to_candidate_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"
            source_chunks_path = tmp_root / "source-chunks.json"
            extraction_output_path = tmp_root / "extraction-result.json"
            graph_output_path = tmp_root / "graph.json"
            source_root = tmp_root / "sources"
            output_root = tmp_root / "generated"

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

            scaffold = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "scaffold_extraction_bundle.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--graph",
                    str(graph_output_path),
                    "--output-root",
                    str(source_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)
            scaffold_payload = json.loads(scaffold.stdout)
            bundle_root = Path(scaffold_payload["bundle_root"])

            manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
            self.assertEqual(manifest["graph"]["graph_version"], "kiu.graph/v0.2")
            self.assertEqual(manifest["domain"], "default")

            build = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(bundle_root),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "heuristic-extraction-smoke",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)

            run_root = output_root / manifest["bundle_id"] / "heuristic-extraction-smoke"
            metrics = json.loads((run_root / "reports" / "metrics.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(metrics["summary"]["workflow_script_candidates"], 2)

            workflow_dirs = [path for path in (run_root / "workflow_candidates").glob("*") if path.is_dir()]
            self.assertEqual(len(workflow_dirs), metrics["summary"]["workflow_script_candidates"])

            candidate_doc = yaml.safe_load(
                (workflow_dirs[0] / "candidate.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(
                candidate_doc["routing_evidence"]["inference_mode"],
                "extraction_derived",
            )

    def test_build_graph_report_cli_emits_navigation_report_for_extraction_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"
            source_chunks_path = tmp_root / "source-chunks.json"
            extraction_output_path = tmp_root / "extraction-result.json"
            graph_output_path = tmp_root / "graph.json"
            source_root = tmp_root / "sources"

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

            scaffold = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "scaffold_extraction_bundle.py"),
                    "--source-chunks",
                    str(source_chunks_path),
                    "--graph",
                    str(graph_output_path),
                    "--output-root",
                    str(source_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(scaffold.returncode, 0, scaffold.stdout + scaffold.stderr)
            bundle_root = Path(json.loads(scaffold.stdout)["bundle_root"])

            build_report = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_graph_report.py"),
                    "--bundle",
                    str(bundle_root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build_report.returncode, 0, build_report.stdout + build_report.stderr)

            manifest = yaml.safe_load((bundle_root / "manifest.yaml").read_text(encoding="utf-8"))
            self.assertEqual(manifest["graph_report"]["path"], "GRAPH_REPORT.md")

            report_text = (bundle_root / "GRAPH_REPORT.md").read_text(encoding="utf-8")
            self.assertIn("## God Nodes", report_text)
            self.assertIn("## Communities", report_text)
            self.assertIn("## Suggested Questions", report_text)
            self.assertIn("Problem-First Requirements Analysis", report_text)

    def test_run_book_pipeline_cli_emits_end_to_end_outputs_for_example_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "artifacts"
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_book_pipeline.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--run-id",
                    "end-to-end-smoke",
                    "--output-root",
                    str(output_root),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            payload = json.loads(result.stdout)
            source_bundle_root = Path(payload["source_bundle_root"])
            run_root = Path(payload["run_root"])
            graph_report_path = Path(payload["graph_report_path"])
            review_path = Path(payload["three_layer_review_path"])

            self.assertTrue(source_bundle_root.exists())
            self.assertTrue(run_root.exists())
            self.assertTrue(graph_report_path.exists())
            self.assertTrue(review_path.exists())

            metrics = json.loads((run_root / "reports" / "metrics.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(metrics["summary"]["workflow_script_candidates"], 2)

            manifest = yaml.safe_load(
                (run_root / "bundle" / "manifest.yaml").read_text(encoding="utf-8")
            )
            skill_ids = [entry["skill_id"] for entry in manifest["skills"]]
            self.assertEqual(len(skill_ids), len(set(skill_ids)))

            review_doc = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertIn("overall_score_100", review_doc)
            self.assertGreaterEqual(review_doc["generated_bundle"]["skill_count"], 1)
            self.assertGreaterEqual(review_doc["generated_bundle"]["workflow_candidate_count"], 2)

            verification_summary = json.loads(
                (run_root / "reports" / "verification-summary.json").read_text(encoding="utf-8")
            )
            self.assertGreaterEqual(verification_summary["accepted_candidate_count"], 1)
            self.assertIn("accepted", verification_summary)
            rejection_log = yaml.safe_load(
                (run_root / "reports" / "rejection-log.yaml").read_text(encoding="utf-8")
            )
            self.assertIn("rejected", rejection_log)

    def test_run_book_pipeline_cli_emits_non_placeholder_candidate_and_usage_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "artifacts"
            source_path = ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_book_pipeline.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--run-id",
                    "quality-smoke",
                    "--output-root",
                    str(output_root),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            run_root = Path(payload["run_root"])

            usage_root = run_root / "usage-review"
            usage_docs = sorted(usage_root.glob("*.yaml"))
            self.assertTrue(usage_docs)
            usage_doc = yaml.safe_load(usage_docs[0].read_text(encoding="utf-8"))
            structured_output = usage_doc["structured_output"]
            self.assertNotIn(
                structured_output["next_action"],
                {
                    "collect_more_info",
                    "gather_more_info",
                    "review_more",
                    "review_source_evidence",
                },
            )
            self.assertTrue(structured_output["evidence_to_check"])
            self.assertIn("decline_reason", structured_output)

            production_quality = json.loads(
                (run_root / "reports" / "production-quality.json").read_text(encoding="utf-8")
            )
            skill_report = production_quality["skills"][0]
            self.assertNotIn("placeholder_contract", skill_report["blockers"])
            self.assertNotIn("generic_trigger_contract", skill_report["blockers"])
            self.assertNotIn("placeholder_rationale", skill_report["blockers"])
            self.assertNotIn("missing_trace_examples", skill_report["blockers"])
            self.assertGreaterEqual(skill_report["artifact_quality"], 0.55)

            review_doc = json.loads(
                (run_root / "reports" / "three-layer-review.json").read_text(encoding="utf-8")
            )
            self.assertGreaterEqual(review_doc["source_bundle"]["score_100"], 85.0)
            self.assertIn("graph_report_present", review_doc["source_bundle"]["notes"])
            self.assertIn("provenance_graph_complete", review_doc["source_bundle"]["notes"])
            self.assertIn("tri_state_effective", review_doc["source_bundle"]["notes"])
            self.assertNotIn("tri_state_coverage_partial", review_doc["source_bundle"]["notes"])
            extraction_kind_counts = review_doc["source_bundle"]["provenance"]["extraction_kind_counts"]
            self.assertGreater(extraction_kind_counts["EXTRACTED"], 0)
            self.assertGreater(extraction_kind_counts["INFERRED"], 0)
            self.assertGreater(extraction_kind_counts["AMBIGUOUS"], 0)
            tri_state_effectiveness = review_doc["source_bundle"]["tri_state_effectiveness"]
            self.assertEqual(tri_state_effectiveness["candidate_coverage_ratio"], 1.0)
            self.assertGreater(tri_state_effectiveness["inferred_edge_reference_ratio"], 0.0)
            self.assertGreater(tri_state_effectiveness["ambiguous_node_reference_ratio"], 0.0)
            self.assertGreater(review_doc["usage_outputs"]["score_100"], 0.0)
            self.assertEqual(
                review_doc["usage_outputs"]["failure_tag_counts"].get("next_step_blunt", 0),
                0,
            )
            self.assertNotIn("next_step_quality_weak", review_doc["release_gate"]["reasons"])
            self.assertTrue(review_doc["release_gate"]["overall_ready"])

            generated_manifest = yaml.safe_load(
                (run_root / "bundle" / "manifest.yaml").read_text(encoding="utf-8")
            )
            first_skill_entry = generated_manifest["skills"][0]
            first_skill_dir = run_root / "bundle" / first_skill_entry["path"]
            first_skill_markdown = (first_skill_dir / "SKILL.md").read_text(encoding="utf-8")
            contract = extract_yaml_section(parse_sections(first_skill_markdown).get("Contract", ""))
            trigger = contract.get("trigger", {})
            boundary = contract.get("boundary", {})
            intake = contract.get("intake", {})
            judgment_schema = contract.get("judgment_schema", {})
            output_schema = judgment_schema.get("output", {}).get("schema", {})

            for pattern in trigger.get("patterns", []):
                self.assertNotIn("_needed", pattern)
                self.assertNotIn("_decision_window", pattern)
            for exclusion in trigger.get("exclusions", []):
                self.assertNotIn("_out_of_scope", exclusion)
            self.assertIn("concept_query_only", trigger.get("exclusions", []))
            self.assertIn("scenario_missing_decision_context", boundary.get("do_not_fire_when", []))
            self.assertIn("disconfirming_evidence_present", boundary.get("fails_when", []))

            intake_names = [
                item.get("name")
                for item in intake.get("required", [])
                if isinstance(item, dict)
            ]
            self.assertIn("disconfirming_evidence", intake_names)
            self.assertIn("decision_scope", intake_names)
            self.assertIn("evidence_to_check", output_schema)
            self.assertIn("decline_reason", output_schema)

            scenario_families_path = first_skill_dir / "usage" / "scenarios.yaml"
            self.assertTrue(scenario_families_path.exists())
            scenario_families = yaml.safe_load(
                scenario_families_path.read_text(encoding="utf-8")
            )
            self.assertIn("should_trigger", scenario_families)
            self.assertIn("should_not_trigger", scenario_families)
            self.assertIn("edge_case", scenario_families)
            self.assertIn("refusal", scenario_families)
            self.assertIn("Scenario families:", first_skill_markdown)

    def test_run_book_pipeline_cli_accepts_source_markdown_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            output_root = tmp_root / "artifacts"
            source_path = tmp_root / "external-source.md"
            source_path.write_text(
                (
                    "# External Fixture Source\n\n"
                    "## Decision Boundary Note\n\n"
                    "Checklist discipline matters only when the scenario already contains a concrete decision and explicit constraints.\n\n"
                    "## Failure-First Review\n\n"
                    "Before acting, enumerate failure modes and refuse the move if the remaining downside is still unacceptable.\n"
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_book_pipeline.py"),
                    "--input",
                    str(source_path),
                    "--bundle-id",
                    "external-source-bundle",
                    "--source-id",
                    "external-fixture",
                    "--run-id",
                    "outside-repo-source",
                    "--output-root",
                    str(output_root),
                    "--max-chars",
                    "220",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            source_bundle_root = Path(payload["source_bundle_root"])
            copied_source = source_bundle_root / "sources" / source_path.name
            self.assertTrue(copied_source.exists())

            source_chunks_doc = json.loads(
                (source_bundle_root / "ingestion" / "source-chunks-v0.1.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(source_chunks_doc["source_file"], f"sources/{source_path.name}")

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
