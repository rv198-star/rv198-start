from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from kiu_pipeline.models import CandidateSeed, SourceBundle
from kiu_pipeline.render import render_generated_run, should_publish_skill_seed


class GenerationHygieneTests(unittest.TestCase):
    def test_chapter_title_seed_is_not_publishable_as_skill(self) -> None:
        seed = _seed(
            candidate_id="为争取千百万群众进入抗日民族统一战线而斗争",
            routing_evidence={
                "agentic_priority": 0,
                "matched_keyword_count": 1,
                "case_density_score": 0.5,
            },
            primary_node_id=None,
        )

        decision = should_publish_skill_seed(seed)

        self.assertFalse(decision["publish"])
        self.assertEqual(decision["reason"], "chapter_title_style_candidate")

    def test_chapter_title_seed_is_filtered_even_when_primary_node_exists(self) -> None:
        seed = _seed(
            candidate_id="为争取千百万群众进入抗日民族统一战线而斗争",
            routing_evidence={
                "agentic_priority": 0,
                "matched_keyword_count": 1,
                "case_density_score": 0.5,
            },
            primary_node_id="principle::0108",
        )

        decision = should_publish_skill_seed(seed)

        self.assertFalse(decision["publish"])
        self.assertEqual(decision["reason"], "chapter_title_style_candidate")

    def test_real_judgment_seed_remains_publishable(self) -> None:
        seed = _seed(
            candidate_id="no-investigation-no-decision",
            routing_evidence={
                "agentic_priority": 2,
                "matched_keyword_count": 3,
                "case_density_score": 0.9,
            },
            primary_node_id="principle::001",
        )

        decision = should_publish_skill_seed(seed)

        self.assertTrue(decision["publish"])

    def test_render_generated_run_audits_but_does_not_publish_chapter_title_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_bundle = _source_bundle(root / "source")
            seed = _seed(
                candidate_id="为争取千百万群众进入抗日民族统一战线而斗争",
                routing_evidence={
                    "agentic_priority": 0,
                    "matched_keyword_count": 1,
                    "case_density_score": 0.5,
                },
                primary_node_id=None,
            )

            run_root = render_generated_run(
                source_bundle=source_bundle,
                seeds=[seed],
                output_root=root / "generated",
                run_id="hygiene-smoke",
            )

            manifest = yaml.safe_load((run_root / "bundle" / "manifest.yaml").read_text(encoding="utf-8"))
            audit = json.loads((run_root / "reports" / "skill-hygiene-audit.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["skills"], [])
        self.assertEqual(audit["filtered_count"], 1)
        self.assertEqual(audit["filtered"][0]["candidate_id"], "为争取千百万群众进入抗日民族统一战线而斗争")


def _seed(candidate_id: str, routing_evidence: dict[str, object], primary_node_id: str | None) -> CandidateSeed:
    metadata = {
        "candidate_id": candidate_id,
        "candidate_kind": "general_agentic",
        "disposition": "skill_candidate",
        "routing_evidence": routing_evidence,
        "drafting_mode": "deterministic",
        "recommended_execution_mode": "llm_agentic",
        "loop_mode": "refinement_scheduler",
        "terminal_state": "ready_for_review",
        "source_graph_hash": "sha256:test",
    }
    return CandidateSeed(
        candidate_id=candidate_id,
        candidate_kind="general_agentic",
        primary_node_id=primary_node_id or "",
        supporting_node_ids=[],
        supporting_edge_ids=[],
        community_ids=[],
        gold_match_hint=None,
        source_skill=None,
        score=1,
        metadata=metadata,
        seed_content={"title": candidate_id, "summary": candidate_id},
    )


def _source_bundle(root: Path) -> SourceBundle:
    for relative in ("graph", "traces", "evaluation", "sources"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    graph_doc = {"schema_version": "kiu.graph/v0.2", "nodes": [], "edges": []}
    (root / "graph" / "graph.json").write_text(json.dumps(graph_doc), encoding="utf-8")
    return SourceBundle(
        root=root,
        domain="synthetic",
        manifest={
            "bundle_id": "synthetic-source-v0.6",
            "bundle_version": "0.1.0",
            "graph": {
                "path": "graph/graph.json",
                "graph_version": "kiu.graph/v0.2",
                "graph_hash": "sha256:test",
            },
        },
        graph_doc=graph_doc,
        profile={},
        skills={},
        evaluation_cases=[],
    )


if __name__ == "__main__":
    unittest.main()
