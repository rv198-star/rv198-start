---
name: kiu-poor-charlie-margin-of-safety-sizing
description: Use this KiU-generated action skill from Poor Charlie's Almanack when the task matches `margin-of-safety-sizing`.
---

# Margin of Safety Sizing

## Identity
```yaml
skill_id: margin-of-safety-sizing
title: Margin of Safety Sizing
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 3
```

## Contract
```yaml
trigger:
  patterns:
  - user_deciding_position_size_for_investment
  - user_contemplating_concentrated_capital_allocation
  exclusions:
  - user_missing_uncertainty_inputs
  - user_request_is_non_investing_decision
intake:
  required:
  - name: downside_range
    type: structured
    description: Estimated downside range and ruin conditions.
  - name: liquidity_profile
    type: structured
    description: Liquidity, reversibility, and access to fallback capital.
  - name: conviction_basis
    type: string
    description: Why the user believes the edge exists.
judgment_schema:
  output:
    type: structured
    schema:
      sizing_band: enum[tiny, small, medium, concentrated, refuse]
      constraints: list[string]
      rationale: string
      applicability_mode: enum[full_sizing, partial_applicability, refuse]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - user_asserts_high_conviction_without_downside_math
  - liquidity_or_ruin_inputs_are_missing
  do_not_fire_when:
  - user_request_is_non_investing_decision
  - user_missing_uncertainty_inputs
```

## Rationale
这条 skill 负责把“值不值得”翻译成“最多能下多大”，而不是停留在抽象的估值讨论里。凡是用户出现“这个价格合理吗”“安全边际够不够”“品牌很强但不便宜”“市场恐慌是不是机会”“这家公司提价客户也不会跑”“这个项目值不值得投”这类信号，都应该把问题继续往 sizing 层推进：即使护城河、定价权、管理层、能力圈这些前置判断都看起来不错，仓位大小仍然要由 downside range、流动性、可逆性、回本路径和爆仓/被动卖出的风险来决定。[^anchor:margin-source-note]

因此这条 skill 的核心不是预测上涨空间，而是保护生存和可选项。要问的不是“最乐观能赚多少”，而是“如果我看错了、晚了、流动性抽干了、或者需要再融资，损失会放大到什么程度”。哪怕用户说“这种公司和其他公司到底差在哪”，答案也不能只停在“护城河很宽”上，而要继续追问：这种差异会不会转化为更稳的下行保护、更长的回本耐心、以及更可承受的仓位。芒格反复强调，真正稀缺的是“尚未利用的提价能力”，但即便如此，提价能力也只是前置质量信号，不是自动放大仓位的许可证。如果用户拿不出下行区间、流动性约束、资金缓冲、关联风险或不可逆损失的描述，就不能因为故事好、品牌强、趋势热而给大仓位；正确动作往往是缩小到 `tiny / small`，甚至直接 `refuse`。[^anchor:margin-eval] [^trace:canonical/salomon-exposure-cap.yaml]

### Downstream Use Check
This skill must turn caution into an executable risk boundary: identify the exposure being limited, connect the limit to source evidence, name the assumption that would break the recommendation, and give the next safer sizing or deferral action.

Minimum Pressure Pass (failure pressure): Stress the worst credible miss, not the average case; if one adverse assumption would make the exposure unrecoverable, output a smaller sizing, a deferral, or a refusal to size. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
三条 canonical trace 定义了 sizing discipline。`sees-candies-discipline` 说明“伟大企业可以公道价买入”并不等于任何时候都该重仓；只有在业务韧性和 downside resilience 都足够明确时，质量才配得上 concentration，而且“尚未利用的提价能力”只能说明企业可能伟大，不能替你完成 sizing。[^trace:canonical/sees-candies-discipline.yaml] `salomon-exposure-cap` 说明暴露上限是生存工具，不是信念不足：哪怕 thesis 成立，只要杠杆、声誉风险或关联敞口会在压力下放大伤害，就应先压仓位。[^trace:canonical/salomon-exposure-cap.yaml] `irreversible-bet-precheck` 则对应“值不值得投 / 安全边际够不够”的边界情景：如果回撤后难以抽身、决策不可逆、回本周期过长、或失败一次就严重伤筋动骨，仓位必须先缩再说。[^trace:canonical/irreversible-bet-precheck.yaml]

