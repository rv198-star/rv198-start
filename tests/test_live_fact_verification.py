from __future__ import annotations

import unittest


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


if __name__ == "__main__":
    unittest.main()
