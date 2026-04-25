from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

import yaml


class ClaimLedgerTests(unittest.TestCase):
    def test_claim_ledger_marks_current_market_claim_as_verification_required(self) -> None:
        from kiu_pipeline.claim_ledger import build_claim_ledger

        ledger = build_claim_ledger(
            bundle_id="sample-bundle",
            records=[
                {
                    "skill_id": "challenge-price-with-value",
                    "prompt": "当前市场数据证明这家公司被低估，可以直接买入吗？",
                    "temporal_sensitivity": "high",
                    "verdict": "refuse",
                    "reason": "No live web available for current market data.",
                }
            ],
            mode="no_web",
        )

        claim = ledger["claims"][0]
        self.assertEqual(ledger["schema_version"], "kiu.claim-ledger/v0.1")
        self.assertTrue(claim["verification_required"])
        self.assertFalse(claim["allowed_without_web"])
        self.assertEqual(claim["claim_type"], "current_market_fact")
        self.assertEqual(claim["verification_status"], "pending")

    def test_claim_ledger_does_not_force_low_temporal_source_skill_into_live_check(self) -> None:
        from kiu_pipeline.claim_ledger import build_claim_ledger

        ledger = build_claim_ledger(
            bundle_id="sample-bundle",
            records=[
                {
                    "skill_id": "circle-of-competence",
                    "prompt": "我是否应该承认自己不懂这个领域？",
                    "temporal_sensitivity": "low",
                    "verdict": "apply",
                    "reason": "Source-faithful principle application.",
                }
            ],
            mode="no_web",
        )

        self.assertEqual(ledger["claims"], [])


class ExternalFactPackTests(unittest.TestCase):
    def test_external_fact_pack_requires_citation_metadata(self) -> None:
        from kiu_pipeline.live_facts import build_external_fact_pack, validate_external_fact_pack

        pack = build_external_fact_pack(
            claims=[{"claim_id": "claim-001", "text": "SEC 10-K is available", "claim_type": "current_regulatory_fact"}],
            facts=[
                {
                    "claim_id": "claim-001",
                    "claim": "SEC 10-K is available",
                    "verification_status": "supported",
                    "evidence": [
                        {
                            "source_url": "https://www.sec.gov/",
                            "source_title": "SEC",
                            "published_at": "2026-04-20",
                            "retrieved_at": "2026-04-26T00:00:00Z",
                            "relation_to_claim": "supports",
                        }
                    ],
                    "freshness_status": "current",
                    "confidence": "medium",
                    "decision_effect": ["allow_cited_application"],
                }
            ],
            retrieved_at="2026-04-26T00:00:00Z",
        )

        self.assertEqual(pack["schema_version"], "kiu.external-fact-pack/v0.1")
        self.assertEqual(validate_external_fact_pack(pack), [])

    def test_external_fact_pack_flags_missing_relation_to_claim(self) -> None:
        from kiu_pipeline.live_facts import build_external_fact_pack, validate_external_fact_pack

        pack = build_external_fact_pack(
            claims=[],
            facts=[{"claim_id": "claim-001", "claim": "x", "verification_status": "supported", "evidence": [{"source_url": "https://example.com"}]}],
            retrieved_at="2026-04-26T00:00:00Z",
        )

        errors = validate_external_fact_pack(pack)
        self.assertTrue(any("relation_to_claim" in error for error in errors))


class FactVerificationTests(unittest.TestCase):
    def test_fact_verification_status_matrix_blocks_unsafe_direct_apply(self) -> None:
        from kiu_pipeline.fact_verification import direct_apply_allowed, verify_claim_against_evidence

        cases = [
            ("Company filed its 2025 10-K", [{"text": "Company filed its 2025 10-K", "published_at": "2026-02-01"}], "supported", True),
            ("Company filed its 2025 10-K and raised guidance", [{"text": "Company filed its 2025 10-K", "published_at": "2026-02-01"}], "partially_supported", True),
            ("Company is undervalued today", [{"text": "Company reports revenue", "published_at": "2026-02-01"}], "unsupported", False),
            ("Policy requires X", [{"text": "Policy says X is not required", "published_at": "2026-04-01"}], "conflicting", False),
            ("Current rate is 5%", [{"text": "Rate was 5%", "published_at": "2020-01-01"}], "stale", False),
            ("Current rule is active", [{"text": "Rule is active"}], "undated", False),
            ("Market proves buy", [], "insufficient_evidence", False),
            ("Market proves buy", [{"retrieval_error": "timeout"}], "retrieval_failed", False),
        ]

        for claim, evidence, expected_status, expected_allowed in cases:
            result = verify_claim_against_evidence(claim, evidence, retrieved_at="2026-04-26T00:00:00Z")
            self.assertEqual(result["verification_status"], expected_status)
            self.assertEqual(direct_apply_allowed(result), expected_allowed)


