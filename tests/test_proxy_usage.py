from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from kiu_pipeline.proxy_usage import write_proxy_usage_reviews
from kiu_pipeline.review import review_generated_run


class ProxyUsageTests(unittest.TestCase):
    def test_generates_randomized_proxy_cases_with_required_case_type_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = _write_run(Path(tmp), {"business-first-subsystem-decomposition": "Business First Subsystem Decomposition"})

            payload = write_proxy_usage_reviews(run_root, cases_per_skill=8, seed="fixed")

            self.assertEqual(payload["case_count"], 8)
            summary = payload["summary"]
            self.assertTrue(summary["gate_ready"])
            self.assertGreaterEqual(summary["score_100"], 90.0)
            for case_type in (
                "should_fire",
                "should_not_fire",
                "edge_case",
                "world_alignment_case",
                "high_risk_or_missing_context",
            ):
                self.assertGreater(summary["case_type_counts"].get(case_type, 0), 0)

            docs = [
                yaml.safe_load(path.read_text(encoding="utf-8"))
                for path in sorted((run_root / "proxy-usage-review").glob("*.yaml"))
                if path.name != "summary.yaml"
            ]
            prompts = [doc["input_prompt"] for doc in docs]
            self.assertFalse(any(prompt.startswith("## ") for prompt in prompts))
            self.assertTrue(any("现实压力" in prompt and ("AI" in prompt or "cross-functional" in prompt) for prompt in prompts))
            self.assertTrue(any(doc["case_type"] == "should_not_fire" and doc["expected_verdict"] == "do_not_apply" for doc in docs))
            for doc in docs:
                self.assertIn("expected_use_state", doc)
                self.assertIn("predicted_use_state", doc["proxy_evaluator"])

    def test_proxy_usage_uses_use_state_to_block_direct_apply_on_risky_general_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = _write_run(Path(tmp), {"historical-analogy-transfer-gate": "Historical Analogy Transfer Gate"})

            payload = write_proxy_usage_reviews(run_root, cases_per_skill=8, seed="kiu-v072-eval-proxy")
            summary = payload["summary"]

            self.assertEqual(summary["failure_tag_counts"].get("boundary_leak", 0), 0)
            self.assertEqual(summary["failure_tag_counts"].get("wrong_verdict", 0), 0)
            self.assertTrue(summary["gate_ready"])
            self.assertGreaterEqual(summary["score_100"], 85.0)

    def test_proxy_usage_cli_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = _write_run(Path(tmp), {"challenge-price-with-value": "Challenge Price With Value"})

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/generate_proxy_usage.py",
                    "--run-root",
                    str(run_root),
                    "--cases-per-skill",
                    "7",
                    "--seed",
                    "cli-fixed",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["case_count"], 7)
            self.assertTrue((run_root / "proxy-usage-review" / "summary.yaml").exists())
            summary = yaml.safe_load((run_root / "proxy-usage-review" / "summary.yaml").read_text(encoding="utf-8"))
            self.assertIn("claim_boundary", summary)

    def test_generated_run_review_surfaces_proxy_usage_without_replacing_usage_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = _write_run(Path(tmp), {"business-first-subsystem-decomposition": "Business First Subsystem Decomposition"})
            write_proxy_usage_reviews(run_root, cases_per_skill=8, seed="review-fixed")
            usage_root = run_root / "usage-review"
            usage_root.mkdir(parents=True)
            _write_minimal_reports(run_root)

            review = review_generated_run(
                run_root=run_root,
                source_bundle_path=run_root / "bundle",
            )

            self.assertIn("usage_outputs", review)
            self.assertEqual(review["usage_outputs"]["sample_count"], 0)
            self.assertIn("proxy_usage_outputs", review)
            self.assertEqual(review["proxy_usage_outputs"]["case_count"], 8)
            self.assertTrue(review["proxy_usage_outputs"]["gate_ready"])
            self.assertIn("practical_effect_outputs", review)
            self.assertLess(review["practical_effect_outputs"]["score_100"], 90.0)
            self.assertFalse(review["practical_effect_outputs"]["gate_ready"])
            self.assertEqual(review["practical_effect_outputs"]["evidence_level"], "L2_5_proxy_usage")
            self.assertIn("not real user validation", review["practical_effect_outputs"]["claim_boundary"])


def _write_run(root: Path, skills: dict[str, str]) -> Path:
    run_root = root / "run"
    bundle = run_root / "bundle"
    (bundle / "skills").mkdir(parents=True)
    manifest_skills = []
    world_items = []
    for skill_id, title in skills.items():
        skill_dir = bundle / "skills" / skill_id
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"# {title}\n\n## Contract\n```yaml\nskill_id: {skill_id}\ntrigger:\n  patterns:\n    - {skill_id.replace('-', '_')}_decision_required\njudgment_schema:\n  output:\n    schema:\n      verdict: apply\n```\n",
            encoding="utf-8",
        )
        manifest_skills.append({"skill_id": skill_id, "path": f"skills/{skill_id}"})
        world_items.append(
            {
                "applies_to": [skill_id],
                "pressure_dimensions": [
                    "AI-assisted prototyping can make technical slices cheap, so accountability still needs checking.",
                    "cross-functional ownership can blur product, engineering, data, and operations boundaries.",
                ],
            }
        )
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump({"skills": manifest_skills}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (bundle / "graph").mkdir(parents=True)
    (bundle / "graph" / "graph.json").write_text(
        json.dumps({"nodes": [], "edges": []}),
        encoding="utf-8",
    )
    (bundle / "world_alignment").mkdir(parents=True)
    (bundle / "world_alignment" / "world_context.yaml").write_text(
        yaml.safe_dump({"items": world_items}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return run_root


def _write_minimal_reports(run_root: Path) -> None:
    reports = run_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "metrics.json").write_text(
        json.dumps({"summary": {"workflow_script_candidates": 0}}),
        encoding="utf-8",
    )
    (reports / "production-quality.json").write_text(
        json.dumps(
            {
                "minimum_production_quality": 0.9,
                "average_production_quality": 0.9,
                "candidate_count": 1,
                "bundle_quality_grade": "excellent",
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
