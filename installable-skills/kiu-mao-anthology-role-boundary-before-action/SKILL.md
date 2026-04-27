---
name: kiu-mao-anthology-role-boundary-before-action
description: Use this KiU-generated action skill from Mao Anthology when the task matches `role-boundary-before-action`.
---

# Role Boundary Before Action

## Identity
```yaml
skill_id: role-boundary-before-action
title: Role Boundary Before Action
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 6
```

## Contract
```yaml
trigger:
  patterns:
  - user_deciding_whether_to_act_under_a_role_or_mandate
  - action_may_exceed_authority_or_responsibility_boundary
  - short_term_effectiveness_may_damage_long_term_order
  exclusions:
  - pure_role_definition_query
  - mechanical_workflow_template_request
  - pure_character_evaluation_request
  - pure_viewpoint_summary_request
  - legal_or_compliance_final_opinion_required
intake:
  required:
  - name: actor_role
    type: string
    description: The user's role, mandate, authorization source, and practical responsibility
      in the current situation.
  - name: proposed_action
    type: string
    description: The concrete action the user is considering before the boundary is
      checked.
  - name: authority_boundary
    type: structured
    description: What the actor is clearly allowed to do, what is ambiguous, and what
      is outside the role.
  - name: order_cost
    type: list[string]
    description: Second-order effects on trust, mandate, coordination, precedent,
      and escalation paths.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[act|act_with_boundary|ask_or_delegate|refuse]
      role_boundary: string
      authority_gap: list[string]
      order_cost: list[string]
      safe_next_action: string
      confidence: enum[low|medium|high]
      value_gain_decision: string
      value_gain_evidence: list[string]
      value_gain_risk_boundary: string
      value_gain_next_handoff: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - authorization_facts_unknown
  - legal_or_ethics_review_needed
  - role_boundary_analogy_does_not_transfer
  do_not_fire_when:
  - pure_role_definition_query
  - meeting_template_or_checklist_request
  - pure_character_evaluation_request
  - pure_viewpoint_summary_request
  - mechanical_workflow_template_request
  - no_current_action_under_consideration
```

