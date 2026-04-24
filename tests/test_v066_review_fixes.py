import tempfile
import unittest
from pathlib import Path

import yaml

from kiu_pipeline.contracts import build_semantic_contract
from kiu_pipeline.review import review_generated_run
from kiu_pipeline.seed import _infer_candidate_kind
from kiu_pipeline.seed import _candidate_seed_score


class V066ReviewFixTests(unittest.TestCase):
    def test_borrowed_value_contracts_reject_review_summary_and_workflow_prompts(self) -> None:
        for skill_id in [
            "historical-analogy-transfer-gate",
            "historical-case-consequence-judgment",
            "role-boundary-before-action",
            "principal-contradiction-focus",
        ]:
            contract = build_semantic_contract(candidate_id=skill_id)
            text = str(contract)
            self.assertIn("pure_character_evaluation_request", text, skill_id)
            self.assertIn("pure_viewpoint_summary_request", text, skill_id)
            self.assertIn("mechanical_workflow_template_request", text, skill_id)

    def test_case_density_score_downranks_weak_source_forms_in_seed_score(self) -> None:
        profile = {"routing_inference": {"default_candidate_kind": "general_agentic"}}
        strong_kind, strong_routing = _infer_candidate_kind(
            node={
                "id": "strong",
                "type": "skill_principle",
                "label": "货殖列传中的选择约束后果机制",
                "source_file": "史记/货殖列传.md",
                "routing_hints": {"agentic_priority": 20},
            },
            support={
                "evidence_support_count": 4,
                "extracted_evidence_support_count": 4,
                "tri_state_support_count": 2,
                "support_entity_count": 8,
            },
            profile=profile,
        )
        weak_kind, weak_routing = _infer_candidate_kind(
            node={
                "id": "weak",
                "type": "skill_principle",
                "label": "龟策列传占辞清单",
                "source_file": "史记/龟策列传.md",
                "routing_hints": {"agentic_priority": 20},
            },
            support={
                "evidence_support_count": 4,
                "extracted_evidence_support_count": 4,
                "tri_state_support_count": 2,
                "support_entity_count": 8,
            },
            profile=profile,
        )

        self.assertEqual(strong_kind, "general_agentic")
        self.assertEqual(weak_kind, "general_agentic")
        self.assertGreater(strong_routing["case_density_score"], weak_routing["case_density_score"])
        strong_score = _candidate_seed_score(
            seed_content={},
            source_skill=None,
            support={"supporting_edge_ids": [], "community_ids": []},
            routing_evidence=strong_routing,
        )
        weak_score = _candidate_seed_score(
            seed_content={},
            source_skill=None,
            support={"supporting_edge_ids": [], "community_ids": []},
            routing_evidence=weak_routing,
        )
        self.assertGreater(strong_score, weak_score)

    def test_review_flags_repeated_rationale_template_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source = root / "source"
            bundle = root / "run" / "bundle"
            reports = root / "run" / "reports"
            reports.mkdir(parents=True)
            (root / "run" / "workflow_candidates").mkdir(parents=True)
            for path in [source / "graph", source / "skills", source / "evaluation", source / "traces"]:
                path.mkdir(parents=True)
            (source / "manifest.yaml").write_text(
                yaml.safe_dump(
                    {
                        "bundle_id": "source-test",
                        "domain": "test",
                        "graph": {"graph_hash": "sha256:test"},
                        "skills": [],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            (source / "graph" / "graph.json").write_text('{"nodes": [], "edges": [], "communities": []}', encoding="utf-8")
            for path in [bundle / "graph", bundle / "skills", bundle / "evaluation", bundle / "traces"]:
                path.mkdir(parents=True)
            skills = []
            repeated = "原文呈现行动、位置、激励与后果之间的张力。"
            for skill_id in ["alpha", "beta"]:
                skill_dir = bundle / "skills" / skill_id
                skill_dir.mkdir()
                skills.append({"skill_id": skill_id, "path": f"skills/{skill_id}"})
                (skill_dir / "SKILL.md").write_text(
                    f"# {skill_id}\n\n## Identity\nskill_id: {skill_id}\n\n## Contract\ntrigger: decision\n\n## Rationale\n{repeated}\n\n## Evidence Summary\nanchor_refs: []\n\n## Relations\n[]\n\n## Usage Summary\ncase\n\n## Evaluation Summary\npass\n\n## Revision Summary\nnone\n",
                    encoding="utf-8",
                )
            (bundle / "manifest.yaml").write_text(
                yaml.safe_dump(
                    {
                        "bundle_id": "generated-test",
                        "domain": "test",
                        "graph": {"graph_hash": "sha256:test"},
                        "skills": skills,
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            (bundle / "graph" / "graph.json").write_text('{"nodes": [], "edges": [], "communities": []}', encoding="utf-8")
            (reports / "metrics.json").write_text('{"summary": {"workflow_script_candidates": 0}}', encoding="utf-8")
            (reports / "production-quality.json").write_text(
                '{"minimum_production_quality": 0.9, "average_production_quality": 0.9, "bundle_quality_grade": "good", "candidate_count": 2}',
                encoding="utf-8",
            )
            (reports / "verification-summary.json").write_text('{}', encoding="utf-8")

            report = review_generated_run(run_root=root / "run", source_bundle_path=source)

            generated = report["generated_bundle"]
            self.assertEqual(generated["rationale_template_collision"]["collision_count"], 1)
            self.assertIn("rationale_template_collision", generated["notes"])


if __name__ == "__main__":
    unittest.main()
