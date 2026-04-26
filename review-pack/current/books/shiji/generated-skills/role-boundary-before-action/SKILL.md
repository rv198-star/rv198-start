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
`Role Boundary Before Action` is anchored in role, mandate, and consequence evidence beginning with "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:role-boundary-before-action-narrative-pattern::role-boundary-before-action]. It should fire when the user has a live action under a role, mandate, delegation, or organizational position and must decide whether acting now would exceed authority, damage trust, or create a bad precedent. `昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失...` adds operational context through "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:role-boundary-before-action-evidence::shiji-0001]. `名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` adds operational context through "名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实易行，其辞难知。其术以虚无为本，以因循为用。无成埶，无常形，故能究万物之情。不为物先，不为物後，故能为万物主。有法无法，因时为业；有度无度，因物与合。故曰“圣人不朽，时变是守。虚者道之常也，因者君之纲”也。群臣并至，使各自明也。其实中其声者谓之端，实不中其声者谓之窾(kuǎn)。窾言不听，奸乃不生，贤"[^anchor:role-boundary-before-action-evidence::shiji-0002]. The skill should not merely warn generically; it must name the role boundary, authority gap, order cost, and safe next action. It must refuse pure role-definition questions, meeting templates, and cases requiring legal/compliance final judgment rather than agentic boundary arbitration.

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` — 名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实易行，其辞难知。其术以虚无为本，以因循为用。无成埶，无常形，故能究万物之情。不为物先，不为物後，故能为万物主。有法无法，因时为业；有度无度，因物与合。故曰“圣人不朽，时变是守。虚者道之常也，因者君之纲”也。群臣并至，使各自明也。其实中其声者谓之端，实不中其声者谓之窾(kuǎn)。窾言不听，奸乃不生，贤[^anchor:role-boundary-before-action-evidence::shiji-0002]
- mechanism observed: `名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` contains mechanism-density `0.875`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Role Boundary Before Action` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `user_deciding_whether_to_act_under_a_role_or_mandate`
- anti-misuse boundary: `pure_role_definition_query`

## Evidence Summary
`Role Boundary Before Action` is grounded in role-boundary evidence beginning with "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:role-boundary-before-action-narrative-pattern::role-boundary-before-action].

`昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失...` supplies another authority, mandate, or consequence anchor: "昔在颛顼，命南正重以司天，北正黎以司地。唐虞之际，绍重黎之後，使复典之，至于夏商，故重黎氏世序天地。其在周，程伯休甫其後也。当周宣王时，失其守而为司马氏。司马氏世典周史。惠襄之间，司马氏去周適(shì)晋。晋中军随会奔秦，而司马氏入少梁。 自司马氏去周適晋，分散，或在卫，或在赵，或在秦。其在卫者，相中山。在赵者，以传剑论显，蒯聩其後也。在秦者名错，与张仪争论，於是惠王使错将伐蜀，遂拔，因而守之。错孙靳，事武安君白起。而少梁更名曰夏阳。靳"[^anchor:role-boundary-before-action-evidence::shiji-0001].

`名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实...` supplies another authority, mandate, or consequence anchor: "名家苛察缴绕，使人不得反其意，专决於名而失人情，故曰“使人俭而善失真”。若夫控名责实，参伍不失，此不可不察也。 道家无为，又曰无不为，其实易行，其辞难知。其术以虚无为本，以因循为用。无成埶，无常形，故能究万物之情。不为物先，不为物後，故能为万物主。有法无法，因时为业；有度无度，因物与合。故曰“圣人不朽，时变是守。虚者道之常也，因者君之纲”也。群臣并至，使各自明也。其实中其声者谓之端，实不中其声者谓之窾(kuǎn)。窾言不听，奸乃不生，贤"[^anchor:role-boundary-before-action-evidence::shiji-0002].

These anchors support a boundary-arbitration skill only when a user is deciding whether to act under uncertain authorization. They do not support ancient-role literalism, generic hierarchy advice, or deterministic workflow execution.

Scenario-family anchor coverage: `should_trigger` `act-under-ambiguous-mandate` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::shiji-0001` (There is a live action and the user needs role-boundary arbitration, not a role definition; check authority, responsibility, stakeholders, and long-term order cost.); `should_not_trigger` `role-definition-or-template-only` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::shiji-0001` (No current action under uncertain authorization is being judged.); `edge_case` `urgent-but-authorization-unknown` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::shiji-0001` (Urgency can justify a bounded temporary action but not silent overreach.); `refusal` `legal-or-ethics-final-opinion` -> `role-boundary-before-action-narrative-pattern::role-boundary-before-action`, `role-boundary-before-action-evidence::shiji-0001` (The skill can structure the boundary question but cannot replace accountable review.).

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

