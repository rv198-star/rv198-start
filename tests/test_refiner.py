import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.baseline import build_candidate_baseline
from kiu_pipeline.load import load_source_bundle
from kiu_pipeline.mutate import mutate_candidate
from kiu_pipeline.refiner import refine_candidate
from kiu_pipeline.refiner.providers import MockLLMProvider
from kiu_pipeline.normalize import normalize_graph
from kiu_pipeline.quality import assess_candidate_artifact, assess_candidate_output
from kiu_pipeline.render import load_generated_candidates, render_generated_run
from kiu_pipeline.reports import write_final_decision, write_round_report
from kiu_pipeline.scoring import decide_terminal_state, score_candidate
from kiu_pipeline.seed import derive_candidate_metadata, mine_candidate_seeds


class RefinerConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"

    def test_load_source_bundle_reads_refinement_scheduler_profile(self) -> None:
        bundle = load_source_bundle(self.bundle_path)
        refiner = bundle.profile["refinement_scheduler"]

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
                "refinement_scheduler": {"enabled_by_default": True},
            },
        )

        self.assertEqual(metadata["loop_mode"], "refinement_scheduler")
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

    def test_decide_terminal_state_does_not_ready_when_production_quality_below_gate(self) -> None:
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
                    "artifact_quality": 0.74,
                    "production_quality": 0.78,
                },
            },
            scorecard={
                "overall_quality": 0.84,
                "boundary_quality": 0.87,
                "delta_vs_nearest": 0.05,
                "delta_vs_bundle": 0.05,
                "net_positive_value": 0.05,
                "artifact_quality": 0.58,
                "production_quality": 0.69,
            },
            history=[{"overall_quality": 0.81}, {"overall_quality": 0.84}],
            structural_valid=True,
        )

        self.assertEqual(decision["terminal_state"], "pending")
        self.assertEqual(decision["reason"], "content_quality_below_release_bar")

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
                "loop_mode": "refinement_scheduler",
                "current_round": 0,
                "terminal_state": "pending",
                "human_gate": "skipped",
                "boundary_quality": boundary_quality,
                "eval_aggregate": eval_aggregate,
                "cross_subset_stability": stability,
            },
            "nearest_skill_id": "circle-of-competence",
        }

    def _extract_section(self, markdown: str, section_name: str) -> str:
        pattern = rf"## {re.escape(section_name)}\n(.*?)(?:\n## |\Z)"
        match = re.search(pattern, markdown, re.DOTALL)
        self.assertIsNotNone(match)
        return match.group(1).strip()

    def _build_generated_candidate(
        self,
        tmp_dir: str,
        *,
        drafting_mode: str,
    ) -> tuple[Path, dict, object]:
        bundle = deepcopy(self.bundle)
        config = bundle.profile["refinement_scheduler"]
        config["min_rounds"] = 1
        config["max_rounds"] = 1
        config["targets"] = {
            "overall_quality": 0.0,
            "boundary_quality": 0.0,
            "min_positive_delta": -1.0,
        }

        graph = normalize_graph(bundle.graph_doc)
        seeds = mine_candidate_seeds(
            bundle,
            graph,
            drafting_mode=drafting_mode,
        )
        run_root = render_generated_run(
            source_bundle=bundle,
            seeds=seeds,
            output_root=Path(tmp_dir),
            run_id="llm-drafting",
        )
        candidates = load_generated_candidates(run_root / "bundle")
        candidate = next(
            item for item in candidates if item["candidate"]["candidate_id"] == "circle-of-competence"
        )
        return run_root, candidate, bundle

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

    def test_refine_candidate_llm_assisted_updates_rationale_and_records_prompt_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_root, candidate, bundle = self._build_generated_candidate(
                tmp_dir,
                drafting_mode="llm-assisted",
            )
            provider = MockLLMProvider(
                responses=[
                    (
                        "Circle discipline only works when the refusal threshold is explicit and tied to actual decision size. "
                        "The draft should force a `study_more` or `decline` verdict when the user cannot connect product familiarity, "
                        "industry structure, and downside path into one coherent model.[^anchor:circle-source-note] "
                        "That density matters because the canonical dotcom refusal trace shows that vague interest is not actionable understanding, "
                        "and the evaluator should preserve that refusal stance even when social proof or narrative momentum makes action feel urgent.[^trace:canonical/dotcom-refusal.yaml]"
                    )
                ]
            )

            result = refine_candidate(
                candidate=candidate,
                source_bundle=bundle,
                run_root=run_root,
                llm_provider=provider,
                llm_budget_tokens=4000,
            )

            rationale = self._extract_section(result["skill_markdown"], "Rationale")
            self.assertIn("refusal threshold is explicit", rationale)
            self.assertIn("[^anchor:circle-source-note]", rationale)

            round_report = json.loads(
                (run_root / "reports" / "rounds" / "circle-of-competence-round-01.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(round_report["llm_drafting"]["provider"], "mock")
            self.assertEqual(round_report["llm_drafting"]["field"], "Rationale")
            self.assertEqual(round_report["llm_rejections"], [])

    def test_refine_candidate_records_llm_rejection_when_precheck_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_root, candidate, bundle = self._build_generated_candidate(
                tmp_dir,
                drafting_mode="llm-assisted",
            )
            original_rationale = self._extract_section(candidate["skill_markdown"], "Rationale")
            provider = MockLLMProvider(responses=["Too short to survive validation."])

            result = refine_candidate(
                candidate=candidate,
                source_bundle=bundle,
                run_root=run_root,
                llm_provider=provider,
                llm_budget_tokens=4000,
            )

            rationale = self._extract_section(result["skill_markdown"], "Rationale")
            self.assertEqual(rationale, original_rationale)

            round_report = json.loads(
                (run_root / "reports" / "rounds" / "circle-of-competence-round-01.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(round_report["llm_rejections"])
            self.assertTrue(
                any(
                    "rationale_below_density_threshold" in rejection
                    for rejection in round_report["llm_rejections"]
                )
            )


class ArtifactQualityAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_source_bundle(ROOT / "bundles" / "poor-charlies-almanack-v0.1")

    def test_assess_candidate_artifact_flags_placeholder_candidate_as_poor(self) -> None:
        candidate = {
            "skill_markdown": (
                "# Synthetic Placeholder\n\n"
                "## Identity\n"
                "```yaml\n"
                "skill_id: synthetic-placeholder\n"
                "title: Synthetic Placeholder\n"
                "status: under_evaluation\n"
                "bundle_version: 0.2.0\n"
                "skill_revision: 1\n"
                "```\n\n"
                "## Contract\n"
                "```yaml\n"
                "trigger:\n"
                "  patterns:\n"
                "  - candidate_seed::n_synthetic\n"
                "  exclusions: []\n"
                "intake:\n"
                "  required:\n"
                "  - name: scenario\n"
                "    type: structured\n"
                "    description: Scenario data required to review this candidate.\n"
                "judgment_schema:\n"
                "  output:\n"
                "    type: structured\n"
                "    schema:\n"
                "      verdict: enum[pending_review]\n"
                "  reasoning_chain_required: true\n"
                "boundary:\n"
                "  fails_when:\n"
                "  - evidence_is_too_sparse_for_candidate_review\n"
                "  do_not_fire_when:\n"
                "  - candidate_has_not_been_reviewed_by_human\n"
                "```\n\n"
                "## Rationale\n"
                "This candidate was seeded from the graph snapshot and still needs human review.\n\n"
                "## Evidence Summary\n"
                "The current draft is anchored to the released graph snapshot and awaits evidence enrichment.\n\n"
                "## Relations\n"
                "```yaml\n"
                "depends_on: []\n"
                "delegates_to: []\n"
                "constrained_by: []\n"
                "complements: []\n"
                "contradicts: []\n"
                "```\n\n"
                "## Usage Summary\n"
                "Current trace attachments: 0.\n\n"
                "Representative cases are still pending curation.\n\n"
                "## Evaluation Summary\n"
                "This candidate was prefilled by the deterministic pipeline and remains under evaluation.\n\n"
                "## Revision Summary\n"
                "Revision 1 is the initial pipeline seed.\n"
            ),
            "anchors": {
                "graph_anchor_sets": [{"anchor_id": "synthetic-support", "node_ids": ["n_synthetic"]}],
                "source_anchor_sets": [
                    {
                        "anchor_id": "synthetic-source",
                        "kind": "source_excerpt",
                        "path": "../../sources/demo.md",
                        "line_start": 1,
                        "line_end": 2,
                        "snippet": "placeholder snippet",
                    }
                ],
            },
            "eval_summary": {
                "skill_id": "synthetic-placeholder",
                "bundle_version": "0.2.0",
                "skill_revision": 1,
                "status": "under_evaluation",
                "kiu_test": {
                    "trigger_test": "pending",
                    "fire_test": "pending",
                    "boundary_test": "pending",
                },
                "subsets": {
                    "real_decisions": {"cases": [], "passed": 0, "total": 0, "threshold": 0.0, "status": "pending"},
                    "synthetic_adversarial": {"cases": [], "passed": 0, "total": 0, "threshold": 0.0, "status": "pending"},
                    "out_of_distribution": {"cases": [], "passed": 0, "total": 0, "threshold": 0.0, "status": "pending"},
                },
                "key_failure_modes": [],
            },
            "revisions": {
                "skill_id": "synthetic-placeholder",
                "bundle_version": "0.2.0",
                "current_revision": 1,
                "history": [
                    {
                        "revision": 1,
                        "date": "2026-04-22",
                        "summary": "Initial placeholder seed.",
                        "graph_hash": "sha256:test",
                        "effective_status": "under_evaluation",
                        "evidence_changes": ["Initial placeholder seed."],
                    }
                ],
                "open_gaps": ["Everything important is still missing."],
            },
            "candidate": {
                "candidate_id": "synthetic-placeholder",
                "drafting_mode": "deterministic",
            },
        }

        assessment = assess_candidate_artifact(candidate=candidate, profile=self.bundle.profile)

        self.assertLess(assessment["artifact_quality"], 0.62)
        self.assertEqual(assessment["quality_grade"], "poor")
        self.assertTrue(
            any("placeholder_contract" == blocker for blocker in assessment["blockers"]),
            assessment,
        )

    def test_assess_candidate_output_prefers_refined_candidate_scorecard_when_present(self) -> None:
        candidate = {
            "skill_markdown": "# Demo\n\n## Contract\n```yaml\ntrigger: {patterns: [real_trigger], exclusions: []}\nintake: {required: [{name: a}, {name: b}, {name: c}]}\njudgment_schema: {output: {schema: {verdict: 'enum[yes,no]'}}}\nboundary: {fails_when: [x], do_not_fire_when: [y]}\n```\n\n## Rationale\n足够长的理由文本，并且带一个锚点引用。[^anchor:demo]\n\n## Evidence Summary\n证据摘要也带锚点。[^anchor:demo]\n\n## Relations\n```yaml\ndepends_on: []\ndelegates_to: []\nconstrained_by: []\ncomplements: []\ncontradicts: []\n```\n\n## Usage Summary\nCurrent trace attachments: 2.\n\n- note\n\nRepresentative cases:\n- `traces/canonical/demo-a.yaml`\n- `traces/canonical/demo-b.yaml`\n\n## Evaluation Summary\nok\n\n## Revision Summary\nok\n",
            "anchors": {
                "graph_anchor_sets": [{"anchor_id": "g1", "node_ids": ["n1"]}],
                "source_anchor_sets": [{"anchor_id": "s1", "path": "../../sources/demo.md"}],
            },
            "eval_summary": {
                "kiu_test": {
                    "trigger_test": "pending",
                    "fire_test": "pending",
                    "boundary_test": "pending",
                },
                "subsets": {
                    "real_decisions": {"cases": ["a"], "passed": 0, "total": 1, "threshold": 0.5, "status": "pending"},
                    "synthetic_adversarial": {"cases": ["b"], "passed": 0, "total": 1, "threshold": 0.5, "status": "pending"},
                    "out_of_distribution": {"cases": ["c"], "passed": 0, "total": 1, "threshold": 1.0, "status": "pending"},
                },
                "key_failure_modes": ["demo"],
            },
            "revisions": {"history": [{"revision": 1}], "open_gaps": ["demo"]},
            "candidate": {
                "candidate_id": "demo",
                "overall_quality": 0.91,
                "boundary_quality": 0.92,
                "eval_aggregate": 0.9,
                "cross_subset_stability": 0.89,
            },
        }

        assessment = assess_candidate_output(candidate=candidate, profile=self.bundle.profile)

        self.assertEqual(assessment["loop_overall_quality"], 0.91)

if __name__ == "__main__":
    unittest.main()