这些证据共同支持一个判断：安全边际不是给看多观点贴一层谨慎措辞，而是把护城河、定价权、能力圈和价格判断，最后落实为不会把自己逼到被动局面的 sizing band。[^anchor:margin-source-note] [^anchor:margin-eval]

The v0.2 seed preserves graph/source double anchoring and records the workflow-vs-agentic routing decision in `candidate.yaml`.

Scenario-family anchor coverage: `should_trigger` `live-price-vs-value-decision` -> `margin-source-note`, `margin-trace-sees` (这不是纯估值讨论，而是要把前置判断落实成真实 sizing。); `should_trigger` `panic-mispricing-check` -> `margin-trace-salomon`, `margin-eval` (这里需要同时判断价值锚、回撤承受力和仓位大小，而不是只判断“公司好不好”。); `should_not_trigger` `short-term-trading` -> `margin-source-note` (这条 skill 面向长期资本配置，不是给短线仓位美化。); `should_not_trigger` `pure-scale-comparison` -> `margin-source-note` (这类问题更像一般商业分析，而不是 live sizing 决策。); `edge_case` `private-business-or-franchise` -> `margin-trace-irreversible`, `margin-eval` (价值逻辑部分适用，但流动性、退出难度和资产类型与公开市场不同。); `edge_case` `angel-check-under-uncertainty` -> `margin-source-note`, `margin-eval` (理解浅、流动性差、失败不可逆时，不能因为故事好就给正常 sizing。); `refusal` `speculative-asset-without-value-anchor` -> `margin-source-note` (安全边际不适用于赌博，不能拿本框架替投机做背书。).