## Rationale
`Role Boundary Before Action` is anchored in role, mandate, and consequence evidence beginning with "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:role-boundary-before-action-narrative-pattern::role-boundary-before-action]. It should fire when the user has a live action under a role, mandate, delegation, or organizational position and must decide whether acting now would exceed authority, damage trust, or create a bad precedent. `谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` adds operational context through "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:role-boundary-before-action-evidence::mao-0002]. `------------------ 注 释 〔1〕国家主义派指中国青年党，当时以其外围组织“中国国家主义青年团”的名义公开进行活动。组织...` adds operational context through "------------------ 注　　释 〔1〕国家主义派指中国青年党，当时以其外围组织“中国国家主义青年团”的名义公开进行活动。组织这个政团的是一些反动政客，他们投靠帝国主义和当权的反动派，把反对中国共产党和苏联当作职业。 〔2〕戴季陶（一八九一——一九四九），又名传贤，原籍浙江湖州，生于四川广汉。早年参加中国同盟会，从事过反对清政府和袁世凯的活动。后曾和蒋介石在上海共同经营交易所的投机事业。一九二五年随着孙中山的逝世和革命高潮"[^anchor:role-boundary-before-action-evidence::mao-0003]. The skill should not merely warn generically; it must name the role boundary, authority gap, order cost, and safe next action. It must refuse pure role-definition questions, meeting templates, and cases requiring legal/compliance final judgment rather than agentic boundary arbitration.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `湖南的农民运动，就湘中、湘南已发达的各县来说，大约分为两个时期。去年一月至九月为第一时期，即组织时期。此时期内，一月至六月为秘密活动时期，...` — 湖南的农民运动，就湘中、湘南已发达的各县来说，大约分为两个时期。去年一月至九月为第一时期，即组织时期。此时期内，一月至六月为秘密活动时期，七月至九月革命军驱逐赵恒惕⑵，为公开活动时期。此时期内，农会会员的人数总计不过三四十万，能直接领导的群众也不过百余万，在农村中还没有什么斗争，因此各界对它也没有什么批评。因为农会会员能作向导，作侦探，作挑夫，北伐军的军官们还有说几句好话的。十月至今年一月为第二时期，即革命时期。农会会员激增到二百万，能[^anchor:role-boundary-before-action-evidence::mao-0006]
- mechanism observed: `湖南的农民运动，就湘中、湘南已发达的各县来说，大约分为两个时期。去年一月至九月为第一时期，即组织时期。此时期内，一月至六月为秘密活动时期，...` contains mechanism-density `0.625`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Role Boundary Before Action` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `user_deciding_whether_to_act_under_a_role_or_mandate`
- anti-misuse boundary: `pure_role_definition_query`

### Downstream Use Check
This skill must make `Role Boundary Before Action` safe to transfer by naming the source mechanism, the current mechanism, and the boundary that would make the analogy invalid.

Minimum Pressure Pass (evidence pressure): Check whether the shared mechanism is evidenced or merely story-similar; if only names, roles, or outcomes match, return do_not_apply or demand more context. Continue only if this changes the decision, action, evidence, handoff, or review value; otherwise freeze the skill without adding process weight.

## Evidence Summary
`Role Boundary Before Action` is grounded in role-boundary evidence beginning with "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:role-boundary-before-action-narrative-pattern::role-boundary-before-action].

`谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的...` supplies another authority, mandate, or consequence anchor: "谁是我们的敌人？谁是我们的朋友？这个问题是革命的首要问题。中国过去一切革命斗争成效甚少，其基本原因就是因为不能团结真正的朋友，以攻击真正的敌人。革命党是群众的向导，在革命中未有革命党领错了路而革命不失败的。我们的革命要有不领错路和一定成功的把握，不可不注意团结我们的真正的朋友，以攻击我们的真正的敌人。我们要分辨真正的敌友，不可不将中国社会各阶级的经济地位及其对于革命的态度，作一个大概的分析。 中国社会各阶级的情况是怎样的呢？ 地主阶级和"[^anchor:role-boundary-before-action-evidence::mao-0002].

`------------------ 注 释 〔1〕国家主义派指中国青年党，当时以其外围组织“中国国家主义青年团”的名义公开进行活动。组织...` supplies another authority, mandate, or consequence anchor: "------------------ 注　　释 〔1〕国家主义派指中国青年党，当时以其外围组织“中国国家主义青年团”的名义公开进行活动。组织这个政团的是一些反动政客，他们投靠帝国主义和当权的反动派，把反对中国共产党和苏联当作职业。 〔2〕戴季陶（一八九一——一九四九），又名传贤，原籍浙江湖州，生于四川广汉。早年参加中国同盟会，从事过反对清政府和袁世凯的活动。后曾和蒋介石在上海共同经营交易所的投机事业。一九二五年随着孙中山的逝世和革命高潮"[^anchor:role-boundary-before-action-evidence::mao-0003].

These anchors support a boundary-arbitration skill only when a user is deciding whether to act under uncertain authorization. They do not support ancient-role literalism, generic hierarchy advice, or deterministic workflow execution.

Scenario-family anchor coverage: `should_trigger` `act-under-ambiguous-mandate` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::mao-0002` (There is a live action and the user needs role-boundary arbitration, not a role definition; check authority, responsibility, stakeholders, and long-term order cost.); `should_not_trigger` `role-definition-or-template-only` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::mao-0002` (No current action under uncertain authorization is being judged.); `edge_case` `urgent-but-authorization-unknown` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::mao-0002` (Urgency can justify a bounded temporary action but not silent overreach.); `refusal` `legal-or-ethics-final-opinion` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::mao-0002` (The skill can structure the boundary question but cannot replace accountable review.).

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

- Use this skill when the user asks whether they should act, intervene, decide, escalate, or refuse under a specific role, mandate, delegation, or organizational responsibility.
- Ask for actor_role, proposed_action, authority_boundary, stakeholders, urgency, and order_cost before giving a verdict.
- Output `act / act_with_boundary / ask_or_delegate / refuse`, with role_boundary, authority_gap, order_cost, and safe_next_action.
- Use `ask_or_delegate` when the action may be useful but the mandate is ambiguous or the decision properly belongs to another role.
- Use `refuse` when the user requests a template, role definition, legal final opinion, or action with unknown authorization facts.

Scenario families:
- `should_trigger` `act-under-ambiguous-mandate`; The user is considering an intervention, decision, escalation, or refusal under a role where authorization, cross-team responsibility boundaries, and long-term order costs are unclear.; signals: 我有权限推动 / 越过其他团队 / 职责边界; boundary: There is a live action and the user needs role-boundary arbitration, not a role definition; check authority, responsibility, stakeholders, and long-term order cost.; next: 列出 role_boundary、authority_gap、order_cost，并给 act_with_boundary / ask_or_delegate / refuse。
- `should_not_trigger` `role-definition-or-template-only`; Do not fire when the user only asks for a concept explanation, meeting template, or mechanical checklist.; signals: 解释一下职责 / 生成会议纪要模板 / 给我一个流程清单; boundary: No current action under uncertain authorization is being judged.
- `edge_case` `urgent-but-authorization-unknown`; Use ask_or_delegate when urgency is real but authorization facts are missing or the mandate belongs to another owner.; signals: 事情很急 / 不知道有没有授权 / 可能要先斩后奏; boundary: Urgency can justify a bounded temporary action but not silent overreach.; next: 先给 low-regret bounded action，再要求补授权或升级给 owner。
- `refusal` `legal-or-ethics-final-opinion`; Refuse to provide final legal, compliance, or ethics authorization when the facts require a responsible authority.; signals: 这合法吗 / 能不能规避合规 / 不用告诉负责人; boundary: The skill can structure the boundary question but cannot replace accountable review.; next: 说明不能最终授权，列出需提交给合规/负责人确认的问题。

Representative cases:
- `traces/canonical/role-boundary-before-action-source-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=1 / total=1, threshold=1.0, status=`pass`
- `synthetic_adversarial`: passed=1 / total=1, threshold=1.0, status=`pass`
- `out_of_distribution`: passed=1 / total=1, threshold=1.0, status=`pass`

关键失败模式：
- Do not fire on role definitions, meeting templates, or mechanical checklist requests; the skill requires a live proposed action under uncertain authorization.
- Do not give a final legal, compliance, or ethics authorization; structure the boundary question and route to accountable review.
- Do not let urgency justify silent overreach; if authorization facts are missing, use ask_or_delegate or a bounded temporary action.

场景族覆盖：`should_trigger`=1，`should_not_trigger`=1，`edge_case`=1，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 5 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Confirm whether the current trigger symbols are specific enough for production use.
- Replace smoke evaluation with real domain cases before publication.