class LiveRetrievalAndGateTests(unittest.TestCase):
    def test_live_retrieval_adapter_records_source_metadata_without_advice(self) -> None:
        from kiu_pipeline.live_facts import retrieve_live_facts_for_claims

        def fake_fetch(url: str) -> dict[str, str]:
            return {
                "source_url": url,
                "source_title": "Official Source",
                "text": "Company filed its 2025 10-K",
                "published_at": "2026-02-01",
            }

        pack = retrieve_live_facts_for_claims(
            claims=[{"claim_id": "claim-001", "text": "Company filed its 2025 10-K", "claim_type": "current_regulatory_fact"}],
            source_urls=["https://example.gov/company-10-k"],
            retrieved_at="2026-04-26T00:00:00Z",
            fetcher=fake_fetch,
        )

        fact = pack["facts"][0]
        self.assertEqual(fact["evidence"][0]["source_title"], "Official Source")
        self.assertEqual(fact["verification_status"], "supported")
        self.assertNotIn("advice", fact)
        self.assertNotIn("recommendation", fact)

    def test_live_retrieval_failure_is_recorded_not_fabricated(self) -> None:
        from kiu_pipeline.live_facts import retrieve_live_facts_for_claims

        def failing_fetch(url: str) -> dict[str, str]:
            raise TimeoutError("network timeout")

        pack = retrieve_live_facts_for_claims(
            claims=[{"claim_id": "claim-001", "text": "Current market proves buy", "claim_type": "current_market_fact"}],
            source_urls=["https://example.gov/market"],
            retrieved_at="2026-04-26T00:00:00Z",
            fetcher=failing_fetch,
        )

        fact = pack["facts"][0]
        self.assertEqual(fact["verification_status"], "retrieval_failed")
        self.assertEqual(fact["evidence"][0]["relation_to_claim"], "retrieval_failed")
        self.assertIn("network timeout", fact["evidence"][0]["retrieval_error"])

    def test_freshness_gate_maps_verification_status_to_safe_verdicts(self) -> None:
        from kiu_pipeline.freshness_gate import application_decision_from_verification

        expected = {
            "supported": "apply_with_caveats",
            "partially_supported": "partial_apply",
            "unsupported": "refuse",
            "conflicting": "refuse",
            "stale": "ask_more_context",
            "undated": "ask_more_context",
            "insufficient_evidence": "ask_more_context",
            "retrieval_failed": "refuse",
        }

        for status, verdict in expected.items():
            decision = application_decision_from_verification({"verification_status": status}, high_stakes=True)
            self.assertEqual(decision["verdict"], verdict)
            self.assertTrue(decision["world_context_isolated"])
            self.assertNotIn("rewrite_source_claim", decision.get("decision_effect", []))

    def test_world_alignment_consumes_fact_pack_without_mutating_skill_markdown(self) -> None:
        from kiu_pipeline.world_alignment import apply_external_fact_pack_to_gates

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bundle"
            skill_dir = bundle / "skills" / "challenge-price-with-value"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text("# Challenge Price With Value\n\nSource-only content.", encoding="utf-8")
            (bundle / "manifest.yaml").write_text(
                yaml.safe_dump({"skills": [{"skill_id": "challenge-price-with-value", "path": "skills/challenge-price-with-value"}]}),
                encoding="utf-8",
            )
            gate_dir = bundle / "world_alignment" / "challenge-price-with-value"
            gate_dir.mkdir(parents=True)
            (gate_dir / "application_gate.yaml").write_text(
                yaml.safe_dump({"skill_id": "challenge-price-with-value", "verdict": "ask_more_context", "world_context_isolated": True}),
                encoding="utf-8",
            )
            before = skill_md.read_text(encoding="utf-8")

            summary = apply_external_fact_pack_to_gates(
                bundle,
                {
                    "facts": [
                        {
                            "claim_id": "claim-001",
                            "skill_id": "challenge-price-with-value",
                            "verification_status": "supported",
                            "evidence": [{"source_url": "https://example.gov/fact", "relation_to_claim": "supports"}],
                        }
                    ]
                },
            )

            self.assertEqual(summary["updated_gate_count"], 1)
            self.assertEqual(skill_md.read_text(encoding="utf-8"), before)
            live_gate = yaml.safe_load((gate_dir / "application_gate.live.yaml").read_text(encoding="utf-8"))
            self.assertEqual(live_gate["verdict"], "apply_with_caveats")
            self.assertTrue(live_gate["web_check_performed"])

    def test_hallucination_matrix_blocks_negative_cases_and_allows_low_temporal_source_use(self) -> None:
        from kiu_pipeline.fact_verification import direct_apply_allowed, verify_claim_against_evidence

        negative_cases = [
            ("Company is undervalued today", [{"text": "Company reports revenue", "published_at": "2026-02-01"}], "unsupported"),
            ("Policy requires X", [{"text": "Policy says X is not required", "published_at": "2026-04-01"}], "conflicting"),
            ("Current rate is 5%", [{"text": "Rate was 5%", "published_at": "2020-01-01"}], "stale"),
            ("Market proves buy", [{"retrieval_error": "timeout"}], "retrieval_failed"),
        ]
        for claim, evidence, status in negative_cases:
            result = verify_claim_against_evidence(claim, evidence, retrieved_at="2026-04-26T00:00:00Z")
            self.assertEqual(result["verification_status"], status)
            self.assertFalse(direct_apply_allowed(result))

        from kiu_pipeline.claim_ledger import build_claim_ledger

        ledger = build_claim_ledger(
            bundle_id="sample",
            records=[{"skill_id": "circle-of-competence", "prompt": "Should I stay inside competence?", "temporal_sensitivity": "low"}],
        )
        self.assertEqual(ledger["claims"], [])


class LiveFactPreflightTests(unittest.TestCase):
    def test_live_fact_urls_do_not_pollute_source_skill_markdown(self) -> None:
        from kiu_pipeline.preflight import scan_live_fact_pollution

        errors = scan_live_fact_pollution(
            skill_markdown="# Skill\nEvidence: examples/book.md",
            fact_pack={"facts": [{"evidence": [{"source_url": "https://example.gov/fact"}]}]},
        )
        self.assertEqual(errors, [])

        polluted = scan_live_fact_pollution(
            skill_markdown="# Skill\nEvidence: https://example.gov/fact",
            fact_pack={"facts": [{"evidence": [{"source_url": "https://example.gov/fact"}]}]},
        )
        self.assertTrue(any("live fact URL" in error for error in polluted))


if __name__ == "__main__":
    unittest.main()