Graph-to-skill distillation: `INFERRED` graph links `e_invert_margin_complements` (`Invert the problem` -> `Margin of safety sizing`, source_location `sources/invert-the-problem.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_risk_control`/Risk control; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先确认 downside_range、liquidity_profile 和 entry_price，再给 sizing_band、constraints、next_action 或 refuse。

## Relations
```yaml
depends_on:
- circle-of-competence
delegates_to: []
constrained_by:
- invert-the-problem
complements:
- bias-self-audit
- opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Graph-to-skill distillation: `INFERRED` graph links `e_invert_margin_complements` (`Invert the problem` -> `Margin of safety sizing`, source_location `sources/invert-the-problem.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_risk_control`/Risk control; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先确认 downside_range、liquidity_profile 和 entry_price，再给 sizing_band、constraints、next_action 或 refuse。

Scenario families:
- `should_trigger` `live-price-vs-value-decision`; 当用户问“这个价格合理吗”“安全边际够不够”“值不值得买/投”并且真实在做资本配置时触发。; signals: 价格合理吗 / 安全边际够不够 / 值不值得投; boundary: 这不是纯估值讨论，而是要把前置判断落实成真实 sizing。; next: 从护城河、安全边际、定价权、管理层、能力圈五维评估，再转成 downside、liquidity 和 sizing constraints。
- `should_trigger` `panic-mispricing-check`; 当市场恐慌、价格大跌，用户在问“是不是错杀了好公司”时触发。; signals: 市场跌了很多 / 好公司可能被错杀了 / 现在是不是机会; boundary: 这里需要同时判断价值锚、回撤承受力和仓位大小，而不是只判断“公司好不好”。; next: 检查内在价值与价格差距，再落到 downside range、liquidity、position-size constraints。
- `should_trigger` `graph-inferred-link-e_invert_margin_complements`; Graph-to-skill distillation: `INFERRED` edge `e_invert_margin_complements` expands trigger language only when a live decision links `Invert the problem` and `Margin of safety sizing`.; signals: Invert the problem / Margin of safety sizing / # Invert the Problem Source Note Skill ID: invert-the-problem Primary Claim:...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: 先确认 downside_range、liquidity_profile 和 entry_price，再给 sizing_band、constraints、next_action 或 refuse。 Evidence check: verify source_location `sources/invert-the-problem.md:1-9` before expanding the trigger.
- `should_not_trigger` `short-term-trading`; 短线交易、技术指标择时不应触发。; signals: 日内交易 / MACD / KDJ; boundary: 这条 skill 面向长期资本配置，不是给短线仓位美化。
- `should_not_trigger` `pure-scale-comparison`; 只比较规模、行业地位或竞争格局但不涉及“值不值 / 下多大”的问题不应触发。; signals: 员工8000人算不算大 / 营收200亿算不算强 / 和竞争对手比谁更大; boundary: 这类问题更像一般商业分析，而不是 live sizing 决策。
- `edge_case` `private-business-or-franchise`; 奶茶加盟、线下开店、私有生意等非标准投资场景，只能部分适用。; signals: 加盟店 / 开店投200万 / 回本周期; boundary: 价值逻辑部分适用，但流动性、退出难度和资产类型与公开市场不同。; next: 先判断是否真正理解生意，再检查回本周期、流动性、退出难度和 check size，输出 partial_applicability。
- `edge_case` `angel-check-under-uncertainty`; 天使轮或创业项目，只有在能力圈和 downside 逻辑都能被说清时，才进入 sizing 讨论。; signals: 天使轮 / 商业模式大概能看懂 / 值不值得投; boundary: 理解浅、流动性差、失败不可逆时，不能因为故事好就给正常 sizing。; next: 先做能力圈检验，再评估护城河、安全边际、流动性和 sizing band，必要时降级为 tiny / small。
- `refusal` `speculative-asset-without-value-anchor`; 比特币或类似高波动、缺少稳定内在价值锚的投机场景，应拒绝给正常 sizing。; signals: 比特币 / 最近涨很多 / 值不值得买; boundary: 安全边际不适用于赌博，不能拿本框架替投机做背书。; next: 输出强警告或 refuse，不要伪造正常估值和仓位建议。

Representative cases:
- `traces/canonical/sees-candies-discipline.yaml`
- `traces/canonical/salomon-exposure-cap.yaml`
- `traces/canonical/irreversible-bet-precheck.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=18 / total=20, threshold=0.7, status=`under_evaluation`
- `synthetic_adversarial`: passed=18 / total=20, threshold=0.85, status=`under_evaluation`
- `out_of_distribution`: passed=9 / total=10, threshold=0.9, status=`under_evaluation`

关键失败模式：
- Users often present confidence but omit liquidity, reversibility, and ruin inputs.
- Users can mistake upside magnitude for permission to size aggressively without survival math.
- Concentration can look disciplined on paper while hiding unwind friction and forced-selling risk.

场景族覆盖：`should_trigger`=3，`should_not_trigger`=2，`edge_case`=2，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 2 tightened boundary signals and improved evaluation support. It now ties “市盈率 25 倍但品牌很强, 价格合理吗” and “市场恐慌是不是错杀好公司” to live sizing decisions, while refusing 规模和竞争格局比较 and 短线交易指标 questions because they are not value-and-sizing judgments.

本轮补入：
- Refinement scheduler round 2 tightened boundary signals and improved evaluation support. It now ties “市盈率 25 倍但品牌很强, 价格合理吗” and “市场恐慌是不是错杀好公司” to live sizing decisions, while refusing 规模和竞争格局比较 and 短线交易指标 questions because they are not value-and-sizing judgments.

当前待补缺口：
- Add future cases that separate temporary volatility from permanent impairment across new corpora.
- Run a real refinement_scheduler pass before describing this skill as loop-driven.

