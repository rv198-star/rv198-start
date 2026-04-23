# Margin of Safety Sizing

## Identity
```yaml
skill_id: margin-of-safety-sizing
title: Margin of Safety Sizing
status: published
bundle_version: 0.1.0
skill_revision: 5
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

## Evidence Summary
三条 canonical trace 定义了 sizing discipline。`sees-candies-discipline` 说明“伟大企业可以公道价买入”并不等于任何时候都该重仓；只有在业务韧性和 downside resilience 都足够明确时，质量才配得上 concentration，而且“尚未利用的提价能力”只能说明企业可能伟大，不能替你完成 sizing。[^trace:canonical/sees-candies-discipline.yaml] `salomon-exposure-cap` 说明暴露上限是生存工具，不是信念不足：哪怕 thesis 成立，只要杠杆、声誉风险或关联敞口会在压力下放大伤害，就应先压仓位。[^trace:canonical/salomon-exposure-cap.yaml] `irreversible-bet-precheck` 则对应“值不值得投 / 安全边际够不够”的边界情景：如果回撤后难以抽身、决策不可逆、回本周期过长、或失败一次就严重伤筋动骨，仓位必须先缩再说。[^trace:canonical/irreversible-bet-precheck.yaml]

这些证据共同支持一个判断：安全边际不是给看多观点贴一层谨慎措辞，而是把护城河、定价权、能力圈和价格判断，最后落实为不会把自己逼到被动局面的 sizing band。[^anchor:margin-source-note] [^anchor:margin-eval]

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
当前挂载 trace：3 条。

代表性案例：
- `traces/canonical/sees-candies-discipline.yaml`
- `traces/canonical/salomon-exposure-cap.yaml`
- `traces/canonical/irreversible-bet-precheck.yaml`

推荐输出骨架：
1. 先判断是否属于真实资本配置，而不是短线交易、概念查询或纯规模分析。
2. 写出前置判断：护城河、定价权、管理层、能力圈是否已基本成立；若前置条件不成立，应直接降级或拒绝。
3. 写出 downside range、流动性、相关性、回本周期、不可逆损失、备用资金来源。
4. 输出 `sizing_band`，并标注 `applicability_mode`：标准投资场景用 `full_sizing`，加盟店/非标商业投入等边界案例用 `partial_applicability`，纯投机或框架不适用时直接 `refuse`。

边界案例要区别处理：
- 奶茶加盟、线下开店等商业投入，可部分适用，但应显式输出 `partial_applicability`，并先看回本周期和退出难度。
- 比特币这类高波动、缺乏稳定内在价值锚的投机场景，不应借“安全边际”之名给出正常 sizing 建议，而应直接 `refuse` 或强警告。

## Evaluation Summary
完整的 v0.1 shared evaluation corpus 仍保持 release-scale 绑定。当前摘要覆盖 20 条真实决策、20 条 adversarial trap、10 条 OOD refusal；主失败簇仍然是“只有看多逻辑，没有 downside / liquidity / ruin math”，尤其是把“公司很好、价格不算离谱”直接误翻成“可以下大注”。

边界要求要写清楚：
- 纯概念查询，例如“什么是安全边际 / 芒格怎么定义内在价值”，不触发。
- 短线交易、指标择时不触发，这条 skill 不是给日内交易做仓位美化。
- 只分析规模与竞争格局、不涉及“值不值 / 下多大”的问题，也不应强行触发。

详见 `eval/summary.yaml`。

## Revision Summary
Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。本轮把正文改成中文 action-facing 说明，明确写出“价格合理吗 / 安全边际够不够 / 市场恐慌是不是机会 / 项目值不值得投”这类用户语言在本 skill 中如何落到 sizing，而不是把它伪装成通用估值框架。

这轮同时补上了 concept query、短线交易、纯规模比较、加盟投入、加密投机等边界裁定，并显式加入 `applicability_mode = full_sizing / partial_applicability / refuse`，目标是在不放松 workflow-vs-agentic 边界的前提下，缩小与 reference pack 在 same-scenario benchmark 上的使用落差。剩余缺口是继续加强真实案例下的 sizing 约束模板，并补出真实 loop 驱动的修订记录。详见 `iterations/revisions.yaml`。
