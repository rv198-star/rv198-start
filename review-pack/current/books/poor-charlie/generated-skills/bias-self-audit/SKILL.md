# Bias Self Audit

## Identity
```yaml
skill_id: bias-self-audit
title: Bias Self Audit
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 1
```

## Contract
```yaml
trigger:
  patterns:
  - user_about_to_commit_high_stakes_investment_decision
  - user_expressing_unusual_certainty_or_social_pressure
  exclusions:
  - decision_is_low_stakes_or_reversible
  - user_request_is_non_investing_decision
intake:
  required:
  - name: thesis
    type: string
    description: The current decision thesis in the user's own words.
  - name: incentives
    type: list
    description: Incentives, identity, or social forces that could bias the user.
  - name: reversibility
    type: string
    description: How costly it is to reverse the decision.
judgment_schema:
  output:
    type: structured
    schema:
      triggered_biases: list[string]
      severity: enum[low, medium, high]
      mitigation_actions: list[string]
      audit_mode: enum[full_audit, partial_review, defer]
  reasoning_chain_required: true
boundary:
  fails_when:
  - user_tries_to_use_bias_audit_as_domain_analysis
  - decision_is_too_low_stakes_to_warrant_full_audit
  do_not_fire_when:
  - decision_is_low_stakes_or_reversible
  - user_request_is_non_investing_decision
```

## Rationale
这条 skill 的作用，不是泛泛提醒“注意偏差”，而是在用户已经形成强观点、准备下注或拍板之前，强行做一次带名字的自我审计。凡是出现“我觉得这肯定是对的”“不可能错”“反面意见我都不想听了”“大家都同意这个方案”“我已经找到了很多支持证据”之类的信号，都应假设确认偏见、社会认同、身份绑定、沉没成本或激励扭曲已经开始工作。[^anchor:bias-source-note]

真正的输出不是一句“保持客观”，而是三步：先写出当前 thesis 和核心假设，再点名当前正在起作用的偏差簇，最后给出具体 countermeasure，例如去找最强反面证据、指定一个唱反调的人、延迟承诺、降低仓位、或者要求外部 base rate。用户如果说不出自己现在可能被什么误导，也说不出什么事实会推翻自己的判断，那就应默认信心已经跑在观察力前面，决策必须先降速。[^anchor:bias-eval] [^trace:canonical/us-air-regret.yaml]

## Evidence Summary
三条 canonical trace 说明“自我偏差审计”应该怎么落地。`us-air-regret` 是反面教材：如果在承诺前没有把过度自信、身份绑定和激励错位写成审计项，事后再后悔已经太晚。[^trace:canonical/us-air-regret.yaml] `incentive-caused-delusion-audit` 展示了正向模式：当报酬、面子、立场或职业身份开始影响解释时，先暂停决策、写清偏差、再谈结论。[^trace:canonical/incentive-caused-delusion-audit.yaml] `pilot-pre-mortem` 说明这条 skill 经常应接在 inversion 之后使用：先暴露失败链，再检查是不是因为确认偏见、群体共识或自我叙事，把这些风险重新遮住了。[^trace:canonical/pilot-pre-mortem.yaml]

这些证据共同指向一个结论：偏差只有在“具体偏差名 + 反证动作 + 缓释动作”都被写出来时才是可操作的；否则它只是礼貌性的心理卫生语言。[^anchor:bias-source-note] [^anchor:bias-eval]

The v0.2 seed preserves graph/source double anchoring and records the workflow-vs-agentic routing decision in `candidate.yaml`.

Scenario-family anchor coverage: `should_trigger` `high-conviction-under-pressure` -> `bias-source-note`, `bias-trace-incentive` (这已经不是普通分析，而是偏差可能开始主导判断的承诺窗口。); `should_trigger` `supportive-evidence-only` -> `bias-trace-pilot`, `bias-eval` (这是确认偏见和社会认同最容易被误当成“充分调研”的场景。); `should_not_trigger` `concept-history-or-data-collection` -> `bias-source-note` (这时用户还没有稳定 thesis，谈不上做 bias audit。); `edge_case` `option-comparison-without-hardened-thesis` -> `bias-eval` (这更像临界态，而不是已经陷入确认偏见的强观点状态。); `refusal` `urgent-incident-response` -> `bias-source-note` (情境太急，系统性搜索反证不现实，优先进入应急处理。).

