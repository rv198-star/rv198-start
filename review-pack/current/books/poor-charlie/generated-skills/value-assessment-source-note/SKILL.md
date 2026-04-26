# Value Assessment

## Identity
```yaml
skill_id: value-assessment-source-note
title: Value Assessment
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 1
```

## Contract
```yaml
trigger:
  patterns:
  - user_judging_price_vs_value_before_position_size
  - user_testing_whether_business_has_defensible_value_anchor
  exclusions:
  - user_request_is_short_term_trading
  - user_request_is_pure_scale_comparison
  - user_request_is_concept_query_without_live_decision
intake:
  required:
  - name: current_price_or_valuation_claim
    type: string
    description: Current market price, quoted valuation, or the user's mispricing
      claim.
  - name: value_anchor_hypothesis
    type: string
    description: Why the user believes the business can compound value or why the
      valuation may be unjustified.
  - name: business_quality_drivers
    type: structured
    description: Moat, pricing power, reinvestment economics, management quality,
      and circle-of-competence signals.
judgment_schema:
  output:
    type: structured
    schema:
      value_view: enum[undervalued, fairly_priced, overvalued, no_value_anchor]
      key_drivers: list[string]
      rationale: string
      applicability_mode: enum[full_valuation, partial_applicability, refuse]
      next_action: string
      decline_reason: string
      first_next_action: string
      handoff_condition: string
      next_step: enum[delegate_to_sizing, monitor_only, decline]
  reasoning_chain_required: true
boundary:
  fails_when:
  - user_cannot_state_business_value_anchor
  - user_requests_position_size_before_value_judgment_is_stable
  do_not_fire_when:
  - user_request_is_short_term_trading
  - user_request_is_pure_scale_comparison
  - user_request_is_concept_query_without_live_decision
```

## Rationale
这条 parent skill 先回答“值不值”，而不是直接跳到“下多大”。当用户说“品牌很强但价格不便宜，这个价到底值不值”“市场大跌是不是把好公司错杀了”“这种公司和其他公司到底差在哪”“这个天使轮估值有没有道理”时，真正需要先建立的是价值锚点，而不是仓位动作。`n_margin_principle` 的原始原则提醒我们，安全边际判断本身就隐含了“先用价值挑战价格”的顺序；如果价值锚点没有站稳，任何 sizing 都只是把模糊判断伪装成纪律。[^anchor:value-assessment-source-note-n_margin_principle] [^anchor:value-assessment-source-note-n_margin_see_candies_trace]

因此这条 skill 的核心职责是把用户的语言拆成五个价值判断维度：护城河是否真实、定价权是否可持续、资本回报与再投资路径是否清楚、管理层是否会把优势转成长期价值、以及这个判断是否真的在能力圈内。只有这五层先站住，才谈得上“当前价格相对价值是低估、公允还是高估”；如果用户接着问仓位大小，再明确交给 `margin-of-safety-sizing`，而不是让 valuation 偷偷吞掉 sizing discipline。[^trace:canonical/sees-candies-discipline.yaml]

