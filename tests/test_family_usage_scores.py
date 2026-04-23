import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from kiu_pipeline.contracts import build_semantic_contract
from kiu_pipeline.draft import (
    _build_seed_evaluation_summary,
    _build_usage_summary,
    build_revision_summary_markdown,
)
from kiu_pipeline.extraction_bundle import (
    _build_revision_seed,
    _build_seed_evidence_summary,
    _build_seed_rationale,
    _build_usage_notes,
    _write_eval_docs,
)
from kiu_pipeline.load import load_source_bundle
from kiu_pipeline.reference_benchmark import _evaluate_kiu_usage_case
from kiu_pipeline.refiner.loop import _family_revision_note


def _build_fake_skill(skill_id: str, title: str) -> SimpleNamespace:
    descriptors = [
        {
            "anchor_id": f"{skill_id}-anchor-1",
            "label": title,
            "snippet": f"## {title}",
        },
        {
            "anchor_id": f"{skill_id}-anchor-2",
            "label": "supporting-evidence",
            "snippet": "supporting evidence snippet",
        },
        {
            "anchor_id": f"{skill_id}-anchor-3",
            "label": "framework",
            "snippet": "framework snippet",
        },
    ]
    contract = build_semantic_contract(candidate_id=skill_id)
    rationale = _build_seed_rationale(
        candidate_id=skill_id,
        title=title,
        descriptors=descriptors,
        contract=contract,
    )
    evidence_summary = _build_seed_evidence_summary(
        candidate_id=skill_id,
        title=title,
        descriptors=descriptors,
    )
    usage_summary = _build_usage_summary(
        [f"traces/canonical/{skill_id}.yaml"],
        _build_usage_notes(
            candidate_id=skill_id,
            title=title,
            descriptors=descriptors,
        ),
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_root = Path(tmp_dir)
        for relative in (
            "evaluation/real_decisions",
            "evaluation/synthetic_adversarial",
            "evaluation/out_of_distribution",
        ):
            (bundle_root / relative).mkdir(parents=True, exist_ok=True)
        eval_summary = _write_eval_docs(
            bundle_root=bundle_root,
            candidate_id=skill_id,
            title=title,
            descriptors=descriptors,
            contract=contract,
        )
    evaluation_summary = _build_seed_evaluation_summary(
        SimpleNamespace(seed_content={"eval_summary": eval_summary})
    )
    revision_summary = build_revision_summary_markdown(
        {
            "current_revision": 5,
            "history": [
                {
                    "revision": 5,
                    "summary": _family_revision_note(candidate_id=skill_id, round_index=5),
                    "evidence_changes": _build_revision_seed(
                        candidate_id=skill_id,
                        title=title,
                    )["evidence_changes"],
                }
            ],
            "open_gaps": _build_revision_seed(candidate_id=skill_id, title=title)["open_gaps"],
        }
    )
    return SimpleNamespace(
        skill_id=skill_id,
        title=title,
        contract=contract,
        scenario_families={},
        sections={
            "Rationale": rationale,
            "Evidence Summary": evidence_summary,
            "Usage Summary": usage_summary,
            "Evaluation Summary": evaluation_summary,
            "Revision Summary": revision_summary,
        },
        trace_refs=["traces/canonical/mock.yaml"],
        anchors={
            "graph_anchor_sets": [{"node_ids": ["n1"]}],
            "source_anchor_sets": [{"source": "sources/mock.md"}],
            "graph_hash": "graph-hash",
            "graph_version": "v0",
        },
        eval_summary=eval_summary,
        revisions={"current_revision": 1},
    )


class FamilyUsageScoreTests(unittest.TestCase):
    bundle_path = Path(__file__).resolve().parents[1] / "bundles" / "poor-charlies-almanack-v0.1"

    def test_structured_scenario_families_raise_usage_specificity(self) -> None:
        base_skill = SimpleNamespace(
            skill_id="synthetic-value-skill",
            title="Synthetic Value Skill",
            contract={
                "trigger": {
                    "patterns": ["value_decision_required"],
                    "exclusions": ["concept_query_only"],
                },
                "intake": {"required": [{"name": "decision_goal", "type": "string"}]},
                "judgment_schema": {
                    "output": {
                        "type": "structured",
                        "schema": {
                            "next_action": "string",
                            "decline_reason": "string",
                        },
                    }
                },
                "boundary": {
                    "fails_when": ["evidence_conflict"],
                    "do_not_fire_when": ["concept_query_only"],
                },
            },
            scenario_families={},
            sections={
                "Rationale": "Use this skill for real value decisions under uncertainty.",
                "Evidence Summary": "Anchored to source evidence.",
                "Usage Summary": "Current trace attachments: 1.\n\n- Use this skill when a value decision is active.\n\nRepresentative cases:\n- `traces/canonical/mock.yaml`",
                "Evaluation Summary": "当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。",
                "Revision Summary": "Initial revision.",
            },
            trace_refs=["traces/canonical/mock.yaml"],
            anchors={
                "graph_anchor_sets": [{"node_ids": ["n1"]}],
                "source_anchor_sets": [{"source": "sources/mock.md"}],
                "graph_hash": "graph-hash",
                "graph_version": "v0",
            },
            eval_summary={"kiu_test": {"trigger_test": "pass"}},
            revisions={"current_revision": 1},
        )
        scenario_skill = SimpleNamespace(
            **{
                **base_skill.__dict__,
                "scenario_families": {
                    "should_trigger": [
                        {
                            "scenario_id": "panic-mispricing",
                            "prompt_signals": [
                                "市场跌了很多",
                                "好公司可能被错杀了",
                                "现在是不是机会",
                            ],
                            "expected_posture": "full_sizing",
                            "next_action_shape": "从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估",
                            "boundary_reason": "只有在存在真实价格判断时才触发",
                        }
                    ]
                },
            }
        )
        case = {
            "type": "should_trigger",
            "prompt": "最近市场跌了很多，大家都很恐慌，但我觉得有些好公司可能被错杀了，现在是不是机会？",
            "expected_behavior": "应激活 value-assessment，并引导用户在市场恐慌中冷静评估内在价值与价格的差距，寻找安全边际",
            "notes": "命中场景：panic mispricing",
        }

        base_review = _evaluate_kiu_usage_case(
            skill=base_skill,
            case=case,
            alignment_strength=0.65,
        )
        scenario_review = _evaluate_kiu_usage_case(
            skill=scenario_skill,
            case=case,
            alignment_strength=0.65,
        )

        self.assertGreaterEqual(
            scenario_review["overall_score_100"],
            base_review["overall_score_100"] + 8.0,
        )

    def test_circle_non_trigger_comparison_request_scores_as_pass(self) -> None:
        skill = _build_fake_skill(
            "circle-of-competence-source-note",
            "Circle Of Competence Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_not_trigger",
                "prompt": "帮我比较一下Python和Go哪个语言更适合做微服务开发",
                "expected_behavior": "不应激活本 skill，因为用户是在做客观技术比较，不是在判断自己是否处于能力圈外。",
                "notes": "纯技术比较请求。",
            },
            alignment_strength=1.0,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 75.0)

    def test_invert_non_trigger_brainstorming_scores_as_pass(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_not_trigger",
                "prompt": "帮我头脑风暴一下新产品可以有哪些创意方向",
                "expected_behavior": "不应激活本 skill，因为这只是创意发散，不是要做失败分析或风险规避。",
                "notes": "纯 brainstorming。",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 75.0)

    def test_invert_non_trigger_creative_brainstorming_boundary_stays_strict(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_not_trigger",
                "prompt": "帮我头脑风暴一下新产品可以有哪些创意方向",
                "expected_behavior": "不应激活本 skill，因为用户需要的是创意发散而非风险规避。逆向思维天然偏向保守和防御，不适合创意场景",
                "notes": "边界：需要创意发散时不适用，不能把 failure-first 硬套进 ideation。",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 80.0)

    def test_published_invert_skill_refuses_concept_query_without_boundary_leak(self) -> None:
        bundle = load_source_bundle(self.bundle_path)
        skill = bundle.skills["invert-the-problem"]

        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_not_trigger",
                "prompt": "逆向思维是什么意思？能给我解释一下这个概念吗",
                "expected_behavior": "不应激活本 skill，因为用户只是在询问概念定义，不需要将逆向思维应用于实际决策",
                "notes": "纯知识查询。",
            },
            alignment_strength=0.9,
        )

        self.assertNotIn("boundary_leak", review["failure_analysis"]["tags"])
        self.assertGreaterEqual(review["overall_score_100"], 75.0)

    def test_published_margin_skill_refuses_concept_query_without_boundary_leak(self) -> None:
        bundle = load_source_bundle(self.bundle_path)
        skill = bundle.skills["margin-of-safety-sizing"]

        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_not_trigger",
                "prompt": "什么是安全边际？芒格和巴菲特是怎么定义内在价值的？",
                "expected_behavior": "不应激活, 因为这是纯概念查询，不是在面临一个需要做价值判断的真实投资决策",
                "notes": "纯概念查询。",
            },
            alignment_strength=0.65,
        )

        self.assertNotIn("boundary_leak", review["failure_analysis"]["tags"])
        self.assertGreaterEqual(review["overall_score_100"], 75.0)

    def test_circle_trigger_ai_boundary_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "circle-of-competence-source-note",
            "Circle Of Competence Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "老板让我负责一个AI相关的项目，虽然我没做过机器学习，但感觉跟之前的软件工程差不多，我可以学嘛，帮我评估一下我是否适合做这件事",
                "expected_behavior": "应激活 circle-of-competence，帮用户区分软件工程经验和机器学习专业能力的边界，评估核心风险点是否在能力圈内，给出圈内/边界/圈外的分类判断",
                "notes": "正面场景：面对新领域挑战，语言信号匹配我可以学和感觉跟XX差不多以及帮我评估一下我是否适合做这件事",
            },
            alignment_strength=1.0,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 88.0)

    def test_invert_trigger_startup_failure_paths_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "我准备明年创业做在线教育，但目前只知道要成功需要做什么，不知道有没有什么我没想到的风险，能帮我从失败的角度分析一下吗",
                "expected_behavior": "应激活 inversion-thinking，帮助用户列出创业可能失败的具体路径（资金断裂、获客成本、政策风险等），形成避坑清单",
                "notes": "正面场景：创业决策，用户主动要求从失败角度分析，匹配有没有什么我没想到的触发信号",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 84.0)

    def test_circle_trigger_self_media_monetization_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "circle-of-competence-source-note",
            "Circle Of Competence Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "我在考虑要不要从大厂辞职去全职做自媒体，我好像懂了怎么做内容，但说不清楚到底怎么变现，你觉得我能行吗",
                "expected_behavior": "应激活 circle-of-competence，对说不清楚变现逻辑进行否定测试。说不清等于不在圈内，先列出真正理解和不理解的部分，再制定行动方案",
                "notes": "正面场景：重大职业转型决策，语言信号匹配我好像懂了，但说不清楚",
            },
            alignment_strength=1.0,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 84.0)

    def test_bias_non_trigger_urgent_incident_scores_as_pass(self) -> None:
        skill = _build_fake_skill(
            "bias-self-audit-source-note",
            "Bias Self Audit Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_not_trigger",
                "prompt": "服务器突然宕机了，客户在催，我需要立刻判断是数据库问题还是网络问题",
                "expected_behavior": "不应激活, 因为 B 段明确排除紧急决策场景——系统性地搜索反面证据不现实",
                "notes": "诱饵: 需要做判断但属于紧急场景，不是方法论检验的合适时机",
            },
            alignment_strength=0.75,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 75.0)

    def test_margin_trigger_price_reasonable_scores_as_pass(self) -> None:
        skill = _build_fake_skill(
            "margin-of-safety-sizing-source-note",
            "Margin Of Safety Sizing Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "我在考虑要不要买一只消费股，市盈率25倍不算便宜，但品牌很强，这个价格合理吗？安全边际够不够？",
                "expected_behavior": "应激活本 skill，把护城河、价格、下行风险和仓位约束连起来判断安全边际。",
                "notes": "真实估值与仓位决策。",
            },
            alignment_strength=0.65,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 75.0)

    def test_margin_trigger_price_reasonable_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "margin-of-safety-sizing-source-note",
            "Margin Of Safety Sizing Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "我在考虑要不要买一只消费股，市盈率25倍不算便宜，但品牌很强，这个价格合理吗？安全边际够不够？",
                "expected_behavior": "应激活 value-assessment，并从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估",
                "notes": "命中 A2 语言信号: 值不值得买 + 价格合理吗/安全边际 + 具体投资决策场景",
            },
            alignment_strength=0.65,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 82.0)

    def test_margin_trigger_angel_round_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "margin-of-safety-sizing-source-note",
            "Margin Of Safety Sizing Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "有个朋友推荐了一个创业项目让我投天使轮，商业模式我大概能看懂，但不确定值不值得投",
                "expected_behavior": "应激活 value-assessment，并先做能力圈检验（是否真正理解这门生意），再评估护城河和安全边际",
                "notes": "命中 A2 场景: 评估投资/创业项目是否值得投入",
            },
            alignment_strength=0.65,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 80.0)

    def test_invert_trigger_investment_ruin_scan_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "我在做一个投资决策，正面分析都做完了，但我就是不确定怎么才能让这个投资不失败，你能帮我想想什么情况下这笔投资会血本无归吗",
                "expected_behavior": "应激活 inversion-thinking，从什么会导致投资失败的反面视角列出致命风险因素，并形成失败前置检查清单",
                "notes": "正面场景：投资决策，用户明确表达从失败角度分析的需求",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 82.0)

    def test_invert_trigger_team_threat_scan_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "should_trigger",
                "prompt": "团队头脑风暴讨论新产品方向，大家提了很多好想法，但我担心我们只看到了机会没看到威胁，能不能系统性地找找这个方案的茬",
                "expected_behavior": "应激活 inversion-thinking，针对团队只看机会忽视威胁的场景，系统性地列出潜在威胁和失败模式，并形成找茬清单与预防动作",
                "notes": "正面场景：团队只看机会没看到威胁，需要系统性找茬，而不是继续扩创意广度",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 86.0)

    def test_invert_edge_job_switch_risk_screen_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "edge_case",
                "prompt": "我在纠结要不要跳槽去一家新公司，你能帮我分析一下吗",
                "expected_behavior": "可激活也可不激活。如果进一步对话发现用户是想系统性评估跳槽风险和失败模式，则激活；如果只是比较两个选项的优劣，则更适合一般决策辅助",
                "notes": "边界：职业决策不天然等于 inversion，关键看用户是否担心自己遗漏了致命风险",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 80.0)

    def test_invert_edge_low_stakes_personal_plan_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "invert-the-problem-source-note",
            "Invert The Problem Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "edge_case",
                "prompt": "我想制定一个明年的健身计划，你能帮我从'怎么才会失败'的角度来设计吗",
                "expected_behavior": "可以激活但权重较低。用户主动请求从失败角度分析，符合触发信号，但健身计划属于个人日常目标，适合轻量 pre-mortem 而不是重大决策级别的方法论展开",
                "notes": "边界：语言信号匹配，但重要度较低，应该输出轻量版 failure-first 检查而不是重型风险框架",
            },
            alignment_strength=0.9,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 78.0)

    def test_margin_edge_crypto_non_applicability_scores_with_high_specificity(self) -> None:
        skill = _build_fake_skill(
            "margin-of-safety-sizing-source-note",
            "Margin Of Safety Sizing Source Note",
        )
        review = _evaluate_kiu_usage_case(
            skill=skill,
            case={
                "type": "edge_case",
                "prompt": "比特币最近涨了很多，我想用芒格的思维框架来评估一下值不值得买",
                "expected_behavior": "不应激活或强烈警告，因为面对高波动但无内在价值的投机标的时，安全边际不适用于赌博",
                "notes": "边界：用户主动要求用芒格框架，但标的本身不在框架适用范围内",
            },
            alignment_strength=0.65,
        )

        self.assertEqual(review["verdict"], "pass")
        self.assertGreaterEqual(review["overall_score_100"], 80.0)


if __name__ == "__main__":
    unittest.main()