Graph-to-skill distillation: `INFERRED` graph links `e_circle_bias_complements` (`Circle of competence` -> `Bias self audit`, source_location `sources/circle-of-competence.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_boundary_discipline`/Boundary discipline, `c_error_avoidance`/Error avoidance; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先写 thesis，再命名 triggered_biases，指定 strongest counter-evidence，最后给 mitigation_actions 和 next_action。

## Relations
```yaml
depends_on: []
delegates_to: []
constrained_by:
- circle-of-competence
complements:
- invert-the-problem
- margin-of-safety-sizing
- opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Graph-to-skill distillation: `INFERRED` graph links `e_circle_bias_complements` (`Circle of competence` -> `Bias self audit`, source_location `sources/circle-of-competence.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_boundary_discipline`/Boundary discipline, `c_error_avoidance`/Error avoidance; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先写 thesis，再命名 triggered_biases，指定 strongest counter-evidence，最后给 mitigation_actions 和 next_action。

Scenario families:
- `should_trigger` `high-conviction-under-pressure`; 当用户已经形成强 thesis，且带着时间压力、面子压力或身份绑定准备承诺时触发。; signals: 我觉得这肯定对 / 反面意见我都不想听了 / 明天就拍板; boundary: 这已经不是普通分析，而是偏差可能开始主导判断的承诺窗口。; next: 写出 thesis、点名 active biases、指定 strongest counter-evidence、再给 mitigation actions 和 next_action。
- `should_trigger` `supportive-evidence-only`; 当用户已经收集了大量支持证据，但没主动找最强反例时触发。; signals: 我已经找了很多支持数据 / 有没有反面证据 / 团队都同意; boundary: 这是确认偏见和社会认同最容易被误当成“充分调研”的场景。; next: 指出当前偏差簇，生成 strongest counter-evidence checklist，并给出 full_audit / partial_review / defer。
- `should_trigger` `graph-inferred-link-e_circle_bias_complements`; Graph-to-skill distillation: `INFERRED` edge `e_circle_bias_complements` expands trigger language only when a live decision links `Circle of competence` and `Bias self audit`.; signals: Circle of competence / Bias self audit / # Circle of Competence Source Note Skill ID: circle-of-competence Primary Cla...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: 先写 thesis，再命名 triggered_biases，指定 strongest counter-evidence，最后给 mitigation_actions 和 next_action。 Evidence check: verify source_location `sources/circle-of-competence.md:1-9` before expanding the trigger.
- `should_not_trigger` `concept-history-or-data-collection`; 纯概念解释、历史回顾或早期信息收集不应触发。; signals: 达尔文是怎么提出进化论的 / 先帮我收集行业数据 / 市场规模和主要玩家有哪些; boundary: 这时用户还没有稳定 thesis，谈不上做 bias audit。
- `edge_case` `option-comparison-without-hardened-thesis`; 用户在几个方案之间犹豫，但还没有锁定单一 thesis 时，只做 partial review。; signals: 还拿不定主意 / 对比了几个方案 / 感觉都有道理; boundary: 这更像临界态，而不是已经陷入确认偏见的强观点状态。; next: 先确认 thesis 是否真的形成，再决定 partial_review 还是 defer，不要直接上 full_audit。
- `refusal` `urgent-incident-response`; 紧急故障排查、事故处置不应强行套用偏差审计。; signals: 服务器突然宕机 / 先判断数据库还是网络 / 现在必须立刻处理; boundary: 情境太急，系统性搜索反证不现实，优先进入应急处理。; next: 明确转为应急排障或普通分析，不要伪装成 bias audit。

Representative cases:
- `traces/canonical/us-air-regret.yaml`
- `traces/canonical/incentive-caused-delusion-audit.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=20 / total=20, threshold=0.7, status=`pass`
- `synthetic_adversarial`: passed=20 / total=20, threshold=0.85, status=`pass`
- `out_of_distribution`: passed=10 / total=10, threshold=0.9, status=`pass`

关键失败模式：
- Low-stakes cases can trigger false positives unless reversibility is represented explicitly.
- Fluent thesis presentation can hide identity or incentive pressure unless the distortion is named directly.
- Social proof and sunk cost can survive casual reflection unless the audit demands a concrete mitigation action.

场景族覆盖：`should_trigger`=3，`should_not_trigger`=1，`edge_case`=1，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。本轮把正文从英文审计口吻改成中文 action-facing 表达，补进了和同源 benchmark 高度相关的触发语：“我觉得这肯定对”“不可能错”“反面意见我都不想听了”“大家都同意”“已经收集了很多支持数据”。

这轮同时把“找最强反面证据”“点名偏差”“给出缓释动作”写成默认输出骨架，并显式加入 `audit_mode = full_audit / partial_review / defer`。为压低误触发，本轮还写明了两类非触发例子：像“达尔文的进化论和自然选择是怎么发展出来的”这种历史/概念查询不触发；像“先帮我收集新能源汽车行业的数据，市场规模、增长率、主要玩家”这种信息收集的早期阶段也不触发，因为用户还没有形成任何观点，不需要证伪。剩余缺口是继续提高低风险场景的拒触发精度，并补出真实 loop 驱动的修订记录。详见 `iterations/revisions.yaml`。

本轮补入：
- Added direct trigger phrases such as "不可能错", "反面意见我都不想听了", "大家都同意", and "已经收集了很多支持数据".
- Reworked the usage summary around thesis naming, bias naming, counter-evidence search, and mitigation actions.
- Clarified non-trigger boundaries for early-stage data collection, urgent incidents, and indecision without a formed thesis.

当前待补缺口：
- Continue tightening low-stakes refusal calibration without weakening the current published contract.
- Run a real refinement_scheduler pass before describing this skill as loop-driven.