这条 skill 还必须守住两条硬边界。第一，遇到比特币这类缺少稳定业务价值锚点的投机场景，不能为了看起来有用就硬做估值，而是应直接给出 `no_value_anchor` 与 `refuse`。[^trace:canonical/crypto-rejection.yaml] 第二，遇到短线交易、技术指标择时、纯规模比较、纯概念查询时，不应把任何“好公司分析”都冒充成价值判断。只有在用户真的面对 price-vs-value 决策，或者在问 quoted valuation 是否站得住时，这条 skill 才应该 firing。

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `Invert the problem` — # Invert the Problem Source Note Skill ID: invert-the-problem Primary Claim: When the success path is vague, list the failure modes first and remove them in order. Evidence: - Inversion is most useful when the user is pl[^anchor:value-assessment-source-note-n_invert_principle]
- mechanism observed: `Invert the problem` contains mechanism-density `0.125`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Value Assessment` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `user_judging_price_vs_value_before_position_size`
- anti-misuse boundary: `user_request_is_short_term_trading`

## Evidence Summary
这条 companion candidate 绑定在与 `margin-of-safety-sizing` 相同的 graph support 上，但承担更窄也更靠前的 parent 职责：先建立价值锚点，再决定是否把资本配置问题交给 sizing。[^anchor:value-assessment-source-note-seed-support] [^anchor:value-assessment-source-note-n_margin_principle]

`traces/canonical/sees-candies-discipline.yaml` 支持“伟大企业与普通企业为何值不同价”的判断：护城河、定价权和尚未利用的提价能力，解释的是 business quality 如何转成更高质量的价值，而不是直接授权大仓位。[^trace:canonical/sees-candies-discipline.yaml] `traces/canonical/unused-pricing-power-signal.yaml` 进一步把这个判断钉死到 `pricing power`：芒格所强调的“尚未利用的提价能力”不是泛泛的品牌好，而是企业在不伤害客户留存的情况下还能继续把价值转成价格的能力，因此它会直接抬高 value anchor 的质量，而不是只让人觉得“这公司不错”。[^trace:canonical/unused-pricing-power-signal.yaml] `traces/canonical/newspaper-sizing-discipline.yaml` 提醒市场恐慌或局部 franchise 机会不自动等于低估，仍要先检查价值锚点是否稳定，再决定 monitor 还是 handoff。[^trace:canonical/newspaper-sizing-discipline.yaml]

`traces/canonical/crypto-rejection.yaml` 则提供 refusal 证据：当标的没有稳定的业务价值基础时，正确动作不是编造 valuation story，而是明确输出 `no_value_anchor`。[^trace:canonical/crypto-rejection.yaml]

Scenario-family anchor coverage: `should_trigger` `price-vs-value-before-sizing` -> `value-assessment-source-note-n_margin_principle`, `value-assessment-source-note-n_margin_see_candies_trace` (这是典型的 price-vs-value 判断，应该先建立价值锚点，再决定是否交给 sizing。); `should_trigger` `panic-created-mispricing` -> `value-assessment-source-note-n_margin_principle`, `value-assessment-source-note-n_salomon_cap_trace` (这里先要判断 price 是否脱离 value，而不是直接给仓位。); `should_not_trigger` `short-term-trading-or-scale-only` -> `value-assessment-source-note-n_margin_principle` (这些场景要么不需要长期价值判断，要么只是纯概念查询，不是在面临一个需要做价值判断的真实投资决策。); `edge_case` `private-business-or-angel` -> `value-assessment-source-note-n_margin_principle`, `value-assessment-source-note-n_salomon_cap_trace` (这些场景没有稳定公开市场参照，valuation 只能先到 partial_applicability。); `refusal` `speculative-asset-without-value-anchor` -> `value-assessment-source-note-n_margin_principle` (没有稳定价值锚点时，valuation parent 的责任是拒绝，而不是编造高深理由。).

Graph-to-skill distillation: `INFERRED` graph links `e_invert_margin_complements` (`Invert the problem` -> `Margin of safety sizing`, source_location `sources/invert-the-problem.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_risk_control`/Risk control; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先判断 value_anchor 是否成立，再看 price_or_valuation 是否脱离 business economics，最后 handoff 到 sizing 或 decline。

## Relations
```yaml
depends_on:
- circle-of-competence
delegates_to:
- margin-of-safety-sizing
constrained_by:
- invert-the-problem
complements:
- bias-self-audit
- opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 4.

