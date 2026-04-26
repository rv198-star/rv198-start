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
  - 13_业务场景分析_decision_required
  - 13_业务场景分析_evidence_grounded
  exclusions:
  - concept_query_only
  - 13_业务场景分析_outside_operating_boundary
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
  reasoning_chain_required: true
boundary:
  fails_when:
  - disconfirming_evidence_present
  - 13_业务场景分析_evidence_conflict
  do_not_fire_when:
  - scenario_missing_decision_context
  - 13_业务场景分析_boundary_unclear
```

## Rationale
当一个材料存在 high workflow certainty + high context certainty 的候选时，KiU 不能为了让 bundle 看起来有 skill 而把确定性步骤伪装成厚 skill。但默认产物仍需要一个可安装、可调用的入口，否则用户拿到的包只能审计，不能使用。`workflow-gateway` 的职责就是在这两者之间保持边界：它读取用户目标、现有上下文和可能的 workflow hint，再选择、排序或要求补充上下文；它不改写 workflow_candidates 下的固定步骤，也不把脚本逻辑偷偷并回 agentic skill。因此它是一个薄路由 skill，而不是领域判断 skill。[^anchor:workflow-gateway-primary]

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景...` — 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景描述、场景—挑战—方案两个基础思维。 生活悟道场 （接第12.2.1节生活悟道场）当我成功地激发出外婆对相机的兴趣之后，接下来我决定通过用户视角的场景描述思路来帮助她老人家掌握这个新时代的“玩具”。 “外婆，其实拍照这件事相当简单，只有三步：第一步我们要把相机打开；第二步用相机对准要拍的人或东西；第三[^anchor:workflow-gateway-case::effective-requirements-0064]
- mechanism observed: `当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景...` contains mechanism-density `0.5`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Workflow Gateway` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `13_业务场景分析_decision_required`
- anti-misuse boundary: `scenario_missing_decision_context`

User-facing role: this is a thin workflow router, not a thick judgment skill. It should select, sequence, or defer workflow candidates while keeping deterministic steps in `workflow_candidates/`.

## Evidence Summary
该 gateway 在当前生成轮次存在 workflow_script_candidate 时生成，即使同一 bundle 也包含少量真正判断密集型 skill。这说明材料仍有一部分主要交付物是确定性流程，同时也说明需要一个最小可用入口，把用户请求路由到 workflow_candidates 中的具体 `workflow.yaml` / `CHECKLIST.md`。当前候选 workflow 包括 `10-业务流程识别`, `11-业务流程分析与优化`, `12-业务场景识别`, `13-业务场景分析`, `14-管理需求分析`, `17-领域建模`, `19-质量需求分析`, `2-日常需求分析`。[^anchor:workflow-gateway-primary]

Scenario-family anchor coverage: `should_trigger` `choose-workflow-entrypoint` -> `workflow-gateway-primary` (这是路由问题，不是重新生成领域答案。); `should_trigger` `graph-inferred-link-derives_case_signal::principle::0023->case::effective-requirements-0064` -> `derives_case_signal::principle::0023->case::effective-requirements-0064` (This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.); `should_not_trigger` `exact-workflow-already-known` -> `workflow-gateway-primary` (这时应直接执行对应 workflow，而不是再做 agentic 路由。); `edge_case` `goal-too-vague-for-routing` -> `workflow-gateway-primary` (目标不足时只能 ask_clarifying_question，不能猜一个 workflow。); `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0064` -> `counter-example::effective-requirements-0064` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `agentic-judgment-request` -> `workflow-gateway-primary` (这超出薄 gateway 职责，应转交厚 skill 或要求新建 agentic candidate。).

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0023->case::effective-requirements-0064` (`13 业务场景分析` -> `当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景...`, source_location `sources/有效需求分析（第2版）.md:2510-2573`), `derives_case_signal::principle::0023->case::effective-requirements-0066` (`13 业务场景分析` -> `“这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我...`, source_location `sources/有效需求分析（第2版）.md:2596-2637`), `derives_case_signal::principle::0023->case::effective-requirements-0067` (`13 业务场景分析` -> `具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交...`, source_location `sources/有效需求分析（第2版）.md:2642-2687`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::effective-requirements-0064` at source_location `sources/有效需求分析（第2版）.md:2510-2573`, `counter-example::effective-requirements-0066` at source_location `sources/有效需求分析（第2版）.md:2596-2637`, `counter-example::effective-requirements-0067` at source_location `sources/有效需求分析（第2版）.md:2642-2687` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0018`/功能需求主线子篇——业务支持部分 Cluster, `community::principle::0023`/13 业务场景分析 Cluster; use this for related-skill handoff, not as independent evidence.

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

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0023->case::effective-requirements-0064` (`13 业务场景分析` -> `当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景...`, source_location `sources/有效需求分析（第2版）.md:2510-2573`), `derives_case_signal::principle::0023->case::effective-requirements-0066` (`13 业务场景分析` -> `“这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我...`, source_location `sources/有效需求分析（第2版）.md:2596-2637`), `derives_case_signal::principle::0023->case::effective-requirements-0067` (`13 业务场景分析` -> `具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交...`, source_location `sources/有效需求分析（第2版）.md:2642-2687`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::effective-requirements-0064` at source_location `sources/有效需求分析（第2版）.md:2510-2573`, `counter-example::effective-requirements-0066` at source_location `sources/有效需求分析（第2版）.md:2596-2637`, `counter-example::effective-requirements-0067` at source_location `sources/有效需求分析（第2版）.md:2642-2687` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0018`/功能需求主线子篇——业务支持部分 Cluster, `community::principle::0023`/13 业务场景分析 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

Scenario families:
- `should_trigger` `choose-workflow-entrypoint`; 用户拿到一组 workflow candidates，但不知道应该从哪一个开始。; signals: 应该先跑哪个流程 / 这些步骤哪个适合当前目标 / 帮我选一个工作流入口; boundary: 这是路由问题，不是重新生成领域答案。; next: 返回 selected_workflow_id、routing_reason、missing_context、next_action。
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0023->case::effective-requirements-0064`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0023->case::effective-requirements-0064` expands trigger language only when a live decision links `13 业务场景分析` and `当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景...`.; signals: 13 业务场景分析 / 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景... / 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景描述、场景—挑战...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2510-2573` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0023->case::effective-requirements-0066`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0023->case::effective-requirements-0066` expands trigger language only when a live decision links `13 业务场景分析` and `“这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我...`.; signals: 13 业务场景分析 / “这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我... / “这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我顺势做了一个总结...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2596-2637` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0023->case::effective-requirements-0067`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0023->case::effective-requirements-0067` expands trigger language only when a live decision links `13 业务场景分析` and `具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交...`.; signals: 13 业务场景分析 / 具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交... / 具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交互而非人机界面，...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2642-2687` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0023->case::effective-requirements-0068`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0023->case::effective-requirements-0068` expands trigger language only when a live decision links `13 业务场景分析` and `相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件...`.; signals: 13 业务场景分析 / 相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件... / 相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件流表示。 案例分...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2690-2697` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0023->case::effective-requirements-0069`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0023->case::effective-requirements-0069` expands trigger language only when a live decision links `13 业务场景分析` and `在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分...`.; signals: 13 业务场景分析 / 在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分... / 在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分析困难”的方法，...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2700-2725` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0064`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0064` expands trigger language only when a live decision links `13 业务场景分析` and `当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景...`.; signals: 13 业务场景分析 / 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景... / 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景描述、场景—挑战...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2510-2573` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0066`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0066` expands trigger language only when a live decision links `13 业务场景分析` and `“这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我...`.; signals: 13 业务场景分析 / “这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我... / “这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我顺势做了一个总结...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2596-2637` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0067`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0067` expands trigger language only when a live decision links `13 业务场景分析` and `具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交...`.; signals: 13 业务场景分析 / 具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交... / 具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交互而非人机界面，...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2642-2687` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0068`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0068` expands trigger language only when a live decision links `13 业务场景分析` and `相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件...`.; signals: 13 业务场景分析 / 相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件... / 相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件流表示。 案例分...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2690-2697` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0069`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0069` expands trigger language only when a live decision links `13 业务场景分析` and `在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分...`.; signals: 13 业务场景分析 / 在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分... / 在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分析困难”的方法，...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2700-2725` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0070`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0023->counter-example::effective-requirements-0070` expands trigger language only when a live decision links `13 业务场景分析` and `质量要求和约束是有局限性的，在分析一个业务场景时，还应该考虑到环境、业务特点给系统实现带来的要求和影响。通常可以从以下几个方面着手分析。 ...`.; signals: 13 业务场景分析 / 质量要求和约束是有局限性的，在分析一个业务场景时，还应该考虑到环境、业务特点给系统实现带来的要求和影响。通常可以从以下几个方面着手分析。 ... / 质量要求和约束是有局限性的，在分析一个业务场景时，还应该考虑到环境、业务特点给系统实现带来的要求和影响。通常可以从以下几个方面着手分析。 (1)性能相关：...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2728-2767` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_term_signal::principle::0023->term::ui-ue`; Graph-to-skill distillation: `INFERRED` edge `derives_term_signal::principle::0023->term::ui-ue` expands trigger language only when a live decision links `13 业务场景分析` and `UI/UE`.; signals: 13 业务场景分析 / UI/UE / 质量要求和约束是有局限性的，在分析一个业务场景时，还应该考虑到环境、业务特点给系统实现带来的要求和影响。通常可以从以下几个方面着手分析。 (1)性能相关：...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/有效需求分析（第2版）.md:2728-2767` before expanding the trigger.
- `should_not_trigger` `exact-workflow-already-known`; 用户已经明确指定 workflow id 时，不需要 gateway 再判断。; signals: 运行 10-业务流程识别 / 打开这个 workflow.yaml; boundary: 这时应直接执行对应 workflow，而不是再做 agentic 路由。
- `edge_case` `goal-too-vague-for-routing`; 用户只说想分析材料，但没有说明目标、输入或约束。; signals: 帮我分析一下 / 看看这个材料; boundary: 目标不足时只能 ask_clarifying_question，不能猜一个 workflow。; next: 列 missing_context 并提出最少澄清问题。
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0064`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0064` is a boundary probe, not a permission to fire broadly.; signals: 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景... / 当识别出业务场景之后，还应该细化业务场景的事件流，从而实现以用户视角发现系统应该提供的功能。要执行好这个任务，则应该深入理解用户视角的场景描述、场景—挑战...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:2510-2573`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0066`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0066` is a boundary probe, not a permission to fire broadly.; signals: “这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我... / “这个方案不错，我回头告诉我朋友，仔细讨论一下技术可行性。”小李显得相当开心。 “怎么样？这就是场景—挑战—方案的逻辑，你有体会了吧？”我顺势做了一个总结...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:2596-2637`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0067`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0067` is a boundary probe, not a permission to fire broadly.; signals: 具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交... / 具体的梳理方法我们已经在第13.2.2节“场景—挑战—方案”中列举过例子了，在这里不再重复，仅对一些写作要点进行补充说明。 1.重在人机交互而非人机界面，...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:2642-2687`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0068`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0068` is a boundary probe, not a permission to fire broadly.; signals: 相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件... / 相信大家从上面的案例中可以得出结论：不要用“如果……那么……”之类的结构，改用扩展事件流表示；不要用“重复执行……”之类的结构，改用子事件流表示。 案例分...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:2690-2697`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::effective-requirements-0069`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::effective-requirements-0069` is a boundary probe, not a permission to fire broadly.; signals: 在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分... / 在用例分析的方法中，用例描述通常就是细化业务步骤，但这样的写法与要实现的功能并没有形成有机的关联。因此，我们建议在此基础上通过“遍历步骤分析困难”的方法，...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/有效需求分析（第2版）.md:2700-2725`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
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

