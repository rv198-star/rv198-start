# Bias Self Audit

## Identity
```yaml
skill_id: bias-self-audit
title: Bias Self Audit
status: published
bundle_version: 0.1.0
skill_revision: 5
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
当前挂载 trace：3 条。

代表性案例：
- `traces/canonical/us-air-regret.yaml`
- `traces/canonical/incentive-caused-delusion-audit.yaml`
- `traces/canonical/pilot-pre-mortem.yaml`

推荐输出骨架：
1. 写出当前 thesis 和 1-3 个核心假设。
2. 命名当前偏差：例如确认偏见、社会认同、身份绑定、沉没成本、时间压力、激励扭曲。
3. 给出最强反面证据或反证任务：用户接下来应该去找什么事实来推翻自己。
4. 给出 `mitigation_actions`，并标注 `audit_mode`：高风险强观点用 `full_audit`，边界态可用 `partial_review`，不适合的场景直接 `defer`。

高频触发场景包括：对投资或方案越来越确信、不想听反面意见、团队所有人都同意、已经收集了很多支持数据但担心不够客观。
若不触发，默认动作应写清楚：历史/概念查询转为普通解释，早期数据收集转为研究清单，紧急事故转为应急排障，而不是强行套用偏差审计。特别是像“先帮我收集行业数据、市场规模、增长率、主要玩家”这类信息收集的早期阶段，用户还没有形成任何观点，不需要证伪，应直接 `defer`。

## Evaluation Summary
完整的 v0.1 shared evaluation corpus 仍保持 release-scale 绑定。当前摘要覆盖 20 条真实决策、20 条 adversarial trap、10 条 OOD refusal；主要校准问题有两类：一类是低风险、可逆决策被过度审计，另一类是用户能把 thesis 讲得很顺，但说不出自己现在究竟受什么激励、身份或情绪牵引。

边界裁定需要写清楚：
- 纯信息收集阶段不触发，例如“先帮我搜集行业数据”，因为此时还没有形成明确观点。
- 像“先帮我收集新能源汽车行业的数据，市场规模、增长率、主要玩家”这种请求，本质上还是研究准备，不是偏差审计。
- 紧急故障处理不触发，例如“服务器突然宕机了，立刻判断数据库还是网络问题”，因为没有时间做系统性反证。
- 边界案例可以触发，但要看用户是否已经形成强观点；“我对比了五个方案还拿不定主意”更像犹豫，不等于确认偏见。

详见 `eval/summary.yaml`。

## Revision Summary
Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。本轮把正文从英文审计口吻改成中文 action-facing 表达，补进了和同源 benchmark 高度相关的触发语：“我觉得这肯定对”“不可能错”“反面意见我都不想听了”“大家都同意”“已经收集了很多支持数据”。

这轮同时把“找最强反面证据”“点名偏差”“给出缓释动作”写成默认输出骨架，并显式加入 `audit_mode = full_audit / partial_review / defer`。为压低误触发，本轮还写明了两类非触发例子：像“达尔文的进化论和自然选择是怎么发展出来的”这种历史/概念查询不触发；像“先帮我收集新能源汽车行业的数据，市场规模、增长率、主要玩家”这种信息收集的早期阶段也不触发，因为用户还没有形成任何观点，不需要证伪。剩余缺口是继续提高低风险场景的拒触发精度，并补出真实 loop 驱动的修订记录。详见 `iterations/revisions.yaml`。
