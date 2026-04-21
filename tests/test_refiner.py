import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.baseline import build_candidate_baseline
from kiu_pipeline.load import load_source_bundle
from kiu_pipeline.mutate import mutate_candidate
from kiu_pipeline.refiner import refine_candidate
from kiu_pipeline.reports import write_final_decision, write_round_report
from kiu_pipeline.scoring import decide_terminal_state, score_candidate
from kiu_pipeline.seed import derive_candidate_metadata


class RefinerConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"

    def test_load_source_bundle_reads_autonomous_refiner_profile(self) -> None:
        bundle = load_source_bundle(self.bundle_path)
        refiner = bundle.profile["autonomous_refiner"]

        self.assertTrue(refiner["enabled_by_default"])
        self.assertEqual(refiner["max_rounds"], 5)
        self.assertAlmostEqual(refiner["weights"]["boundary_quality"], 0.45)

    def test_seed_metadata_initializes_loop_fields(self) -> None:
        metadata = derive_candidate_metadata(
            candidate_id="circle-of-competence",
            seed_node_id="n_circle_principle",
            candidate_kind="general_agentic",
            graph_hash="sha256:test",
            bundle_id="demo",
            routing_profile={
                "candidate_kinds": {
                    "general_agentic": {
                        "workflow_certainty": "medium",
                        "context_certainty": "high",
                    }
                },
                "routing_rules": [
                    {
                        "when": {
                            "workflow_certainty": "medium",
                            "context_certainty": "high",
                        },
                        "recommended_execution_mode": "llm_agentic",
                        "disposition": "skill_candidate",
                    }
                ],
                "autonomous_refiner": {"enabled_by_default": True},
            },
        )

        self.assertEqual(metadata["loop_mode"], "autonomous_refiner")
        self.assertEqual(metadata["current_round"], 0)
        self.assertEqual(metadata["terminal_state"], "pending")
        self.assertEqual(metadata["human_gate"], "skipped")


class RefinerScoringTests(unittest.TestCase):
    def test_score_candidate_uses_weighted_quality_and_positive_deltas(self) -> None:
        score = score_candidate(
            boundary_quality=0.90,
            eval_aggregate=0.80,
            cross_subset_stability=0.75,
            baseline={
                "nearest_skill_id": "circle-of-competence",
                "nearest_skill_overall_quality": 0.72,
                "bundle_proxy_overall_quality": 0.70,
            },
            bonuses={"clarity": 0.03, "coverage": 0.01},
            weights={
                "boundary_quality": 0.45,
                "eval_aggregate": 0.35,
                "cross_subset_stability": 0.20,
            },
        )

        self.assertAlmostEqual(score["overall_quality"], 0.835)
        self.assertGreater(score["delta_vs_nearest"], 0)
        self.assertGreater(score["delta_vs_bundle"], 0)
        self.assertGreater(score["net_positive_value"], 0)

    def test_decide_terminal_state_returns_do_not_publish_without_positive_value(self) -> None:
        decision = decide_terminal_state(
            round_index=2,
            config={
                "min_rounds": 2,
                "max_rounds": 5,
                "patience": 2,
                "targets": {
                    "overall_quality": 0.82,
                    "boundary_quality": 0.85,
                    "min_positive_delta": 0.03,
                },
            },
            scorecard={
                "overall_quality": 0.81,
                "boundary_quality": 0.86,
                "delta_vs_nearest": -0.01,
                "delta_vs_bundle": 0.02,
                "net_positive_value": -0.01,
            },
            history=[{"overall_quality": 0.79}, {"overall_quality": 0.81}],
            structural_valid=True,
        )

        self.assertEqual(decision["terminal_state"], "do_not_publish")

    def test_build_candidate_baseline_compares_nearest_skill_and_bundle(self) -> None:
        bundle = load_source_bundle(ROOT / "bundles" / "poor-charlies-almanack-v0.1")
        baseline = build_candidate_baseline(
            source_bundle=bundle,
            nearest_skill_id="circle-of-competence",
        )

        self.assertEqual(baseline["nearest_skill_id"], "circle-of-competence")
        self.assertGreater(baseline["nearest_skill_overall_quality"], 0)
        self.assertGreater(baseline["bundle_proxy_overall_quality"], 0)