- 当用户问“这个价格合理吗”“值不值这个价”“是不是高估/低估了”时，先做价值判断，再决定是否把 sizing 交给后续 skill。
- 代表性触发语包括“品牌很强但价格不便宜”“市场大跌是不是错杀了好公司”“这种公司和其他公司到底差在哪”“这个天使轮估值有没有道理”。
- 对“市盈率25倍不算便宜，但品牌很强，这个价格合理吗？安全边际够不够？”这类问题，应激活 value-assessment，并从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估，先给 value_view，再决定是否交给 sizing。
- 对公开市场股票，要明确从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估，再判断当前价格与内在价值的差距。
- 对“最近市场跌了很多，好公司是不是被错杀了，现在是不是机会？”这类问题，应激活 value-assessment，并引导用户在市场恐慌中冷静评估内在价值与价格的差距，先确认是否真的出现安全边际，再决定是 monitor_only 还是 delegate_to_sizing。
- 当市场恐慌、价格大跌时，要引导用户冷静评估内在价值与价格的差距，先确认是否真的出现安全边际，再决定是 monitor_only 还是 delegate_to_sizing。
- 对“这家公司看起来护城河很宽，产品提价客户也不会跑，这种公司和其他公司到底差在哪？”这类问题，应重点分析定价权，并明确指出芒格认为“尚未利用的提价能力”是伟大企业最可靠的标志之一，因为它说明企业仍能把价值继续转成价格而不伤害竞争地位。
- 当用户问“这种公司和其他公司到底差在哪”时，不要泛泛而谈；要明确写出芒格认为“尚未利用的提价能力”是伟大企业最可靠的标志之一，并说明它如何转成更强的价值锚点。
- 对“朋友推荐一个创业项目让我投天使轮，商业模式大概能看懂，但不确定值不值得投”这类问题，应先做能力圈检验（是否真正理解这门生意），再评估护城河、安全边际、现金流逻辑与回本路径，最后判断 quoted valuation 是否可信。
- 对加盟店、私有生意、天使轮等边界场景，默认使用 partial_applicability：先做能力圈检验（是否真正理解这门生意），再评估护城河、安全边际、现金流逻辑与回本路径，最后判断 quoted valuation 是否站得住。
- 对比特币或类似缺少稳定业务价值锚点的投机场景，明确写出“安全边际不适用于赌博”，输出 no_value_anchor、refuse 与 decline，不要伪造正常估值。
- 如果用户真正的问题已经转成“该下多大仓位”“最大能投多少”，显式 delegate 给 margin-of-safety-sizing，而不是把 sizing 混进 valuation 里。
- 不要在短线交易、技术指标择时、纯规模比较或概念解释里触发这条 skill；纯规模和竞争格局问题应转给 scale-advantage-analysis。
- 输出至少要包含 value_view、key_drivers、applicability_mode、next_step 和一个具体 next action。

