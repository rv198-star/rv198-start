---
name: kiu-financial-statement-workflow-gateway
description: Use this KiU-generated action skill from Financial Statement Analysis when the task matches `workflow-gateway`.
---

# Workflow Gateway

## Identity
```yaml
skill_id: workflow-gateway
title: Workflow Gateway
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 3
```

## Contract
```yaml
trigger:
  patterns:
  - 思考题_decision_required
  - 思考题_evidence_grounded
  exclusions:
  - concept_query_only
  - 思考题_outside_operating_boundary
intake:
  required:
  - name: user_goal
    type: string
    description: The outcome the user wants from the workflow set.
  - name: available_context
    type: list
    description: Known inputs, constraints, and missing situational facts.
  - name: candidate_workflow_hint
    type: string
    description: Optional workflow id or topic the user thinks may fit.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[route_to_workflow, ask_clarifying_question, defer]
      selected_workflow_id: string
      routing_reason: string
      missing_context: list[string]
      next_action: string
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - disconfirming_evidence_present
  - 思考题_evidence_conflict
  do_not_fire_when:
  - scenario_missing_decision_context
  - 思考题_boundary_unclear
```

## Rationale
当一个材料存在 high workflow certainty + high context certainty 的候选时，KiU 不能为了让 bundle 看起来有 skill 而把确定性步骤伪装成厚 skill。但默认产物仍需要一个可安装、可调用的入口，否则用户拿到的包只能审计，不能使用。`workflow-gateway` 的职责就是在这两者之间保持边界：它读取用户目标、现有上下文和可能的 workflow hint，再选择、排序或要求补充上下文；它不改写 workflow_candidates 下的固定步骤，也不把脚本逻辑偷偷并回 agentic skill。因此它是一个薄路由 skill，而不是领域判断 skill。[^anchor:workflow-gateway-primary]

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `C2.1. 股东权益的变动金额是由当期的盈利总额减去对股东的净支付所决定的，但是，股东权益的变化额并不等于净利润（利润表中报告的）与当期对...` — C2.1. 股东权益的变动金额是由当期的盈利总额减去对股东的净支付所决定的，但是，股东权益的变化额并不等于净利润（利润表中报告的）与当期对股东的净支付之差，请问这是为什么？ C2.2. 现金股利是可以将现金支付给股东的唯一方式，请问这句话正确吗？ C2.3. 请解释净利润与归属于普通股股东的净利润之间的区别。在计算每股收益这个指标时，应使用哪一个利润概念比较合适？ C2.4. 请解释为什么一家企业的市净率会大于1.0。 C2.5. 请解[^anchor:workflow-gateway-evidence::financial-statement-0178]
- mechanism observed: `C2.1. 股东权益的变动金额是由当期的盈利总额减去对股东的净支付所决定的，但是，股东权益的变化额并不等于净利润（利润表中报告的）与当期对...` contains mechanism-density `0.625`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Workflow Gateway` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `思考题_decision_required`
- anti-misuse boundary: `scenario_missing_decision_context`

User-facing role: this is a thin workflow router, not a thick judgment skill. It should select, sequence, or defer workflow candidates while keeping deterministic steps in `workflow_candidates/`.

### Downstream Use Check
This skill must convert routing into a usable handoff: name the selected workflow, explain why it fits the current user goal, list missing context, and state when the request should escalate to a thicker judgment skill instead of staying a workflow route.

Minimum Pressure Pass (downstream pressure): After routing, ask what the user still has to invent to actually run the selected workflow; if that missing handoff is material, return ask_clarifying_question or escalate instead of pretending the route is complete. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
该 gateway 在当前生成轮次存在 workflow_script_candidate 时生成，即使同一 bundle 也包含少量真正判断密集型 skill。这说明材料仍有一部分主要交付物是确定性流程，同时也说明需要一个最小可用入口，把用户请求路由到 workflow_candidates 中的具体 `workflow.yaml` / `CHECKLIST.md`。当前候选 workflow 包括 `学习目标`, `学习能力`, `思考题`, `本章小结`, `警示案例`。[^anchor:workflow-gateway-primary]

Scenario-family anchor coverage: `should_trigger` `choose-workflow-entrypoint` -> `workflow-gateway-primary` (这是路由问题，不是重新生成领域答案。); `should_trigger` `graph-inferred-link-derives_case_signal::principle::1336->case::financial-statement-1280` -> `derives_case_signal::principle::1336->case::financial-statement-1280` (This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.); `should_not_trigger` `exact-workflow-already-known` -> `workflow-gateway-primary` (这时应直接执行对应 workflow，而不是再做 agentic 路由。); `edge_case` `goal-too-vague-for-routing` -> `workflow-gateway-primary` (目标不足时只能 ask_clarifying_question，不能猜一个 workflow。); `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-0403` -> `counter-example::financial-statement-0403` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `agentic-judgment-request` -> `workflow-gateway-primary` (这超出薄 gateway 职责，应转交厚 skill 或要求新建 agentic candidate。).

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::1336->case::financial-statement-1280` (`思考题` -> `C17.1. 如果一家企业的净经营性资产报酬率高于它的经营活动必要报酬率，那么说明这家企业的投资活动是增值的，因此它的价值应当高于其账面价...`, source_location `sources/财务报表分析_Markdown版.md:15634-15664`), `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0403` (`思考题` -> `C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价...`, source_location `sources/财务报表分析_Markdown版.md:5091-5107`), `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0484` (`思考题` -> `C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 5...`, source_location `sources/财务报表分析_Markdown版.md:6005-6039`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::financial-statement-0403` at source_location `sources/财务报表分析_Markdown版.md:5091-5107`, `counter-example::financial-statement-0484` at source_location `sources/财务报表分析_Markdown版.md:6005-6039`, `counter-example::financial-statement-0789` at source_location `sources/财务报表分析_Markdown版.md:9648-9666` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0080`/了解企业：金佰利公司（股票代码：KMB） Cluster, `community::principle::0084`/思考题 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

## Relations
```yaml
depends_on: []
delegates_to: []
constrained_by: []
complements: []
contradicts: []
```

## Usage Summary
Current trace attachments: 1.

- 把用户目标映射到一个 workflow id；如果目标不足，先问缺失上下文。
- 输出 selected_workflow_id、routing_reason、missing_context 和 next_action。
- 不要把 workflow_candidates 下的确定性步骤复制成新的厚 skill。

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::1336->case::financial-statement-1280` (`思考题` -> `C17.1. 如果一家企业的净经营性资产报酬率高于它的经营活动必要报酬率，那么说明这家企业的投资活动是增值的，因此它的价值应当高于其账面价...`, source_location `sources/财务报表分析_Markdown版.md:15634-15664`), `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0403` (`思考题` -> `C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价...`, source_location `sources/财务报表分析_Markdown版.md:5091-5107`), `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0484` (`思考题` -> `C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 5...`, source_location `sources/财务报表分析_Markdown版.md:6005-6039`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::financial-statement-0403` at source_location `sources/财务报表分析_Markdown版.md:5091-5107`, `counter-example::financial-statement-0484` at source_location `sources/财务报表分析_Markdown版.md:6005-6039`, `counter-example::financial-statement-0789` at source_location `sources/财务报表分析_Markdown版.md:9648-9666` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0080`/了解企业：金佰利公司（股票代码：KMB） Cluster, `community::principle::0084`/思考题 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

Scenario families:
- `should_trigger` `choose-workflow-entrypoint`; 用户拿到一组 workflow candidates，但不知道应该从哪一个开始。; signals: 应该先跑哪个流程 / 这些步骤哪个适合当前目标 / 帮我选一个工作流入口; boundary: 这是路由问题，不是重新生成领域答案。; next: 返回 selected_workflow_id、routing_reason、missing_context、next_action。
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::1336->case::financial-statement-1280`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::1336->case::financial-statement-1280` expands trigger language only when a live decision links `思考题` and `C17.1. 如果一家企业的净经营性资产报酬率高于它的经营活动必要报酬率，那么说明这家企业的投资活动是增值的，因此它的价值应当高于其账面价...`.; signals: 思考题 / C17.1. 如果一家企业的净经营性资产报酬率高于它的经营活动必要报酬率，那么说明这家企业的投资活动是增值的，因此它的价值应当高于其账面价... / C17.1. 如果一家企业的净经营性资产报酬率高于它的经营活动必要报酬率，那么说明这家企业的投资活动是增值的，因此它的价值应当高于其账面价值。这种说法正确...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:15634-15664` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::1336->counter-example::financial-statement-0403`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0403` expands trigger language only when a live decision links `思考题` and `C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价...`.; signals: 思考题 / C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价... / C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价值。那么这说明该...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:5091-5107` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::1336->counter-example::financial-statement-0484`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0484` expands trigger language only when a live decision links `思考题` and `C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 5...`.; signals: 思考题 / C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 5... / C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 500 指数公司的...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:6005-6039` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::1336->counter-example::financial-statement-0789`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::1336->counter-example::financial-statement-0789` expands trigger language only when a live decision links `思考题` and `C11.1. 请问，现金流量分析对公司估值来说重要吗？ C11.2. 在什么样的情况下，预测现金流量会成为一种分析工具？ C11.3. 对...`.; signals: 思考题 / C11.1. 请问，现金流量分析对公司估值来说重要吗？ C11.2. 在什么样的情况下，预测现金流量会成为一种分析工具？ C11.3. 对... / C11.1. 请问，现金流量分析对公司估值来说重要吗？ C11.2. 在什么样的情况下，预测现金流量会成为一种分析工具？ C11.3. 对一家纯粹的权益性...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:9648-9666` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::1336->counter-example::financial-statement-1054`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::1336->counter-example::financial-statement-1054` expands trigger language only when a live decision links `思考题` and `C14.1. 如果资产是按它们的公允（内在）价值计量的，分析人员预测这些资产能够产生的剩余收益必然就会等于 0。这种说法正确吗？ C14....`.; signals: 思考题 / C14.1. 如果资产是按它们的公允（内在）价值计量的，分析人员预测这些资产能够产生的剩余收益必然就会等于 0。这种说法正确吗？ C14.... / C14.1. 如果资产是按它们的公允（内在）价值计量的，分析人员预测这些资产能够产生的剩余收益必然就会等于 0。这种说法正确吗？ C14.2. 假定有一种...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:12851-12877` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::1336->counter-example::financial-statement-1453`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::1336->counter-example::financial-statement-1453` expands trigger language only when a live decision links `思考题` and `C19.1. 为什么收益率的正态分布并不能完全表示出商业投资的风险特征？ C19.2. 请对下面这种说法进行评价：要计量投资的必要报酬率，...`.; signals: 思考题 / C19.1. 为什么收益率的正态分布并不能完全表示出商业投资的风险特征？ C19.2. 请对下面这种说法进行评价：要计量投资的必要报酬率，... / C19.1. 为什么收益率的正态分布并不能完全表示出商业投资的风险特征？ C19.2. 请对下面这种说法进行评价：要计量投资的必要报酬率，就必须先计量无风...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:17800-17818` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::1336->term::boots`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::1336->term::boots` expands trigger language only when a live decision links `思考题` and `Boots`.; signals: 思考题 / Boots / C9.1. 为什么我们将资产负债表股东权益部分所报告的盈余项目称为“非清洁盈余”项目？ C9.2. 请问，为什么说如果分析人员直接使用企业所报告的净利润数...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:7634-7656` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::1336->term::capm`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::1336->term::capm` expands trigger language only when a live decision links `思考题` and `CAPM`.; signals: 思考题 / CAPM / C7.1. 为什么基本面投资者对根据资本资产定价模型（CAPM）计算出来的必要报酬率会持怀疑态度？ C7.2. 为什么估值模型就像是“镜像游戏”一样？ C...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:6565-6587` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::1336->term::djia`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::1336->term::djia` expands trigger language only when a live decision links `思考题` and `DJIA`.; signals: 思考题 / DJIA / C1.1. 基本面风险与价格风险的区别是什么？ C1.2. α 技术与 β 技术的区别是什么？ C1.3. 请对下面这种说法进行评价：要长期持有股票，因为...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:1420-1448` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::1336->term::dupont`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::1336->term::dupont` expands trigger language only when a live decision links `思考题` and `DuPont`.; signals: 思考题 / DuPont / C4.1. 作为投资股票的回报，投资者能够收到股利。因此，股票的价值应该等于预期股利的 贴现值。请问这句话是正确的吗？ C4.2. 一些分析人员强调“现金...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:4147-4171` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::1336->term::excite`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::1336->term::excite` expands trigger language only when a live decision links `思考题` and `Excite`.; signals: 思考题 / Excite / C18.1. 企业可以通过暂时增大它在本期的坏账准备来为未来储备盈利。这种说法正确吗？ C18.2. 如果本期的折旧费用较低，则意味着将来的利润会受到不良...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:16726-16762` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::1336->term::jetform-corporation`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::1336->term::jetform-corporation` expands trigger language only when a live decision links `思考题` and `Jetform Corporation`.; signals: 思考题 / Jetform Corporation / C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价值。那么这说明该...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/财务报表分析_Markdown版.md:5091-5107` before expanding the trigger.
- `should_not_trigger` `exact-workflow-already-known`; 用户已经明确指定 workflow id 时，不需要 gateway 再判断。; signals: 运行 10-业务流程识别 / 打开这个 workflow.yaml; boundary: 这时应直接执行对应 workflow，而不是再做 agentic 路由。
- `edge_case` `goal-too-vague-for-routing`; 用户只说想分析材料，但没有说明目标、输入或约束。; signals: 帮我分析一下 / 看看这个材料; boundary: 目标不足时只能 ask_clarifying_question，不能猜一个 workflow。; next: 列 missing_context 并提出最少澄清问题。
- `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-0403`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::financial-statement-0403` is a boundary probe, not a permission to fire broadly.; signals: C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价... / C5.1. 假定有信息显示某家公司在将来所有年度中的普通股权益报酬率都大于其权益资本成本率，但这家公司的股票交易价格却还是低于其每股账面价值。那么这说明该...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/财务报表分析_Markdown版.md:5091-5107`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-0484`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::financial-statement-0484` is a boundary probe, not a permission to fire broadly.; signals: C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 5... / C6.1. 请解释在企业发放股利的情况下，为什么分析人员所预测的每股收益增长往往比投资者所获得的真正价值低一些？ C6.2. 标准普尔 500 指数公司的...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/财务报表分析_Markdown版.md:6005-6039`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-0789`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::financial-statement-0789` is a boundary probe, not a permission to fire broadly.; signals: C11.1. 请问，现金流量分析对公司估值来说重要吗？ C11.2. 在什么样的情况下，预测现金流量会成为一种分析工具？ C11.3. 对... / C11.1. 请问，现金流量分析对公司估值来说重要吗？ C11.2. 在什么样的情况下，预测现金流量会成为一种分析工具？ C11.3. 对一家纯粹的权益性...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/财务报表分析_Markdown版.md:9648-9666`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-1054`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::financial-statement-1054` is a boundary probe, not a permission to fire broadly.; signals: C14.1. 如果资产是按它们的公允（内在）价值计量的，分析人员预测这些资产能够产生的剩余收益必然就会等于 0。这种说法正确吗？ C14.... / C14.1. 如果资产是按它们的公允（内在）价值计量的，分析人员预测这些资产能够产生的剩余收益必然就会等于 0。这种说法正确吗？ C14.2. 假定有一种...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/财务报表分析_Markdown版.md:12851-12877`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::financial-statement-1453`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::financial-statement-1453` is a boundary probe, not a permission to fire broadly.; signals: C19.1. 为什么收益率的正态分布并不能完全表示出商业投资的风险特征？ C19.2. 请对下面这种说法进行评价：要计量投资的必要报酬率，... / C19.1. 为什么收益率的正态分布并不能完全表示出商业投资的风险特征？ C19.2. 请对下面这种说法进行评价：要计量投资的必要报酬率，就必须先计量无风...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/财务报表分析_Markdown版.md:17800-17818`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `refusal` `agentic-judgment-request`; 用户要求直接给复杂判断结论，而不是选择 workflow。; signals: 直接告诉我战略怎么定 / 不要流程，给结论; boundary: 这超出薄 gateway 职责，应转交厚 skill 或要求新建 agentic candidate。; next: 说明 gateway 只能路由 workflow，不能替代判断密集型 skill。

Representative cases:
- `traces/workflow-gateway-routing-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=0 / total=0, threshold=0.0, status=`under_evaluation`
- `synthetic_adversarial`: passed=0 / total=0, threshold=0.0, status=`under_evaluation`
- `out_of_distribution`: passed=0 / total=0, threshold=0.0, status=`under_evaluation`

关键失败模式：
- 把 workflow 步骤内联成 agentic skill。
- 在目标和上下文不足时猜测 workflow。

场景族覆盖：`should_trigger`=13，`should_not_trigger`=1，`edge_case`=6，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 2 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 2 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Replace smoke usage review with real user routing logs before publication.
- Confirm whether each routed workflow should later gain a dedicated agentic wrapper.

