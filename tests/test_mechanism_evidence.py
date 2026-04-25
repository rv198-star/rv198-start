from __future__ import annotations

import unittest

from kiu_pipeline.mechanism_evidence import decide_anchor_role, score_mechanism_evidence


class MechanismEvidenceTests(unittest.TestCase):
    def test_high_mechanism_evidence_can_be_primary_anchor(self) -> None:
        evidence = (
            "团队在没有现场调查时直接按模板定方案，导致关键用户流程被遗漏。"
            "后来负责人先访谈一线角色，识别业务约束，再调整系统边界，返工风险下降。"
        )

        score = score_mechanism_evidence(evidence)
        role = decide_anchor_role(score)

        self.assertGreaterEqual(score["mechanism_density_score"], 0.75)
        self.assertTrue(role["primary_anchor_allowed"])
        self.assertEqual(role["anchor_role"], "primary")

    def test_information_dense_but_mechanism_weak_evidence_is_not_primary(self) -> None:
        evidence = "## 为争取千百万群众进入抗日民族统一战线而斗争\n（一九三七年五月八日）\n注释：见本卷相关说明。"

        score = score_mechanism_evidence(evidence)
        role = decide_anchor_role(score)

        self.assertLess(score["mechanism_density_score"], 0.5)
        self.assertFalse(role["primary_anchor_allowed"])
        self.assertEqual(role["anchor_role"], "source_context_only")

    def test_title_or_list_can_remain_supporting_context(self) -> None:
        evidence = "关键步骤：调查对象、行动边界、约束条件、失败后果、反证材料。"

        score = score_mechanism_evidence(evidence)
        role = decide_anchor_role(score)

        self.assertFalse(role["primary_anchor_allowed"])
        self.assertEqual(role["anchor_role"], "supporting")
        self.assertIn("supporting_context", role["reason"])


if __name__ == "__main__":
    unittest.main()