class RefinerMutationTests(unittest.TestCase):
    def test_mutate_candidate_updates_full_candidate_unit(self) -> None:
        candidate = {
            "skill_markdown": (
                "# Circle of Competence\n\n"
                "## Usage Summary\n"
                "Current trace attachments: 1.\n\n"
                "Representative cases:\n"
                "- `traces/canonical/dotcom-refusal.yaml`\n"
            ),
            "anchors": {"graph_anchor_sets": [], "source_anchor_sets": []},
            "eval_summary": {
                "skill_id": "circle-of-competence",
                "bundle_version": "0.2.0",
                "skill_revision": 1,
                "status": "under_evaluation",
                "kiu_test": {
                    "trigger_test": "pending",
                    "fire_test": "pending",
                    "boundary_test": "pending",
                },
                "subsets": {
                    "real_decisions": {"passed": 0, "total": 4, "status": "pending"},
                    "synthetic_adversarial": {"passed": 0, "total": 4, "status": "pending"},
                    "out_of_distribution": {"passed": 0, "total": 2, "status": "pending"},
                },
            },
            "revisions": {
                "skill_id": "circle-of-competence",
                "bundle_version": "0.2.0",
                "current_revision": 1,
                "history": [
                    {
                        "revision": 1,
                        "date": "2026-04-22",
                        "summary": "Initial seed.",
                        "graph_hash": "sha256:test",
                        "effective_status": "under_evaluation",
                        "evidence_changes": ["Initial seed"],
                    }
                ],
                "open_gaps": [],
            },
            "candidate": {
                "candidate_id": "circle-of-competence",
                "current_round": 0,
                "boundary_quality": 0.70,
                "eval_aggregate": 0.70,
                "cross_subset_stability": 0.70,
                "drafting_mode": "deterministic",
            },
        }

        mutated = mutate_candidate(
            candidate=candidate,
            round_index=1,
            mutation_plan={
                "boundary_strength_delta": 0.10,
                "eval_gain_delta": 0.05,
                "stability_delta": 0.04,
                "append_trace_ref": "traces/canonical/pilot-pre-mortem.yaml",
                "revision_note": "Tightened trigger boundary and added stress trace.",
            },
        )

        self.assertEqual(mutated["candidate"]["current_round"], 1)
        self.assertIn("pilot-pre-mortem.yaml", mutated["skill_markdown"])
        self.assertEqual(mutated["eval_summary"]["status"], "under_evaluation")
        self.assertEqual(mutated["revisions"]["current_revision"], 2)

    def test_write_round_reports_emits_scorecard_and_final_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_root = Path(tmp_dir)

            write_round_report(run_root, 1, {"overall_quality": 0.84, "terminal_state": "pending"})
            write_final_decision(run_root, {"terminal_state": "ready_for_review"})

            self.assertTrue((run_root / "reports" / "rounds" / "round-01.json").exists())
            self.assertTrue((run_root / "reports" / "final-decision.json").exists())


class RefinerLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_source_bundle(ROOT / "bundles" / "poor-charlies-almanack-v0.1")

    def _make_candidate(self, *, boundary_quality: float, eval_aggregate: float, stability: float) -> dict:
        source_skill = self.bundle.skills["circle-of-competence"]
        return {
            "skill_markdown": source_skill.skill_dir.joinpath("SKILL.md").read_text(encoding="utf-8"),
            "anchors": yaml.safe_load(
                source_skill.skill_dir.joinpath("anchors.yaml").read_text(encoding="utf-8")
            ),
            "eval_summary": deepcopy(source_skill.eval_summary),
            "revisions": deepcopy(source_skill.revisions),
            "candidate": {
                "candidate_id": "circle-of-competence",
                "source_bundle_id": self.bundle.manifest["bundle_id"],
                "source_graph_hash": self.bundle.manifest["graph"]["graph_hash"],
                "candidate_kind": "general_agentic",
                "workflow_certainty": "medium",
                "context_certainty": "high",
                "recommended_execution_mode": "llm_agentic",
                "disposition": "skill_candidate",
                "drafting_mode": "deterministic",
                "loop_mode": "autonomous_refiner",
                "current_round": 0,
                "terminal_state": "pending",
                "human_gate": "skipped",
                "boundary_quality": boundary_quality,
                "eval_aggregate": eval_aggregate,
                "cross_subset_stability": stability,
            },
            "nearest_skill_id": "circle-of-competence",
        }

    def test_refine_candidate_reaches_ready_for_review_when_targets_are_met(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = refine_candidate(
                candidate=self._make_candidate(
                    boundary_quality=0.80,
                    eval_aggregate=0.79,
                    stability=0.78,
                ),
                source_bundle=self.bundle,
                run_root=Path(tmp_dir),
            )

            self.assertEqual(result["candidate"]["terminal_state"], "ready_for_review")
            self.assertGreaterEqual(result["candidate"]["overall_quality"], 0.82)
            self.assertTrue((Path(tmp_dir) / "reports" / "final-decision.json").exists())

    def test_refine_candidate_returns_do_not_publish_when_no_positive_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = refine_candidate(
                candidate=self._make_candidate(
                    boundary_quality=0.40,
                    eval_aggregate=0.40,
                    stability=0.40,
                ),
                source_bundle=self.bundle,
                run_root=Path(tmp_dir),
                mutation_strategy="stalled",
            )

            self.assertEqual(result["candidate"]["terminal_state"], "do_not_publish")


if __name__ == "__main__":
    unittest.main()