Graph-to-skill distillation: `INFERRED` graph links `e_invert_margin_complements` (`Invert the problem` -> `Margin of safety sizing`, source_location `sources/invert-the-problem.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_risk_control`/Risk control; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先判断 value_anchor 是否成立，再看 price_or_valuation 是否脱离 business economics，最后 handoff 到 sizing 或 decline。

Scenario families:
- `should_trigger` `price-vs-value-before-sizing`; 当用户在真实投资决策里问“价格合理吗”“值不值这个价”时，应先激活 valuation parent，而不是直接进入 sizing。; signals: 值不值这个价 / 价格合理吗 / 是不是高估了; boundary: 这是典型的 price-vs-value 判断，应该先建立价值锚点，再决定是否交给 sizing。; next: 应激活 value-assessment，并从护城河、安全边际、定价权、管理层、能力圈五个维度系统评估；先给出 value_view，再明确 monitor_only / delegate_to_sizing / decline。
- `should_trigger` `panic-created-mispricing`; 当市场恐慌、价格大跌，用户在问好公司是否被错杀时，应先判断价值锚点是否仍然成立。; signals: 市场跌了很多 / 是不是错杀 / 现在是不是机会; boundary: 这里先要判断 price 是否脱离 value，而不是直接给仓位。; next: 应激活 value-assessment，并引导用户在市场恐慌中冷静评估内在价值与价格的差距，确认是否出现安全边际，再决定 delegate_to_sizing 或 monitor_only。
- `should_trigger` `great-business-vs-ordinary-business`; 当用户追问“这家公司和其他公司到底差在哪”且语义落在护城河、定价权、提价能力上时，应激活 valuation parent。; signals: 护城河很宽 / 提价客户也不会跑 / 和其他公司差在哪; boundary: 这不是纯规模比较，而是在追问 business quality 如何转成更高质量的价值。; next: 应重点分析定价权，并明确指出芒格认为“尚未利用的提价能力”是伟大企业最可靠的标志之一，因为它说明企业仍能把价值继续转成价格而不伤害竞争地位。
- `should_trigger` `graph-inferred-link-e_invert_margin_complements`; Graph-to-skill distillation: `INFERRED` edge `e_invert_margin_complements` expands trigger language only when a live decision links `Invert the problem` and `Margin of safety sizing`.; signals: Invert the problem / Margin of safety sizing / # Invert the Problem Source Note Skill ID: invert-the-problem Primary Claim:...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: 先判断 value_anchor 是否成立，再看 price_or_valuation 是否脱离 business economics，最后 handoff 到 sizing 或 decline。 Evidence check: verify source_location `sources/invert-the-problem.md:1-9` before expanding the trigger.
- `should_not_trigger` `short-term-trading-or-scale-only`; 短线交易、技术指标择时、纯规模比较或纯概念解释不应触发这条 skill；纯规模和竞争格局问题应使用 scale-advantage-analysis。; signals: 日内交易 / MACD / 员工8000人算不算大; boundary: 这些场景要么不需要长期价值判断，要么只是纯概念查询，不是在面临一个需要做价值判断的真实投资决策。
- `edge_case` `private-business-or-angel`; 加盟店、私有生意、天使轮等边界案例可部分适用，但必须先做能力圈与价值锚点校验。; signals: 加盟店 / 天使轮 / 这个估值有没有道理; boundary: 这些场景没有稳定公开市场参照，valuation 只能先到 partial_applicability。; next: 应先做能力圈检验（是否真正理解这门生意），再评估护城河、安全边际、现金流与回本路径，最后判断 quoted valuation 是否可信，并决定是否 handoff 给 sizing。
- `refusal` `speculative-asset-without-value-anchor`; 对缺少稳定业务价值锚点的投机场景，应直接拒绝伪估值。; signals: 比特币 / 最近涨很多 / 值不值得买; boundary: 没有稳定价值锚点时，valuation parent 的责任是拒绝，而不是编造高深理由。; next: 明确写出“安全边际不适用于赌博”，并指出芒格本人对加密货币持强烈否定态度；输出 no_value_anchor、refuse 与 decline，不要 handoff 给 sizing。

Representative cases:
- `traces/canonical/sees-candies-discipline.yaml`
- `traces/canonical/unused-pricing-power-signal.yaml`
- `traces/canonical/newspaper-sizing-discipline.yaml`
- `traces/canonical/crypto-rejection.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pending`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=0.7, status=`under_evaluation`
- `synthetic_adversarial`: passed=1 / total=1, threshold=0.85, status=`under_evaluation`
- `out_of_distribution`: passed=1 / total=1, threshold=0.9, status=`under_evaluation`

关键失败模式：
- Valuation can look persuasive while still lacking a defensible business-value anchor.
- The parent skill must delegate to sizing once the user asks for capital commitment size.
- The skill must refuse short-term trading and no-value-anchor speculation instead of fabricating a valuation answer.

场景族覆盖：`should_trigger`=4，`should_not_trigger`=1，`edge_case`=1，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Initial v0.5.1 parent-skill topology repair. This candidate was added so KiU can answer value-anchor questions before handing real position-size questions to `margin-of-safety-sizing`, instead of forcing the sizing specialist to impersonate a full valuation skill.


本轮补入：
- Added explicit parent/specialist split for the margin family.
- Reused existing canonical valuation-support and refusal traces in the generated usage layer.

当前待补缺口：
- Add real evaluation cases dedicated to value-anchor judgments.
- Verify that value-assessment keeps delegating to sizing instead of swallowing capital-allocation questions.
