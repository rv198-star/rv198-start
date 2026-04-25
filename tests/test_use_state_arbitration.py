from __future__ import annotations

import unittest

from kiu_pipeline.use_state import (
    EvidenceState,
    UseState,
    classify_use_state,
    compose_final_verdict,
    evaluate_evidence_sufficiency,
)


class UseStateArbitrationTests(unittest.TestCase):
    def test_use_state_fixture_matrix_classifies_core_books(self) -> None:
        fixtures = [
            ("shiji-summary", "请总结项羽失败的原因。", UseState.SOURCE_UNDERSTANDING),
            ("shiji-translation", "把这段史记原文翻译成现代中文。", UseState.SOURCE_UNDERSTANDING),
            ("mao-viewpoint", "解释一下作者在这篇文章里的主要观点。", UseState.SOURCE_UNDERSTANDING),
            ("poor-charlie-definition", "解释一下能力圈是什么意思。", UseState.SOURCE_UNDERSTANDING),
            ("shiji-transfer", "鸿门宴这个历史案例能不能借鉴到我们团队谈判？", UseState.TRANSFER_CANDIDATE),
            ("shiji-analogy", "这个故事像不像我们现在的合作伙伴局面？", UseState.TRANSFER_CANDIDATE),
            ("mao-principle-transfer", "主要矛盾这个原则能否迁移到我们的产品路线取舍？", UseState.TRANSFER_CANDIDATE),
            ("poor-charlie-case-transfer", "芒格这个案例能不能借鉴到我的投资流程？", UseState.TRANSFER_CANDIDATE),
            ("shiji-copy", "项羽这么做过，我们也照做吧。", UseState.TRANSFER_ABUSE_RISK),
            ("competitor-copy", "竞品这样做成功了，我们也照搬，不要再分析。", UseState.TRANSFER_ABUSE_RISK),
            ("big-company-copy", "大公司都这么做，我们也直接复制这个流程。", UseState.TRANSFER_ABUSE_RISK),
            ("book-authority-copy", "书里这样做成功了，所以我们直接按书执行。", UseState.TRANSFER_ABUSE_RISK),
            ("mao-no-investigation", "没有调查但老板要我今天拍板定方案。", UseState.CONTEXT_INSUFFICIENT),
            ("poor-charlie-direct", "不要问上下文，直接替我决定要不要辞职。", UseState.CONTEXT_INSUFFICIENT),
            ("requirements-thin", "只有一个粗功能列表，还不知道真实用户和失败后果，能直接拆子系统吗？", UseState.CONTEXT_INSUFFICIENT),
            ("conflict-evidence", "证据互相冲突，但我急着要结论。", UseState.CONTEXT_INSUFFICIENT),
            ("financial-current-price", "这只股票今天该买吗？", UseState.CURRENT_FACT_REQUIRED),
            ("financial-latest", "请列出苹果公司最新股价和成交量。", UseState.CURRENT_FACT_REQUIRED),
            ("law-current", "这个法规现在是否已经生效？", UseState.CURRENT_FACT_REQUIRED),
            ("policy-current", "当前政策变化会不会影响这个判断？", UseState.CURRENT_FACT_REQUIRED),
            ("mao-reflection", "没有调查就没有发言权对我个人决策有什么启发？", UseState.LOW_RISK_REFLECTION),
            ("poor-charlie-reflection", "能力圈这个原则如何帮助我反思自己的边界？", UseState.LOW_RISK_REFLECTION),
            ("shiji-reflection", "读这段历史对我借古自省有什么启发？", UseState.LOW_RISK_REFLECTION),
            ("philosophy-reflection", "这个原则对日常思考有什么启发，不需要做现实决策。", UseState.LOW_RISK_REFLECTION),
            ("requirements-bounded", "我们要在调度、安全、计费之间重画业务边界，用户和失败后果已经明确，下一步如何拆？", UseState.BOUNDED_APPLICATION),
            ("financial-bounded", "我已有完整年报和风险期限，只想用书中方法检查现金流质量。", UseState.BOUNDED_APPLICATION),
            ("mao-bounded", "我们已有一线访谈材料，要用主要矛盾原则排序三个产品问题。", UseState.BOUNDED_APPLICATION),
            ("poor-charlie-bounded", "我已列出能力、信息和风险边界，要用能力圈原则判断是否继续研究。", UseState.BOUNDED_APPLICATION),
        ]

        for case_id, prompt, expected in fixtures:
            with self.subTest(case_id=case_id):
                decision = classify_use_state(prompt)
                self.assertEqual(decision.use_state, expected)

    def test_evidence_sufficiency_blocks_transfer_without_required_fields(self) -> None:
        state = evaluate_evidence_sufficiency(
            use_state=UseState.TRANSFER_CANDIDATE,
            mechanism_mapping_present=True,
            transfer_conditions_present=False,
            anti_conditions_present=True,
            verified_current_fact_present=False,
        )

        self.assertFalse(state.direct_apply_allowed)
        self.assertIn("transfer_conditions_missing", state.reasons)

    def test_final_verdict_blocks_unsafe_direct_apply_states(self) -> None:
        unsafe_states = [
            UseState.SOURCE_UNDERSTANDING,
            UseState.CONTEXT_INSUFFICIENT,
            UseState.TRANSFER_ABUSE_RISK,
            UseState.CURRENT_FACT_REQUIRED,
        ]

        for use_state in unsafe_states:
            with self.subTest(use_state=use_state.value):
                verdict = compose_final_verdict(
                    use_state=use_state,
                    source_verdict="apply",
                    evidence_state=EvidenceState(direct_apply_allowed=False, reasons=["blocked"]),
                    verified_current_fact_present=False,
                )
                self.assertNotEqual(verdict.final_verdict, "apply")

    def test_low_risk_reflection_is_not_over_gated(self) -> None:
        verdict = compose_final_verdict(
            use_state=UseState.LOW_RISK_REFLECTION,
            source_verdict="apply",
            evidence_state=EvidenceState(direct_apply_allowed=True, reasons=[]),
            verified_current_fact_present=False,
        )

        self.assertEqual(verdict.final_verdict, "apply_with_caveats")
        self.assertIn(verdict.world_intervention_level, {"minimal", "light"})

    def test_bounded_application_can_apply_when_evidence_is_sufficient(self) -> None:
        verdict = compose_final_verdict(
            use_state=UseState.BOUNDED_APPLICATION,
            source_verdict="apply",
            evidence_state=EvidenceState(direct_apply_allowed=True, reasons=[]),
            verified_current_fact_present=False,
        )

        self.assertEqual(verdict.final_verdict, "apply")


if __name__ == "__main__":
    unittest.main()
