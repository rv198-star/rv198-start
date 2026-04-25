from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from kiu_pipeline.review import _score_generated_bundle
from kiu_pipeline.world_alignment_metrics import build_world_alignment_value_metrics
from kiu_pipeline.world_alignment import (
    build_world_alignment_gate_evidence,
    build_world_alignment_artifacts,
    review_world_alignment,
    validate_no_web_world_alignment,
)


class WorldAlignmentTests(unittest.TestCase):
    def test_generates_isolated_artifacts_without_mutating_source_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"solution-to-problem-reframing": "Solution To Problem Reframing"})
            skill_path = bundle / "skills" / "solution-to-problem-reframing" / "SKILL.md"
            before = skill_path.read_text(encoding="utf-8")

            summary = build_world_alignment_artifacts(bundle, no_web_mode=True)

            self.assertEqual(summary["skill_count"], 1)
            self.assertEqual(before, skill_path.read_text(encoding="utf-8"))
            self.assertTrue((bundle / "world_alignment" / "world_context.yaml").exists())
            gate_path = bundle / "world_alignment" / "solution-to-problem-reframing" / "application_gate.yaml"
            md_path = bundle / "world_alignment" / "solution-to-problem-reframing" / "WORLD_ALIGNMENT.md"
            self.assertTrue(gate_path.exists())
            self.assertTrue(md_path.exists())
            gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
            self.assertTrue(gate["source_skill_unchanged"])
            self.assertTrue(gate["world_context_isolated"])
            self.assertFalse(gate["web_check_performed"])
            self.assertEqual(gate["verdict"], "apply_with_caveats")
            md = md_path.read_text(encoding="utf-8")
            self.assertIn("Original-Source-Only Mode", md)
            self.assertIn("No-Web Disclosure", md)

    def test_no_web_preflight_blocks_current_fact_claims_and_agentic_overgeneralization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"solution-to-problem-reframing": "Solution To Problem Reframing"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)
            md_path = bundle / "world_alignment" / "solution-to-problem-reframing" / "WORLD_ALIGNMENT.md"
            md_path.write_text(
                md_path.read_text(encoding="utf-8")
                + "\n当前市场最新监管已经证明 AI 已经彻底改变所有需求分析流程。\n",
                encoding="utf-8",
            )

            report = validate_no_web_world_alignment(bundle)

            self.assertFalse(report["passed"])
            self.assertGreaterEqual(report["keyword_preflight"]["error_count"], 1)
            self.assertGreaterEqual(report["agentic_review"]["finding_count"], 1)
            self.assertIn("apply", report["agentic_review"]["blocked_verdicts"])

    def test_high_sensitivity_financial_skill_cannot_apply_without_web_or_current_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"financial-statement-current-investment-check": "Financial Statement Current Investment Check"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            gate = yaml.safe_load(
                (bundle / "world_alignment" / "financial-statement-current-investment-check" / "application_gate.yaml").read_text(encoding="utf-8")
            )

            self.assertIn(gate["verdict"], {"ask_more_context", "refuse"})
            self.assertNotEqual(gate["verdict"], "apply")
            self.assertEqual(gate["temporal_sensitivity"], "high")
            self.assertIn("current data", " ".join(gate["required_context"]).lower())

    def test_transfer_candidate_gate_includes_transfer_fit_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"historical-analogy-transfer-gate": "Historical Analogy Transfer Gate"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            gate = yaml.safe_load(
                (bundle / "world_alignment" / "historical-analogy-transfer-gate" / "application_gate.yaml").read_text(encoding="utf-8")
            )

            self.assertEqual(gate["use_state"], "transfer_candidate")
            self.assertEqual(gate["transfer_fit"]["transfer_readiness"], "ask_more_context")
            self.assertGreaterEqual(len(gate["transfer_fit"]["fit_questions"]), 2)
            self.assertIn("mechanism", " ".join(gate["transfer_fit"]["fit_questions"]).lower())

    def test_low_risk_reflection_gate_does_not_force_transfer_fit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"quiet-reflection": "Quiet Reflection"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            gate = yaml.safe_load(
                (bundle / "world_alignment" / "quiet-reflection" / "application_gate.yaml").read_text(encoding="utf-8")
            )

            self.assertEqual(gate["transfer_fit"]["transfer_readiness"], "not_applicable")
            self.assertEqual(gate["transfer_fit"]["fit_questions"], [])

    def test_generic_case_study_word_does_not_trigger_transfer_fit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"mini-case-analysis": "Mini Case Analysis"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            gate = yaml.safe_load(
                (bundle / "world_alignment" / "mini-case-analysis" / "application_gate.yaml").read_text(encoding="utf-8")
            )

            self.assertNotEqual(gate["use_state"], "transfer_candidate")
            self.assertEqual(gate["transfer_fit"]["transfer_readiness"], "not_applicable")

    def test_current_investment_advice_refuses_in_no_web_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"current-investment-advice": "Current Investment Advice"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            gate = yaml.safe_load(
                (bundle / "world_alignment" / "current-investment-advice" / "application_gate.yaml").read_text(encoding="utf-8")
            )

            self.assertEqual(gate["verdict"], "refuse")
            self.assertFalse(gate["web_check_performed"])
            self.assertIn("current financial or investment advice", gate["reason"].lower())


    def test_review_scores_world_alignment_and_detects_source_pollution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"solution-to-problem-reframing": "Solution To Problem Reframing"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            clean = review_world_alignment(bundle)
            self.assertTrue(clean["source_fidelity_preserved"])
            self.assertTrue(clean["world_context_isolated"])
            self.assertEqual(clean["source_pollution_errors"], 0)
            self.assertGreaterEqual(clean["world_alignment_score_100"], 85.0)

            skill_path = bundle / "skills" / "solution-to-problem-reframing" / "SKILL.md"
            skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\nAI 原型工具降低了需求验证成本。\n", encoding="utf-8")
            polluted = review_world_alignment(bundle)
            self.assertFalse(polluted["source_fidelity_preserved"])
            self.assertGreater(polluted["source_pollution_errors"], 0)

    def test_cli_generates_and_reviews_world_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"solution-to-problem-reframing": "Solution To Problem Reframing"})

            generate = _run_cli("scripts/generate_world_alignment.py", "--bundle", str(bundle), "--no-web")
            self.assertEqual(generate.returncode, 0, generate.stderr)
            self.assertIn("skill_count", generate.stdout)

            review = _run_cli("scripts/review_world_alignment.py", "--bundle", str(bundle), "--output", str(Path(tmp) / "review.json"))
            self.assertEqual(review.returncode, 0, review.stderr)
            self.assertIn("world_alignment_score_100", review.stdout)
            self.assertTrue((Path(tmp) / "review.json").exists())

    def test_generated_bundle_review_includes_world_alignment_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run"
            bundle = _write_bundle(run_root, {"solution-to-problem-reframing": "Solution To Problem Reframing"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            scored = _score_generated_bundle(
                generated_report={"errors": [], "warnings": []},
                production_quality={
                    "minimum_production_quality": 0.9,
                    "average_production_quality": 0.9,
                    "candidate_count": 1,
                    "bundle_quality_grade": "excellent",
                },
                metrics={"summary": {"workflow_script_candidates": 0}},
                run_root=run_root,
                pressure_report=None,
            )

            self.assertIn("world_alignment", scored)
            self.assertGreaterEqual(scored["world_alignment"]["world_alignment_score_100"], 85.0)
            self.assertIn("world_alignment_present", scored["notes"])

    def test_world_context_uses_agentic_loop_to_avoid_generic_medium_sensitivity_modeling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(
                Path(tmp),
                {"business-first-subsystem-decomposition": "Business First Subsystem Decomposition"},
            )
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context = yaml.safe_load((bundle / "world_alignment" / "world_context.yaml").read_text(encoding="utf-8"))
            item = context["items"][0]
            summary = item["summary"]
            pressure_text = " ".join(item.get("pressure_dimensions", []))

            self.assertGreaterEqual(item["world_context_depth_score"], 80.0)
            self.assertGreaterEqual(item["deepening_rounds"], 2)
            self.assertIn(item["loop_mode"], {"workflow_plus_agentic_proxy", "workflow_plus_agentic"})
            self.assertNotIn("Real-world organizational practices and tooling may change", summary)
            self.assertIn("AI-assisted prototyping", pressure_text)
            self.assertIn("cross-functional ownership", pressure_text)
            self.assertIn("subsystem boundary", pressure_text)

            md = (bundle / "world_alignment" / "business-first-subsystem-decomposition" / "WORLD_ALIGNMENT.md").read_text(encoding="utf-8")
            self.assertIn("## World Hypothesis", md)
            self.assertIn("## Why This Matters", md)
            self.assertIn("## What To Ask User", md)
            self.assertIn("## No-Web Unverified Status", md)

    def test_world_alignment_need_score_controls_intervention_without_type_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(
                Path(tmp),
                {
                    "circle-of-competence": "Circle Of Competence",
                    "business-first-subsystem-decomposition": "Business First Subsystem Decomposition",
                    "challenge-price-with-value": "Challenge Price With Value",
                },
            )
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context = yaml.safe_load((bundle / "world_alignment" / "world_context.yaml").read_text(encoding="utf-8"))
            items = {item["applies_to"][0]: item for item in context["items"]}

            self.assertLess(items["circle-of-competence"]["world_alignment_need_score"], 0.5)
            self.assertIn(items["circle-of-competence"]["intervention_level"], {"minimal", "light"})
            self.assertGreaterEqual(items["business-first-subsystem-decomposition"]["world_alignment_need_score"], 0.5)
            self.assertEqual(items["business-first-subsystem-decomposition"]["intervention_level"], "moderate")
            self.assertGreaterEqual(items["challenge-price-with-value"]["world_alignment_need_score"], 0.75)
            self.assertEqual(items["challenge-price-with-value"]["intervention_level"], "strong_gate")

    def test_candidate_relevance_arbitration_rejects_off_domain_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"circle-of-competence": "Circle Of Competence"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context = yaml.safe_load((bundle / "world_alignment" / "world_context.yaml").read_text(encoding="utf-8"))
            item = context["items"][0]
            pressure_text = " ".join(item.get("pressure_dimensions", []))
            arbitration = item.get("candidate_pressure_arbitration", [])

            self.assertTrue(arbitration)
            self.assertNotIn("AI-assisted prototyping", pressure_text)
            self.assertNotIn("subsystem boundary", pressure_text)
            self.assertNotIn("business accountability", pressure_text)
            self.assertTrue(any(record.get("accepted") for record in arbitration))
            self.assertTrue(
                all(
                    {
                        "source_fit_score",
                        "enrichment_value_score",
                        "application_need_score",
                        "dilution_risk_score",
                        "hallucination_risk_score",
                        "accepted",
                    }.issubset(record)
                    for record in arbitration
                )
            )

    def test_no_forced_enhancement_when_no_relevant_pressure_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"quiet-reflection": "Quiet Reflection"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context = yaml.safe_load((bundle / "world_alignment" / "world_context.yaml").read_text(encoding="utf-8"))
            item = context["items"][0]
            md = (bundle / "world_alignment" / "quiet-reflection" / "WORLD_ALIGNMENT.md").read_text(encoding="utf-8")

            self.assertTrue(item["no_forced_enhancement"])
            self.assertEqual(item["intervention_level"], "minimal")
            self.assertEqual(item["pressure_dimensions"], [])
            self.assertIn("no_forced_enhancement", md)
            self.assertGreaterEqual(item["source_fit_score"], 80.0)
            self.assertLessEqual(item["dilution_risk_score"], 20.0)

    def test_review_penalizes_unverified_current_fact_pressure_in_no_web_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"challenge-price-with-value": "Challenge Price With Value"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context_path = bundle / "world_alignment" / "world_context.yaml"
            context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
            context["items"][0]["summary"] = "Latest market data proves this company is undervalued today."
            context["items"][0]["pressure_dimensions"] = [
                "Latest market data proves this company is undervalued today.",
                "Current regulatory filings prove direct application is safe now.",
            ]
            context["items"][0]["world_context_depth_score"] = 100.0
            context_path.write_text(yaml.safe_dump(context, sort_keys=False, allow_unicode=True), encoding="utf-8")

            reviewed = review_world_alignment(bundle)

            self.assertFalse(reviewed["no_web_risk_control"]["passed"])
            self.assertGreater(reviewed["scores"]["hallucination_risk_score"], 50.0)
            self.assertIn("hallucination_risk", reviewed["quality_findings"])
            self.assertLess(reviewed["world_alignment_score_100"], 85.0)


    def test_builds_release_gate_evidence_scorecard_from_sample_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundles = [
                _write_bundle(
                    root / "poor",
                    {
                        "circle-of-competence": "Circle Of Competence",
                        "invert-the-problem": "Invert The Problem",
                        "bias-self-audit": "Bias Self Audit",
                        "value-assessment-source-note": "Value Assessment Source Note",
                        "role-boundary-before-action": "Role Boundary Before Action",
                    },
                ),
                _write_bundle(
                    root / "requirements",
                    {
                        "business-first-subsystem-decomposition": "Business First Subsystem Decomposition",
                        "stakeholder-conflict-clarification": "Stakeholder Conflict Clarification",
                    },
                ),
                _write_bundle(
                    root / "finance",
                    {
                        "financial-statement-current-investment-check": "Financial Statement Current Investment Check",
                        "challenge-price-with-value": "Challenge Price With Value",
                    },
                ),
                _write_bundle(root / "refuse", {"current-investment-advice": "Current Investment Advice"}),
            ]
            for bundle in bundles:
                build_world_alignment_artifacts(bundle, no_web_mode=True)

            evidence = build_world_alignment_gate_evidence(bundles)

            self.assertTrue(evidence["passed"])
            self.assertGreaterEqual(evidence["checks"]["samples_passed"]["actual"], 3)
            self.assertGreaterEqual(evidence["checks"]["application_gate_cases"]["actual"], 9)
            self.assertEqual(evidence["checks"]["source_pollution_errors"]["actual"], 0)
            self.assertGreaterEqual(evidence["checks"]["world_alignment_score_min"]["actual"], 85.0)
            self.assertGreaterEqual(evidence["checks"]["world_context_depth_score_min"]["actual"], 80.0)
            self.assertGreater(evidence["mechanism_counts"]["candidate_arbitration_count"], 0)
            self.assertGreater(evidence["mechanism_counts"]["source_fit_review_count"], 0)
            self.assertIn("apply", evidence["verdict_counts"])
            self.assertIn("ask_more_context", evidence["verdict_counts"])
            self.assertIn("refuse", evidence["verdict_counts"])

    def test_release_gate_evidence_fails_when_source_skill_is_polluted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"circle-of-competence": "Circle Of Competence"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)
            skill_path = bundle / "skills" / "circle-of-competence" / "SKILL.md"
            skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\nworld_context_isolated: true\n", encoding="utf-8")

            evidence = build_world_alignment_gate_evidence([bundle])

            self.assertFalse(evidence["passed"])
            self.assertFalse(evidence["checks"]["source_fidelity_preserved"]["passed"])
            self.assertGreater(evidence["checks"]["source_pollution_errors"]["actual"], 0)


    def test_builds_value_metrics_with_release_gate_and_stretch_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundles = [
                _write_bundle(
                    root / "poor",
                    {
                        "circle-of-competence": "Circle Of Competence",
                        "invert-the-problem": "Invert The Problem",
                        "bias-self-audit": "Bias Self Audit",
                        "value-assessment-source-note": "Value Assessment Source Note",
                        "role-boundary-before-action": "Role Boundary Before Action",
                    },
                ),
                _write_bundle(
                    root / "requirements",
                    {
                        "business-first-subsystem-decomposition": "Business First Subsystem Decomposition",
                        "stakeholder-conflict-clarification": "Stakeholder Conflict Clarification",
                    },
                ),
                _write_bundle(
                    root / "finance",
                    {
                        "financial-statement-current-investment-check": "Financial Statement Current Investment Check",
                        "challenge-price-with-value": "Challenge Price With Value",
                    },
                ),
                _write_bundle(root / "refuse", {"current-investment-advice": "Current Investment Advice"}),
            ]
            for bundle in bundles:
                build_world_alignment_artifacts(bundle, no_web_mode=True)

            metrics = build_world_alignment_value_metrics(bundles)

            self.assertTrue(metrics["passed"])
            self.assertGreaterEqual(metrics["metrics"]["alignment_usage_delta"], 0.3)
            self.assertGreaterEqual(metrics["metrics"]["misuse_intercept_rate"], 95.0)
            self.assertGreaterEqual(metrics["metrics"]["temporal_sensitivity_response"], 90.0)
            self.assertGreaterEqual(metrics["metrics"]["verdict_diversity_score"], 4)
            self.assertGreaterEqual(metrics["metrics"]["no_forced_enhancement_rate"], 20.0)
            self.assertGreaterEqual(metrics["metrics"]["application_gate_cases"], 30)
            self.assertEqual(metrics["metrics"]["source_pollution_errors"], 0)
            self.assertIn("misuse_intercept", metrics["case_type_counts"])
            self.assertIn("temporal_missing_current_fact", metrics["case_type_counts"])

    def test_no_web_hallucination_fixture_matrix_blocks_unsafe_claims_and_allows_safe_caveats(self) -> None:
        unsafe_claims = [
            "According to recent reports, the market now confirms this strategy always works.",
            "Studies show regulators increasingly require this method in 2026.",
            "Most companies now use this approach successfully.",
            "As of 2026, industry data confirms this is the dominant practice.",
            "据最新研究，行业数据显示这个方法已经成为通用最佳实践。",
            "监管趋势表明现在必须采用这个判断框架。",
        ]
        safe_caveats = [
            "No web lookup was performed; ask the user for current evidence before applying this method.",
            "This may be a useful hypothesis, but it is unverified and should only guide user-context questions.",
            "当前事实未验证，需要用户提供最新数据后才能判断。",
            "可能存在行业变化，但本产物不声称已经验证。",
        ]

        for claim in unsafe_claims:
            with self.subTest(claim=claim):
                with tempfile.TemporaryDirectory() as tmp:
                    bundle = _write_bundle(Path(tmp), {"challenge-price-with-value": "Challenge Price With Value"})
                    build_world_alignment_artifacts(bundle, no_web_mode=True)
                    md_path = bundle / "world_alignment" / "challenge-price-with-value" / "WORLD_ALIGNMENT.md"
                    md_path.write_text(md_path.read_text(encoding="utf-8") + "\n" + claim + "\n", encoding="utf-8")

                    report = validate_no_web_world_alignment(bundle)

                    self.assertFalse(report["passed"])
                    self.assertGreater(
                        report["keyword_preflight"]["error_count"] + report["agentic_review"]["finding_count"],
                        0,
                    )

        for caveat in safe_caveats:
            with self.subTest(caveat=caveat):
                with tempfile.TemporaryDirectory() as tmp:
                    bundle = _write_bundle(Path(tmp), {"challenge-price-with-value": "Challenge Price With Value"})
                    build_world_alignment_artifacts(bundle, no_web_mode=True)
                    md_path = bundle / "world_alignment" / "challenge-price-with-value" / "WORLD_ALIGNMENT.md"
                    md_path.write_text(md_path.read_text(encoding="utf-8") + "\n" + caveat + "\n", encoding="utf-8")

                    report = validate_no_web_world_alignment(bundle)

                    self.assertTrue(report["passed"])

    def test_candidate_arbitration_rejects_high_hallucination_risk_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"challenge-price-with-value": "Challenge Price With Value"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context = yaml.safe_load((bundle / "world_alignment" / "world_context.yaml").read_text(encoding="utf-8"))
            records = context["items"][0]["candidate_pressure_arbitration"]
            risky = [
                record for record in records
                if "current market data" in record["candidate"].lower()
            ]

            self.assertTrue(risky)
            self.assertTrue(all(record["hallucination_risk_score"] <= 50.0 for record in risky))
            self.assertTrue(all(record["accepted"] for record in risky))

    def test_review_penalizes_source_diluting_world_context_even_when_structurally_deep(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"circle-of-competence": "Circle Of Competence"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context_path = bundle / "world_alignment" / "world_context.yaml"
            context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
            context["items"][0]["pressure_dimensions"] = [
                "AI-assisted prototyping can make technical slices cheap, so the gate should still test subsystem boundary choices.",
                "cross-functional ownership can blur product, engineering, data, and operations boundaries.",
                "business accountability should govern the decomposition."
            ]
            context["items"][0]["world_context_depth_score"] = 100.0
            context_path.write_text(yaml.safe_dump(context, sort_keys=False, allow_unicode=True), encoding="utf-8")

            reviewed = review_world_alignment(bundle)

            self.assertLess(reviewed["scores"]["source_fit_score"], 80.0)
            self.assertGreater(reviewed["scores"]["dilution_risk_score"], 20.0)
            self.assertLess(reviewed["world_alignment_score_100"], 85.0)
            self.assertIn("source_dilution_risk", reviewed["quality_findings"])

    def test_world_alignment_review_penalizes_generic_world_context_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _write_bundle(Path(tmp), {"business-first-subsystem-decomposition": "Business First Subsystem Decomposition"})
            build_world_alignment_artifacts(bundle, no_web_mode=True)

            context_path = bundle / "world_alignment" / "world_context.yaml"
            context = yaml.safe_load(context_path.read_text(encoding="utf-8"))
            context["items"][0]["summary"] = "Real-world organizational practices and tooling may change how this source-derived method should be applied; treat this as an unverified no-web hypothesis."
            context["items"][0]["pressure_dimensions"] = []
            context["items"][0]["world_context_depth_score"] = 35.0
            context_path.write_text(yaml.safe_dump(context, sort_keys=False, allow_unicode=True), encoding="utf-8")

            reviewed = review_world_alignment(bundle)

            self.assertLess(reviewed["scores"]["world_context_depth_score"], 60.0)
            self.assertLess(reviewed["world_alignment_score_100"], 85.0)


def _write_bundle(root: Path, skills: dict[str, str]) -> Path:
    bundle = root / "bundle"
    (bundle / "skills").mkdir(parents=True)
    manifest_skills = []
    for skill_id, title in skills.items():
        skill_dir = bundle / "skills" / skill_id
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"# {title}\n\n## Identity\n```yaml\nskill_id: {skill_id}\ntitle: {title}\n```\n\n## Rationale\nSource-faithful rationale only.\n\n## Usage Summary\nUse the source-derived skill within its native boundary.\n",
            encoding="utf-8",
        )
        manifest_skills.append({"skill_id": skill_id, "path": f"skills/{skill_id}"})
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump({"bundle_id": "test-bundle", "skills": manifest_skills}, sort_keys=False),
        encoding="utf-8",
    )
    return bundle


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = None
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, check=False, cwd=Path(__file__).resolve().parents[1], env=env)


if __name__ == "__main__":
    unittest.main()
