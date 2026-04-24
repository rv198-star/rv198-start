import json
import tempfile
import unittest
from pathlib import Path

from kiu_pipeline.blind_review_pack import build_blind_review_pack
from kiu_pipeline.blind_review_pack import merge_blind_review_response
from kiu_pipeline.reference_benchmark import _load_blind_preference_summary


class BlindReviewPackTests(unittest.TestCase):
    def test_build_pack_separates_public_review_from_private_unblind_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            generated_bundle = root / "generated" / "bundle"
            reference_pack = root / "reference"
            kiu_skill = generated_bundle / "alpha-skill"
            ref_skill = reference_pack / "alpha-skill"
            kiu_skill.mkdir(parents=True)
            ref_skill.mkdir(parents=True)
            (kiu_skill / "SKILL.md").write_text(
                "# KiU Alpha\n\nskill_id: alpha-skill\n\n## Contract\nTrigger: use when action judgment is needed.\n\n## Boundary\nDo not use for fact lookup.\n",
                encoding="utf-8",
            )
            (ref_skill / "SKILL.md").write_text(
                "# Reference Alpha\n\nname: alpha-skill\n\n## E — 可执行步骤\n1. Compare mechanisms.\n\n## B — 边界\nAvoid overreach.\n",
                encoding="utf-8",
            )
            benchmark = {
                "generated_run": {"generated_bundle_path": str(generated_bundle)},
                "reference_pack": {"path": str(reference_pack)},
                "same_scenario_usage": {
                    "matched_pairs": [
                        {
                            "kiu_skill_id": "alpha-skill",
                            "reference_skill_id": "alpha-skill",
                            "cases": [
                                {
                                    "case_id": "case-1",
                                    "type": "should_trigger",
                                    "prompt": "Should I apply this decision pattern?",
                                    "expected_behavior": "should activate alpha-skill",
                                    "notes": "smoke",
                                }
                            ],
                        }
                    ]
                },
            }
            benchmark_path = root / "benchmark.json"
            benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
            out = root / "blind-pack"

            summary = build_blind_review_pack(
                benchmark_report_path=benchmark_path,
                output_dir=out,
                review_id="blind-smoke",
            )

            self.assertEqual(summary["pair_count"], 1)
            public_doc = json.loads((out / "reviewer-pack.json").read_text(encoding="utf-8"))
            template = json.loads((out / "reviewer-response-template.json").read_text(encoding="utf-8"))
            key_doc = json.loads((out / "private-unblind-key.json").read_text(encoding="utf-8"))

            public_text = json.dumps(public_doc, ensure_ascii=False).lower()
            self.assertNotIn("kiu", public_text)
            self.assertNotIn('"reference"', public_text)
            self.assertNotIn("alpha-skill", public_text)
            self.assertNotIn("option_roles", public_text)
            self.assertNotIn("option_roles", json.dumps(template, ensure_ascii=False))
            self.assertEqual(key_doc["pairs"][0]["option_roles"].keys(), {"a", "b"})

    def test_merge_response_with_private_key_produces_loadable_blind_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            key_path = root / "private-unblind-key.json"
            response_path = root / "reviewer-response.json"
            evidence_path = root / "blind-evidence.json"
            key_path.write_text(
                json.dumps(
                    {
                        "schema_version": "kiu.blind-review-key/v0.1",
                        "review_id": "blind-smoke",
                        "pairs": [
                            {"pair_id": "p1", "option_roles": {"a": "kiu", "b": "reference"}}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            response_path.write_text(
                json.dumps(
                    {
                        "schema_version": "kiu.blind-review-response/v0.1",
                        "review_id": "blind-smoke",
                        "pairs": [
                            {
                                "pair_id": "p1",
                                "preferred": "a",
                                "dimension_scores": {
                                    "usage": 5,
                                    "depth": 5,
                                    "transferability": 4,
                                    "anti_misuse": 5,
                                },
                                "notes": "Option A is more usable.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            summary = merge_blind_review_response(
                response_path=response_path,
                key_path=key_path,
                output_path=evidence_path,
            )

            self.assertEqual(summary["pair_count"], 1)
            loaded = _load_blind_preference_summary(evidence_path)
            self.assertTrue(loaded["valid"])
            self.assertEqual(loaded["pass_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
