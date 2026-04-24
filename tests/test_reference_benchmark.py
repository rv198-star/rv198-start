import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kiu_pipeline.cangjie_protocol import PROTOCOL_ID, build_cangjie_protocol_baseline
from kiu_pipeline.reference_benchmark import benchmark_reference_pack
from kiu_pipeline.reference_benchmark import _build_scorecard
from kiu_pipeline.reference_benchmark import _load_blind_preference_summary
from kiu_pipeline.reference_benchmark import _render_markdown_report
from kiu_pipeline.reference_benchmark import _resolve_alignment_pairs


ROOT = Path(__file__).resolve().parents[1]


def _write_reference_pack(root: Path, skill_slugs: list[str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "BOOK_OVERVIEW.md").write_text("# Book Overview\n", encoding="utf-8")
    (root / "INDEX.md").write_text("# Index\n", encoding="utf-8")
    (root / "candidates").mkdir(exist_ok=True)
    (root / "rejected").mkdir(exist_ok=True)
    for slug in skill_slugs:
        skill_dir = root / slug
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "\n".join(
                [
                    "---",
                    f"name: {slug}",
                    "source_book: Test Reference Book",
                    "source_chapter: Chapter 1",
                    "---",
                    "",
                    f"# {slug}",
                    "",
                    "## R — 原文",
                    "> 引用原文片段。",
                    "",
                    "## E — 可执行步骤",
                    "1. 执行第一步。",
                    "",
                    "## B — 边界",
                    "不要在证据不足时使用。",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return root


def _write_test_prompts(skill_dir: Path, payload: dict[str, object]) -> None:
    (skill_dir / "test-prompts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_alignment_file(root: Path) -> Path:
    path = root / "alignment.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: kiu.reference-alignment/v0.1",
                "alignment_id: test-alignment",
                "pairs:",
                "  - kiu_skill_id: circle-of-competence",
                "    reference_skill_id: circle-of-competence",
                "    relationship: direct_match",
                "  - kiu_skill_id: invert-the-problem",
                "    reference_skill_id: inversion-thinking",
                "    relationship: close_match",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_generated_run_alignment_file(root: Path) -> Path:
    path = root / "generated-run-alignment.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: kiu.reference-alignment/v0.1",
                "alignment_id: generated-run-test-alignment",
                "pairs:",
                "  - kiu_skill_id: business-first-subsystem-decomposition",
                "    reference_skill_id: business-first-subsystem-decomposition",
                "    relationship: direct_match",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_competing_alignment_file(root: Path) -> Path:
    path = root / "competing-alignment.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: kiu.reference-alignment/v0.1",
                "alignment_id: competing-alignment",
                "pairs:",
                "  - kiu_skill_id: margin-of-safety-sizing",
                "    reference_skill_id: value-assessment",
                "    relationship: partial_overlap",
                "  - kiu_skill_id: value-assessment",
                "    reference_skill_id: value-assessment",
                "    relationship: direct_match",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


class ReferenceBenchmarkCliTests(unittest.TestCase):
    def test_scorecard_does_not_treat_usage_win_as_cangjie_methodology_absorption(self) -> None:
        scorecard = _build_scorecard(
            kiu_bundle={
                "validator_errors": 0,
                "validator_warnings": 0,
                "workflow_boundary": {"explicit_boundary": True},
                "provenance": {
                    "nodes": {
                        "source_file_ratio": 1.0,
                        "source_location_ratio": 1.0,
                        "extraction_kind_ratio": 1.0,
                    },
                    "edges": {
                        "source_file_ratio": 1.0,
                        "source_location_ratio": 1.0,
                        "extraction_kind_ratio": 1.0,
                        "confidence_ratio": 1.0,
                    },
                    "extraction_kind_counts": {"EXTRACTED": 8, "INFERRED": 3, "AMBIGUOUS": 2},
                },
                "graph": {"community_count": 3},
                "graph_report_present": True,
                "skill_count": 6,
            },
            generated_run={
                "workflow_boundary_preserved": True,
                "verification_gate_present": True,
                "workflow_verification_ready_ratio": 1.0,
                "minimum_production_quality": 0.92,
                "overall_score_100": 96.0,
                "usage_score_100": 98.0,
                "skill_count": 6,
                "source_tri_state_effectiveness": {"overall_ratio": 1.0},
                "pipeline_artifacts": {
                    "raw_book_no_seed_cold_start": True,
                    "book_overview_present": True,
                    "source_chunks_present": True,
                    "extraction_result_present": True,
                    "graph_present": True,
                    "verification_summary_present": True,
                    "extractor_kinds": [
                        "framework",
                        "principle",
                        "case",
                        "counter-example",
                        "term",
                    ],
                    "pipeline_mode": "raw_book_no_seed_cold_start",
                    "source_bundle_skill_count": 0,
                },
            },
            reference_pack={"skill_count": 6},
            same_scenario_usage={
                "summary": {
                    "scenario_count": 24,
                    "usage_winner": "kiu",
                    "average_usage_score_delta_100": 1.0,
                    "kiu_weighted_pass_rate": 1.0,
                    "reference_weighted_pass_rate": 1.0,
                    "failure_tag_counts": {},
                }
            },
        )

        self.assertGreater(scorecard["cangjie_core_absorbed_100"], 80.0)
        self.assertEqual(scorecard["cangjie_methodology_internal_100"], 20.0)
        self.assertEqual(scorecard["cangjie_methodology_external_blind_100"], 0.0)
        self.assertEqual(scorecard["cangjie_methodology_closure_100"], 0.0)
        self.assertFalse(scorecard["cangjie_methodology_gate"]["ready"])
        self.assertEqual(
            scorecard["cangjie_methodology_gate"]["claim"],
            "same_scenario_usage_win_only",
        )
        self.assertIn(
            "principle_depth_review_missing_or_weak",
            scorecard["cangjie_methodology_gate"]["reasons"],
        )
        self.assertIn(
            "decoy_pressure_test_missing_or_weak",
            scorecard["cangjie_methodology_gate"]["reasons"],
        )
        self.assertEqual(scorecard["final_artifact_effect"]["claim"], "usage_effect_only")
        self.assertFalse(scorecard["final_artifact_effect"]["ready"])
        self.assertGreaterEqual(
            scorecard["final_artifact_effect"]["layer1_immediate_usage_effect_100"],
            90.0,
        )
        self.assertEqual(
            scorecard["final_artifact_effect"]["layer2_knowledge_depth_effect_100"],
            20.0,
        )
        self.assertIn(
            "knowledge_depth_effect_below_80",
            scorecard["final_artifact_effect"]["reasons"],
        )

    def test_scorecard_allows_two_layer_effect_only_when_usage_and_depth_both_pass(self) -> None:
        scorecard = _build_scorecard(
            kiu_bundle={
                "validator_errors": 0,
                "validator_warnings": 0,
                "workflow_boundary": {"explicit_boundary": True},
                "provenance": {
                    "nodes": {
                        "source_file_ratio": 1.0,
                        "source_location_ratio": 1.0,
                        "extraction_kind_ratio": 1.0,
                    },
                    "edges": {
                        "source_file_ratio": 1.0,
                        "source_location_ratio": 1.0,
                        "extraction_kind_ratio": 1.0,
                        "confidence_ratio": 1.0,
                    },
                    "extraction_kind_counts": {"EXTRACTED": 8, "INFERRED": 3, "AMBIGUOUS": 2},
                },
                "graph": {"community_count": 3},
                "graph_report_present": True,
                "skill_count": 6,
            },
            generated_run={
                "workflow_boundary_preserved": True,
                "verification_gate_present": True,
                "workflow_verification_ready_ratio": 1.0,
                "minimum_production_quality": 0.92,
                "overall_score_100": 96.0,
                "usage_score_100": 98.0,
                "skill_count": 6,
                "source_tri_state_effectiveness": {"overall_ratio": 1.0},
                "pipeline_artifacts": {
                    "raw_book_no_seed_cold_start": True,
                    "book_overview_present": True,
                    "source_chunks_present": True,
                    "extraction_result_present": True,
                    "graph_present": True,
                    "verification_summary_present": True,
                    "extractor_kinds": [
                        "framework",
                        "principle",
                        "case",
                        "counter-example",
                        "term",
                    ],
                    "pipeline_mode": "raw_book_no_seed_cold_start",
                    "source_bundle_skill_count": 0,
                    "principle_depth_review_ratio": 1.0,
                    "cross_chapter_synthesis_ratio": 1.0,
                    "triple_verification_ratio": 1.0,
                    "decoy_pressure_test_ratio": 1.0,
                    "blind_preference_review_ratio": 1.0,
                },
            },
            reference_pack={"skill_count": 6},
            same_scenario_usage={
                "summary": {
                    "scenario_count": 24,
                    "usage_winner": "kiu",
                    "kiu_average_usage_score_100": 97.4,
                    "reference_average_usage_score_100": 96.4,
                    "average_usage_score_delta_100": 1.0,
                    "kiu_weighted_pass_rate": 1.0,
                    "reference_weighted_pass_rate": 1.0,
                    "failure_tag_counts": {},
                }
            },
        )

        self.assertEqual(scorecard["cangjie_methodology_internal_100"], 100.0)
        self.assertEqual(scorecard["cangjie_methodology_external_blind_100"], 100.0)
        self.assertEqual(scorecard["cangjie_methodology_closure_100"], 100.0)
        self.assertTrue(scorecard["cangjie_methodology_gate"]["ready"])
        self.assertTrue(scorecard["final_artifact_effect"]["ready"])
        self.assertEqual(
            scorecard["final_artifact_effect"]["claim"],
            "two_layer_effect_proven",
        )
        self.assertEqual(scorecard["final_artifact_effect"]["reasons"], [])


    def test_blind_preference_evidence_requires_anonymous_choices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            good_path = tmp_root / "blind-good.json"
            good_path.write_text(
                json.dumps(
                    {
                        "schema_version": "kiu.blind-preference-review/v0.1",
                        "review_id": "blind-smoke",
                        "pairs": [
                            {
                                "pair_id": "pair-1",
                                "preferred": "a",
                                "option_roles": {"a": "kiu", "b": "reference"},
                                "dimension_scores": {
                                    "usage": 1.0,
                                    "depth": 0.9,
                                    "transferability": 0.8,
                                    "anti_misuse": 0.9,
                                },
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            bad_path = tmp_root / "blind-bad.json"
            bad_path.write_text(
                json.dumps(
                    {
                        "schema_version": "kiu.blind-preference-review/v0.1",
                        "review_id": "blind-bad",
                        "pairs": [
                            {
                                "pair_id": "pair-1",
                                "preferred": "kiu",
                                "option_roles": {"a": "kiu", "b": "reference"},
                                "dimension_scores": {"usage": 1.0},
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            good = _load_blind_preference_summary(good_path)
            bad = _load_blind_preference_summary(bad_path)

        self.assertEqual(good["pass_ratio"], 1.0)
        self.assertEqual(good["pair_count"], 1)
        self.assertFalse(bad["valid"])
        self.assertIn("non_anonymous_preference_label", bad["errors"])

    def test_scorecard_reads_pressure_and_blind_evidence_artifacts(self) -> None:
        scorecard = _build_scorecard(
            kiu_bundle={
                "validator_errors": 0,
                "validator_warnings": 0,
                "workflow_boundary": {"explicit_boundary": True},
                "provenance": {
                    "nodes": {"source_file_ratio": 1.0, "source_location_ratio": 1.0, "extraction_kind_ratio": 1.0},
                    "edges": {"source_file_ratio": 1.0, "source_location_ratio": 1.0, "extraction_kind_ratio": 1.0, "confidence_ratio": 1.0},
                    "extraction_kind_counts": {"EXTRACTED": 8, "INFERRED": 3, "AMBIGUOUS": 2},
                },
                "graph": {"community_count": 3},
                "graph_report_present": True,
                "skill_count": 3,
            },
            generated_run={
                "workflow_boundary_preserved": True,
                "verification_gate_present": True,
                "workflow_verification_ready_ratio": 1.0,
                "minimum_production_quality": 0.9,
                "overall_score_100": 94.0,
                "usage_score_100": 95.0,
                "skill_count": 3,
                "source_tri_state_effectiveness": {"overall_ratio": 1.0},
                "pipeline_artifacts": {
                    "raw_book_no_seed_cold_start": True,
                    "book_overview_present": True,
                    "source_chunks_present": True,
                    "extraction_result_present": True,
                    "graph_present": True,
                    "verification_summary_present": True,
                    "extractor_kinds": ["framework", "principle", "case", "counter-example", "term"],
                    "principle_depth_review_ratio": 1.0,
                    "cross_chapter_synthesis_ratio": 1.0,
                    "triple_verification_ratio": 1.0,
                    "pressure_test_summary": {"pass_ratio": 0.9},
                    "blind_preference_summary": {"pass_ratio": 0.85},
                },
            },
            reference_pack={"skill_count": 3},
            same_scenario_usage={"summary": {"scenario_count": 24, "usage_winner": "kiu"}},
        )

        details = scorecard["details"]["cangjie_methodology_quality"]
        self.assertEqual(details["decoy_pressure_test_ratio"], 0.9)
        self.assertEqual(details["blind_preference_review_ratio"], 0.85)
        self.assertTrue(scorecard["cangjie_methodology_gate"]["ready"])

    def test_scorecard_counts_ria_tv_and_triple_verification_artifacts_without_pressure_or_blind(self) -> None:
        scorecard = _build_scorecard(
            kiu_bundle={
                "validator_errors": 0,
                "validator_warnings": 0,
                "workflow_boundary": {"explicit_boundary": True},
                "provenance": {
                    "nodes": {"source_file_ratio": 1.0, "source_location_ratio": 1.0, "extraction_kind_ratio": 1.0},
                    "edges": {"source_file_ratio": 1.0, "source_location_ratio": 1.0, "extraction_kind_ratio": 1.0, "confidence_ratio": 1.0},
                    "extraction_kind_counts": {"EXTRACTED": 8, "INFERRED": 3, "AMBIGUOUS": 2},
                },
                "graph": {"community_count": 3},
                "graph_report_present": True,
                "skill_count": 3,
            },
            generated_run={
                "workflow_boundary_preserved": True,
                "verification_gate_present": True,
                "workflow_verification_ready_ratio": 1.0,
                "minimum_production_quality": 0.9,
                "overall_score_100": 94.0,
                "usage_score_100": 95.0,
                "skill_count": 3,
                "source_tri_state_effectiveness": {"overall_ratio": 1.0},
                "pipeline_artifacts": {
                    "raw_book_no_seed_cold_start": True,
                    "book_overview_present": True,
                    "source_chunks_present": True,
                    "extraction_result_present": True,
                    "graph_present": True,
                    "verification_summary_present": True,
                    "extractor_kinds": ["framework", "principle", "case", "counter-example", "term"],
                    "ria_tv_stage_report_present": True,
                    "ria_tv_stage_status": {
                        "stage0_book_overview": True,
                        "stage1_parallel_extractors": True,
                        "stage1_5_triple_verification": True,
                        "stage2_skill_distillation": True,
                        "stage3_linking": True,
                        "stage4_pressure_test": True,
                    },
                    "triple_verification_summary": {
                        "cross_evidence_ratio": 0.9,
                        "predictive_action_ratio": 0.85,
                        "uniqueness_ratio": 0.8,
                    },
                },
            },
            reference_pack={"skill_count": 3},
            same_scenario_usage={"summary": {"scenario_count": 24, "usage_winner": "kiu"}},
        )

        details = scorecard["details"]["cangjie_methodology_quality"]
        self.assertGreaterEqual(details["principle_depth_review_ratio"], 0.8)
        self.assertGreaterEqual(details["cross_chapter_synthesis_ratio"], 0.8)
        self.assertGreaterEqual(details["triple_verification_ratio"], 0.8)
        self.assertEqual(details["decoy_pressure_test_ratio"], 0.0)
        self.assertEqual(details["blind_preference_review_ratio"], 0.0)
        self.assertGreaterEqual(scorecard["cangjie_methodology_internal_100"], 70.0)
        self.assertEqual(scorecard["cangjie_methodology_external_blind_100"], 0.0)
        self.assertEqual(scorecard["cangjie_methodology_closure_100"], 0.0)
        self.assertFalse(scorecard["cangjie_methodology_gate"]["ready"])
        matrix = scorecard["cangjie_core_baseline_matrix"]
        row_ids = {row["capability_id"] for row in matrix["rows"]}
        self.assertEqual(
            row_ids,
            {
                "ria_tv_stages",
                "five_extractors",
                "triple_verification",
                "decoy_pressure",
                "blind_preference",
                "same_source_benchmark",
                "workflow_boundary_preservation",
            },
        )
        self.assertFalse(matrix["summary"]["ready"])
        self.assertIn("decoy_pressure", matrix["summary"]["missing_capabilities"])
        self.assertIn("blind_preference", matrix["summary"]["missing_capabilities"])

    def test_markdown_report_surfaces_cangjie_methodology_gate(self) -> None:
        scorecard = {
            "kiu_foundation_retained_100": 99.0,
            "graphify_core_absorbed_100": 95.0,
            "cangjie_core_absorbed_100": 86.0,
            "cangjie_methodology_internal_100": 90.0,
            "cangjie_methodology_external_blind_100": 0.0,
            "cangjie_methodology_closure_100": 0.0,
            "cangjie_methodology_quality_100": 0.0,
            "cangjie_methodology_gate": {
                "ready": False,
                "claim": "same_scenario_usage_win_only",
                "reasons": [
                    "principle_depth_review_missing_or_weak",
                    "decoy_pressure_test_missing_or_weak",
                ],
            },
            "final_artifact_effect": {
                "ready": False,
                "claim": "internal_depth_proven_external_blind_missing",
                "layer1_immediate_usage_effect_100": 95.0,
                "layer2_knowledge_depth_effect_100": 90.0,
                "layer3_external_blind_preference_effect_100": 0.0,
                "reasons": ["external_blind_preference_below_80"],
            },
            "book_to_skill_cold_start_proven": True,
            "graph_to_skill_distillation_100": 92.0,
            "v061_distillation_gate": {"ready": True},
            "cangjie_core_baseline_matrix": {
                "schema_version": "kiu.cangjie-core-baseline-matrix/v0.1",
                "summary": {
                    "ready": False,
                    "missing_p0_count": 1,
                    "missing_capabilities": ["decoy_pressure"],
                },
                "rows": [
                    {
                        "capability_id": "decoy_pressure",
                        "status": "missing",
                        "score_ratio": 0.0,
                        "missing_reason": "decoy_pressure_missing_or_weak",
                    }
                ],
            },
        }
        markdown = _render_markdown_report(
            {
                "comparison": {
                    "scope": "same-source",
                    "output_count": {
                        "bundle_throughput_vs_reference": 1.0,
                        "generated_throughput_vs_reference": 1.0,
                    },
                    "evidence_traceability": {
                        "kiu_double_anchor_ratio": 1.0,
                        "reference_source_context_ratio": 1.0,
                    },
                    "real_usage_quality": {"kiu_usage_score_100": 98.0},
                },
                "concept_alignment": {
                    "alignment_source": "fixture",
                    "summary": {
                        "matched_pair_count": 4,
                        "kiu_average_artifact_score_100": 96.0,
                        "reference_average_artifact_score_100": 95.0,
                        "unmatched_kiu_skill_count": 0,
                        "unmatched_reference_skill_count": 0,
                    },
                },
                "same_scenario_usage": {
                    "summary": {
                        "matched_pair_count": 4,
                        "scenario_count": 24,
                        "kiu_average_usage_score_100": 97.4,
                        "reference_average_usage_score_100": 96.4,
                        "average_usage_score_delta_100": 1.0,
                        "kiu_weighted_pass_rate": 1.0,
                        "reference_weighted_pass_rate": 1.0,
                        "weighted_pass_rate_delta": 0.0,
                        "usage_winner": "kiu",
                    }
                },
                "kiu_bundle": {"skill_count": 6},
                "generated_run": {"skill_count": 6},
                "reference_pack": {"skill_count": 6},
                "scorecard": scorecard,
            }
        )

        self.assertIn("cangjie methodology internal", markdown)
        self.assertIn("cangjie external blind preference", markdown)
        self.assertIn("cangjie methodology closure", markdown)
        self.assertIn("cangjie methodology gate ready: `False`", markdown)
        self.assertIn("same_scenario_usage_win_only", markdown)
        self.assertIn("principle_depth_review_missing_or_weak", markdown)
        self.assertIn("final artifact effect claim: `internal_depth_proven_external_blind_missing`", markdown)
        self.assertIn("external_blind_preference_below_80", markdown)
        self.assertIn("Cangjie Core Baseline Matrix", markdown)
        self.assertIn("decoy_pressure", markdown)

    def test_alignment_pairs_match_generated_source_note_skill_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            alignment_path = _write_alignment_file(tmp_root)

            pairs = _resolve_alignment_pairs(
                kiu_reviews={"circle-of-competence-source-note": {"title": "circle"}},
                reference_reviews={"circle-of-competence": {"title": "circle"}},
                alignment_file=alignment_path,
            )

            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0]["kiu_skill_id"], "circle-of-competence-source-note")
            self.assertEqual(pairs[0]["reference_skill_id"], "circle-of-competence")

    def test_alignment_pairs_prefer_direct_match_over_partial_overlap_for_same_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            alignment_path = _write_competing_alignment_file(tmp_root)

            pairs = _resolve_alignment_pairs(
                kiu_reviews={
                    "margin-of-safety-sizing-source-note": {"title": "margin"},
                    "value-assessment-source-note": {"title": "value"},
                },
                reference_reviews={"value-assessment": {"title": "value"}},
                alignment_file=alignment_path,
            )

            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0]["kiu_skill_id"], "value-assessment-source-note")
            self.assertEqual(pairs[0]["reference_skill_id"], "value-assessment")
            self.assertEqual(pairs[0]["relationship"], "direct_match")

    def test_alignment_pairs_fall_back_to_partial_overlap_when_direct_match_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            alignment_path = _write_competing_alignment_file(tmp_root)

            pairs = _resolve_alignment_pairs(
                kiu_reviews={"margin-of-safety-sizing-source-note": {"title": "margin"}},
                reference_reviews={"value-assessment": {"title": "value"}},
                alignment_file=alignment_path,
            )

            self.assertEqual(len(pairs), 1)
            self.assertEqual(pairs[0]["kiu_skill_id"], "margin-of-safety-sizing-source-note")
            self.assertEqual(pairs[0]["reference_skill_id"], "value-assessment")
            self.assertEqual(pairs[0]["relationship"], "partial_overlap")

    def test_reference_benchmark_cli_emits_bundle_comparison_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            reference_root = _write_reference_pack(
                tmp_root / "reference-poor-charlies",
                ["circle-of-competence", "inversion-thinking", "value-assessment"],
            )
            alignment_path = _write_alignment_file(tmp_root)
            output_path = tmp_root / "benchmark.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_reference_pack.py"),
                    "--kiu-bundle",
                    str(ROOT / "bundles" / "poor-charlies-almanack-v0.1"),
                    "--reference-pack",
                    str(reference_root),
                    "--alignment-file",
                    str(alignment_path),
                    "--comparison-scope",
                    "same-source",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["comparison"]["scope"], "same-source")
            self.assertEqual(payload["kiu_bundle"]["skill_count"], 5)
            self.assertEqual(payload["reference_pack"]["skill_count"], 3)
            self.assertGreater(
                payload["comparison"]["output_count"]["bundle_throughput_vs_reference"],
                1.0,
            )
            self.assertEqual(
                payload["comparison"]["evidence_traceability"]["kiu_double_anchor_ratio"],
                1.0,
            )
            self.assertTrue(
                payload["comparison"]["workflow_vs_agentic_boundary"]["kiu_explicit_boundary"]
            )
            self.assertEqual(payload["concept_alignment"]["summary"]["matched_pair_count"], 2)
            self.assertIn("unmatched_kiu_skill_count", payload["concept_alignment"]["summary"])
            self.assertIn(
                "unmatched_reference_skill_count",
                payload["concept_alignment"]["summary"],
            )
            self.assertGreater(
                payload["concept_alignment"]["summary"]["kiu_average_artifact_score_100"],
                0.0,
            )
            first_pair = payload["concept_alignment"]["matched_pairs"][0]
            self.assertIn("kiu_review", first_pair)
            self.assertIn("reference_review", first_pair)
            self.assertIn("overall_artifact_score_100", first_pair["kiu_review"])
            self.assertIn("overall_artifact_score_100", first_pair["reference_review"])
            self.assertGreaterEqual(first_pair["kiu_review"]["actionability_100"], 80.0)
            self.assertIn("kiu_foundation_retained_100", payload["scorecard"])
            self.assertIn("graphify_core_absorbed_100", payload["scorecard"])
            self.assertIn("cangjie_core_absorbed_100", payload["scorecard"])
            self.assertIn("cangjie_methodology_internal_100", payload["scorecard"])
            self.assertIn("cangjie_methodology_external_blind_100", payload["scorecard"])
            self.assertIn("cangjie_methodology_closure_100", payload["scorecard"])
            self.assertIn("cangjie_methodology_gate", payload["scorecard"])
            cli_summary = json.loads(result.stdout)["summary"]
            self.assertIn("cangjie_methodology_internal_100", cli_summary)
            self.assertIn("cangjie_methodology_external_blind_100", cli_summary)
            self.assertIn("cangjie_methodology_closure_100", cli_summary)
            self.assertIn("cangjie_methodology_gate_ready", cli_summary)
            self.assertIn("cangjie_methodology_claim", cli_summary)
            self.assertIn("final_artifact_effect_claim", cli_summary)
            self.assertIn("final_artifact_effect_ready", cli_summary)
            self.assertIn("compatibility_regression_risk", cli_summary)
            self.assertIn("cangjie_core_baseline_matrix_ready", cli_summary)
            self.assertIn("cangjie_core_missing_capabilities", cli_summary)
            markdown_path = output_path.with_suffix(".md")
            self.assertTrue(markdown_path.exists())
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Unmatched KiU skills", markdown)
            self.assertIn("Unmatched reference skills", markdown)

    def test_cangjie_protocol_baseline_emits_benchmark_only_reference_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_dir = tmp_root / "book"
            source_dir.mkdir()
            (source_dir / "001.md").write_text(
                "\n".join(
                    [
                        "# 第一章",
                        "",
                        "君臣之际，利害相持，是以小失其本，卒有大祸。",
                        "不可只见一时之功，而忘后日之乱。",
                    ]
                ),
                encoding="utf-8",
            )
            (source_dir / "002.md").write_text(
                "\n".join(
                    [
                        "# 第二章",
                        "",
                        "王侯用兵，赏罚不明，则臣下争功而国势败。",
                    ]
                ),
                encoding="utf-8",
            )
            output_root = tmp_root / "cangjie-protocol"

            summary = build_cangjie_protocol_baseline(
                input_path=source_dir,
                output_root=output_root,
                book_title="测试史书",
                author="测试作者",
                source_id="test-history",
            )

            self.assertEqual(summary["reference_protocol"], PROTOCOL_ID)
            self.assertFalse(summary["official_cangjie_run"])
            self.assertGreaterEqual(summary["skill_count"], 1)
            metadata = json.loads((output_root / "metadata.json").read_text(encoding="utf-8"))
            self.assertTrue(metadata["benchmark_only"])
            self.assertTrue(
                metadata["external_reference_boundary"]["uses_original_source_material"]
            )
            self.assertFalse(
                metadata["external_reference_boundary"][
                    "uses_external_final_skill_pack_as_input"
                ]
            )
            self.assertTrue((output_root / "BOOK_OVERVIEW.md").exists())
            self.assertTrue((output_root / "INDEX.md").exists())
            self.assertTrue((output_root / "candidates" / "framework.md").exists())
            for skill_id in summary["skill_ids"]:
                self.assertTrue((output_root / skill_id / "SKILL.md").exists())
                self.assertTrue((output_root / skill_id / "test-prompts.json").exists())

    def test_cangjie_protocol_baseline_emits_release_threshold_pressure_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            source_dir = tmp_root / "source"
            source_dir.mkdir()
            (source_dir / "001.md").write_text(
                "\n".join(
                    [
                        "# 第一章",
                        "",
                        "王侯用兵，利害相生。短利若失信，则后有祸败。",
                        "臣下有功而越分，君臣边界不明，则国势乱。",
                    ]
                ),
                encoding="utf-8",
            )
            (source_dir / "002.md").write_text(
                "\n".join(
                    [
                        "# 第二章",
                        "",
                        "赏罚不明，则臣下争功。不可只看一时胜负，须看后患。",
                        "权责未定而急行其事，虽有小利，终损长期秩序。",
                    ]
                ),
                encoding="utf-8",
            )
            output_root = tmp_root / "cangjie-protocol"

            summary = build_cangjie_protocol_baseline(
                input_path=source_dir,
                output_root=output_root,
                book_title="测试史书",
                author="测试作者",
                source_id="test-history",
            )

            total_cases = 0
            boundary_cases = 0
            for skill_id in summary["skill_ids"]:
                prompt_doc = json.loads(
                    (output_root / skill_id / "test-prompts.json").read_text(encoding="utf-8")
                )
                cases = prompt_doc["test_cases"]
                self.assertGreaterEqual(len(cases), 12, skill_id)
                total_cases += len(cases)
                boundary_cases += sum(
                    1
                    for case in cases
                    if case.get("type") in {"should_not_trigger", "edge_case"}
                )

            self.assertGreaterEqual(total_cases, 24)
            self.assertGreaterEqual(boundary_cases / total_cases, 0.4)

    def test_reference_benchmark_preserves_cangjie_protocol_boundary_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            reference_root = _write_reference_pack(
                tmp_root / "reference-pack",
                ["circle-of-competence"],
            )
            (reference_root / "metadata.json").write_text(
                json.dumps(
                    {
                        "reference_protocol": PROTOCOL_ID,
                        "official_cangjie_run": False,
                        "benchmark_only": True,
                        "external_reference_boundary": {
                            "uses_original_source_material": True,
                            "uses_external_final_skill_pack_as_input": False,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            report = benchmark_reference_pack(
                kiu_bundle_path=ROOT / "bundles" / "poor-charlies-almanack-v0.1",
                reference_pack_path=reference_root,
                comparison_scope="same-source",
            )

            self.assertEqual(report["reference_pack"]["reference_protocol"], PROTOCOL_ID)
            self.assertFalse(report["reference_pack"]["official_cangjie_run"])
            self.assertTrue(report["reference_pack"]["benchmark_only"])
            self.assertFalse(
                report["reference_pack"]["external_reference_boundary"][
                    "uses_external_final_skill_pack_as_input"
                ]
            )

    def test_reference_benchmark_cli_includes_generated_run_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            output_root = tmp_root / "artifacts"
            reference_root = _write_reference_pack(
                tmp_root / "reference-engineering",
                ["problem-first-analysis", "business-interface-analysis", "constraint-checklist"],
            )

            pipeline = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_book_pipeline.py"),
                    "--input",
                    str(ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--run-id",
                    "reference-benchmark-smoke",
                    "--output-root",
                    str(output_root),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(pipeline.returncode, 0, pipeline.stdout + pipeline.stderr)
            pipeline_payload = json.loads(pipeline.stdout)

            benchmark_path = tmp_root / "generated-benchmark.json"
            benchmark = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_reference_pack.py"),
                    "--kiu-bundle",
                    pipeline_payload["source_bundle_root"],
                    "--run-root",
                    pipeline_payload["run_root"],
                    "--reference-pack",
                    str(reference_root),
                    "--comparison-scope",
                    "structure-only",
                    "--output",
                    str(benchmark_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(benchmark.returncode, 0, benchmark.stdout + benchmark.stderr)

            payload = json.loads(benchmark_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(payload["generated_run"]["skill_count"], 1)
            self.assertTrue(payload["generated_run"]["raw_book_no_seed_cold_start"])
            self.assertEqual(payload["generated_run"]["pipeline_mode"], "raw_book_no_seed_cold_start")
            self.assertTrue(payload["scorecard"]["book_to_skill_cold_start_proven"])
            self.assertEqual(payload["scorecard"]["book_to_skill_cold_start_proven_100"], 100.0)
            self.assertEqual(
                payload["scorecard"]["details"]["cangjie_core_absorbed"]["cold_start_proof_ratio"],
                1.0,
            )
            self.assertEqual(
                payload["scorecard"]["details"]["cangjie_core_absorbed"]["pipeline_mode"],
                "raw_book_no_seed_cold_start",
            )
            self.assertGreaterEqual(
                payload["generated_run"]["workflow_candidate_count"],
                2,
            )
            self.assertTrue(
                payload["comparison"]["workflow_vs_agentic_boundary"]["kiu_boundary_preserved"]
            )
            self.assertTrue(payload["generated_run"]["verification_gate_present"])
            self.assertGreater(
                payload["comparison"]["workflow_vs_agentic_boundary"][
                    "kiu_workflow_verification_ready_ratio"
                ],
                0.0,
            )
            self.assertGreater(
                payload["comparison"]["real_usage_quality"]["kiu_usage_score_100"],
                0.0,
            )
            self.assertGreater(
                payload["scorecard"]["details"]["cangjie_core_absorbed"]["pipeline_stage_presence_ratio"],
                0.0,
            )
            self.assertGreater(
                payload["scorecard"]["details"]["graphify_core_absorbed"]["tri_state_effectiveness_ratio"],
                0.0,
            )
            self.assertGreater(
                payload["generated_run"]["source_tri_state_effectiveness"]["candidate_coverage_ratio"],
                0.5,
            )
            self.assertGreater(
                payload["comparison"]["output_count"]["generated_throughput_vs_reference"],
                0.0,
            )

    def test_reference_benchmark_marks_source_bundle_regeneration_as_not_cold_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            output_root = tmp_root / "artifacts"
            reference_root = _write_reference_pack(
                tmp_root / "reference-engineering",
                ["postmortem-blameless", "blast-radius-check"],
            )

            build = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_candidates.py"),
                    "--source-bundle",
                    str(ROOT / "bundles" / "engineering-postmortem-v0.1"),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "source-bundle-regeneration-benchmark",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            build_payload = json.loads(build.stdout)

            benchmark_path = tmp_root / "source-bundle-benchmark.json"
            benchmark = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_reference_pack.py"),
                    "--kiu-bundle",
                    str(ROOT / "bundles" / "engineering-postmortem-v0.1"),
                    "--run-root",
                    build_payload["run_root"],
                    "--reference-pack",
                    str(reference_root),
                    "--comparison-scope",
                    "structure-only",
                    "--output",
                    str(benchmark_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(benchmark.returncode, 0, benchmark.stdout + benchmark.stderr)

            payload = json.loads(benchmark_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["generated_run"]["raw_book_no_seed_cold_start"])
            self.assertEqual(payload["generated_run"]["pipeline_mode"], "source_bundle_regeneration")
            self.assertFalse(payload["scorecard"]["book_to_skill_cold_start_proven"])
            self.assertEqual(payload["scorecard"]["book_to_skill_cold_start_proven_100"], 0.0)
            self.assertEqual(
                payload["scorecard"]["details"]["cangjie_core_absorbed"]["cold_start_proof_ratio"],
                0.0,
            )
            self.assertGreater(
                payload["scorecard"]["details"]["cangjie_core_absorbed"]["source_bundle_skill_count"],
                0,
            )

    def test_reference_benchmark_cli_emits_same_scenario_usage_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            reference_root = _write_reference_pack(
                tmp_root / "reference-poor-charlies",
                ["circle-of-competence", "inversion-thinking"],
            )
            _write_test_prompts(
                reference_root / "circle-of-competence",
                {
                    "skill": "circle-of-competence",
                    "version": "0.1.0",
                    "test_cases": [
                        {
                            "id": "should-trigger-01",
                            "type": "should_trigger",
                            "prompt": "有个朋友拉我一起投资他的餐饮连锁项目，我之前从来没做过餐饮，但我觉得应该差不多能搞明白。",
                            "expected_behavior": "应激活 circle-of-competence，帮助用户测试自己是否真的理解这门生意，而不是靠模糊自信下注。",
                            "notes": "真实投资判断，不是概念问答。",
                        },
                        {
                            "id": "should-not-trigger-01",
                            "type": "should_not_trigger",
                            "prompt": "能力圈是什么概念？芒格和巴菲特怎么定义它？",
                            "expected_behavior": "不应激活本 skill，因为用户只是在问概念定义，不是在做真实投资判断。",
                            "notes": "关键词命中但属于知识查询。",
                        },
                        {
                            "id": "edge-01",
                            "type": "edge_case",
                            "prompt": "我做了5年产品经理，现在有机会去一个完全不同行业做产品，我想试试看，但怕自己搞不定。",
                            "expected_behavior": "可以激活但应保留边界判断，区分哪些通用能力可迁移，哪些行业知识仍在圈外。",
                            "notes": "部分圈内，部分圈外。",
                        },
                    ],
                    "minimum_pass_rate": 0.8,
                },
            )
            _write_test_prompts(
                reference_root / "inversion-thinking",
                {
                    "skill": "inversion-thinking",
                    "version": "0.1.0",
                    "test_cases": [
                        {
                            "id": "should-trigger-01",
                            "type": "should_trigger",
                            "prompt": "我们只看市场机会，帮我反过来想想这个产品发布会怎么彻底失败。",
                            "expected_behavior": "应激活 inversion-thinking，引导用户从失败路径出发列出致命风险。",
                            "notes": "典型逆向思考触发场景。",
                        },
                        {
                            "id": "should-not-trigger-01",
                            "type": "should_not_trigger",
                            "prompt": "逆向思维是什么意思？给我讲几个历史故事。",
                            "expected_behavior": "不应激活本 skill，因为这是概念解释，不是正在做风险规避式决策。",
                            "notes": "知识查询，不是方法应用。",
                        },
                    ],
                    "minimum_pass_rate": 0.8,
                },
            )
            alignment_path = _write_alignment_file(tmp_root)
            output_path = tmp_root / "benchmark-same-scenario.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_reference_pack.py"),
                    "--kiu-bundle",
                    str(ROOT / "bundles" / "poor-charlies-almanack-v0.1"),
                    "--reference-pack",
                    str(reference_root),
                    "--alignment-file",
                    str(alignment_path),
                    "--comparison-scope",
                    "same-source",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

            self.assertIn("same_scenario_usage", payload)
            self.assertEqual(payload["same_scenario_usage"]["summary"]["matched_pair_count"], 2)
            self.assertEqual(payload["same_scenario_usage"]["summary"]["scenario_count"], 5)
            self.assertGreater(
                payload["same_scenario_usage"]["summary"]["kiu_average_usage_score_100"],
                0.0,
            )
            self.assertGreater(
                payload["same_scenario_usage"]["summary"]["reference_average_usage_score_100"],
                0.0,
            )
            self.assertGreater(
                payload["comparison"]["real_usage_quality"]["reference_same_scenario_usage_score_100"],
                0.0,
            )
            first_pair = payload["same_scenario_usage"]["matched_pairs"][0]
            self.assertIn("kiu_usage_review", first_pair)
            self.assertIn("reference_usage_review", first_pair)
            self.assertEqual(first_pair["scenario_count"], len(first_pair["cases"]))
            self.assertIn("minimum_pass_rate", first_pair)
            first_case = first_pair["cases"][0]
            self.assertIn("case_id", first_case)
            self.assertIn("type", first_case)
            self.assertIn("kiu_review", first_case)
            self.assertIn("reference_review", first_case)
            self.assertIn("overall_score_100", first_case["kiu_review"])
            self.assertIn("verdict", first_case["reference_review"])
            self.assertIn("failure_analysis", first_case["kiu_review"])
            self.assertIn("tags", first_case["kiu_review"]["failure_analysis"])
            self.assertIn("severity", first_case["kiu_review"]["failure_analysis"])
            self.assertIn("repair_targets", first_case["kiu_review"]["failure_analysis"])
            self.assertIn("repair_owners", first_case["kiu_review"]["failure_analysis"])
            self.assertIn("primary_gap", first_case["kiu_review"]["failure_analysis"])
            self.assertIn("failure_tag_counts", first_pair["kiu_usage_review"])
            self.assertIn("top_failure_modes", first_pair["kiu_usage_review"])
            self.assertIn("repair_owner_counts", first_pair["kiu_usage_review"])
            self.assertIn("failure_tag_counts", payload["same_scenario_usage"]["summary"])
            self.assertIn("top_failure_modes", payload["same_scenario_usage"]["summary"])
            self.assertIn("repair_owner_counts", payload["same_scenario_usage"]["summary"])
            self.assertIn("weighted_pass_rate_delta", payload["same_scenario_usage"]["summary"])
            self.assertIn("usage_winner", payload["same_scenario_usage"]["summary"])
            self.assertIn(
                "same_scenario_weighted_pass_rate_delta",
                payload["comparison"]["real_usage_quality"],
            )
            markdown = output_path.with_suffix(".md").read_text(encoding="utf-8")
            self.assertIn("Top failure modes", markdown)
            self.assertIn("Repair targets", markdown)
            self.assertIn("Upstream owners", markdown)
            self.assertIn("Weighted pass-rate delta", markdown)
            self.assertIn("Usage winner", markdown)

    def test_reference_benchmark_cli_uses_generated_bundle_for_concept_alignment_when_run_root_present(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            output_root = tmp_root / "artifacts"
            reference_root = _write_reference_pack(
                tmp_root / "reference-generated-run",
                ["business-first-subsystem-decomposition"],
            )
            _write_test_prompts(
                reference_root / "business-first-subsystem-decomposition",
                {
                    "skill": "business-first-subsystem-decomposition",
                    "version": "0.1.0",
                    "test_cases": [
                        {
                            "id": "should-trigger-01",
                            "type": "should_trigger",
                            "prompt": "这个需求讨论总是在按前端、后端、数据库拆，但业务职责边界一直说不清。",
                            "expected_behavior": "应激活 business-first-subsystem-decomposition，把系统切分依据拉回业务职责和责任边界。",
                            "notes": "真实需求拆分场景。",
                        }
                    ],
                    "minimum_pass_rate": 0.8,
                },
            )
            alignment_path = _write_generated_run_alignment_file(tmp_root)

            pipeline = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_book_pipeline.py"),
                    "--input",
                    str(ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--run-id",
                    "generated-alignment-smoke",
                    "--output-root",
                    str(output_root),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(pipeline.returncode, 0, pipeline.stdout + pipeline.stderr)
            pipeline_payload = json.loads(pipeline.stdout)

            output_path = tmp_root / "generated-alignment-benchmark.json"
            benchmark = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_reference_pack.py"),
                    "--kiu-bundle",
                    pipeline_payload["source_bundle_root"],
                    "--run-root",
                    pipeline_payload["run_root"],
                    "--reference-pack",
                    str(reference_root),
                    "--alignment-file",
                    str(alignment_path),
                    "--comparison-scope",
                    "same-source",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(benchmark.returncode, 0, benchmark.stdout + benchmark.stderr)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["concept_alignment"]["summary"]["matched_pair_count"], 1)
            self.assertEqual(payload["same_scenario_usage"]["summary"]["matched_pair_count"], 1)
            self.assertEqual(payload["same_scenario_usage"]["summary"]["scenario_count"], 1)

    def test_reference_benchmark_prefers_generated_value_parent_over_margin_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            output_root = tmp_root / "artifacts"
            reference_root = _write_reference_pack(
                tmp_root / "reference-value-assessment",
                ["value-assessment"],
            )
            _write_test_prompts(
                reference_root / "value-assessment",
                {
                    "skill": "value-assessment",
                    "version": "0.1.0",
                    "test_cases": [
                        {
                            "id": "should-trigger-01",
                            "type": "should_trigger",
                            "prompt": "我在考虑要不要买一只消费股，市盈率25倍不算便宜，但品牌很强，这个价格合理吗？安全边际够不够？",
                            "expected_behavior": "应优先激活 value-assessment，先建立价值锚点并判断当前价格相对价值是低估、公允还是高估，再决定是否交给 sizing。",
                            "notes": "价格与价值判断优先于 sizing 的场景。",
                        }
                    ],
                    "minimum_pass_rate": 0.8,
                },
            )

            generated = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_candidates.py"),
                    "--source-bundle",
                    str(ROOT / "bundles" / "poor-charlies-almanack-v0.1"),
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    "value-parent-alignment",
                    "--drafting-mode",
                    "deterministic",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            generated_payload = json.loads(generated.stdout)

            output_path = tmp_root / "value-parent-benchmark.json"
            benchmark = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "benchmark_reference_pack.py"),
                    "--kiu-bundle",
                    str(ROOT / "bundles" / "poor-charlies-almanack-v0.1"),
                    "--run-root",
                    generated_payload["run_root"],
                    "--reference-pack",
                    str(reference_root),
                    "--alignment-file",
                    str(ROOT / "benchmarks" / "alignments" / "poor-charlies-vs-cangjie.yaml"),
                    "--comparison-scope",
                    "same-source",
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(benchmark.returncode, 0, benchmark.stdout + benchmark.stderr)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            matched_pair = next(
                pair
                for pair in payload["concept_alignment"]["matched_pairs"]
                if pair["reference_skill_id"] == "value-assessment"
            )

            self.assertEqual(matched_pair["kiu_skill_id"], "value-assessment-source-note")
            self.assertEqual(matched_pair["relationship"], "direct_match")
            self.assertGreaterEqual(
                payload["scorecard"]["graph_to_skill_distillation_100"],
                90.0,
            )
            self.assertTrue(
                payload["scorecard"]["v061_distillation_gate"]["ready"],
                payload["scorecard"]["v061_distillation_gate"],
            )
            self.assertGreaterEqual(
                payload["generated_run"]["graph_to_skill_distillation"]["inferred_trigger_expansion_ratio"],
                1.0,
            )
            self.assertGreaterEqual(
                payload["generated_run"]["graph_to_skill_distillation"]["ambiguous_boundary_probe_ratio"],
                1.0,
            )


if __name__ == "__main__":
    unittest.main()
