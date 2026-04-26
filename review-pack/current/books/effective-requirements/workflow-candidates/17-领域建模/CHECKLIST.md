# 17-领域建模

Execution mode: `workflow_script`

## Objective
Run a deterministic preflight before execution when the control pattern is better served by a fixed workflow than an agentic skill.

## Scope
- [ ] Summarize the proposed change and the exact affected surface.
- [ ] Name the users, data paths, and downstream systems in scope.
- [ ] Define the abort condition before execution starts.

## Rollback
- [ ] Confirm rollback steps are written, owned, and time-bounded.
- [ ] State whether rollback has been rehearsed on a representative environment.
- [ ] Record the monitoring signal that would trigger rollback.

## Reversibility
- [ ] Identify any irreversible data writes or side effects.
- [ ] Document the safeguard for irreversible steps: backup, dual-write, holdback, or canary.
- [ ] Record the explicit go/no-go decision.

## Evidence Anchors
- Primary node: `principle::0030` (17 领域建模)
- Supporting nodes: `case::effective-requirements-0083` (在执行领域建模任务之前，首先应该深入理解“数据范围与关系”对系统的价值与影响，掌握类图基础知识。 生活悟道场 （注：本故事发生在很多年前，...), `case::effective-requirements-0085` (这4种关系中，关联关系最简单，如“客户和订单关联”；类别关系也不复杂，如“银行卡分为三种，信用卡、贷记卡、借记卡”；整体部分关系则表示“x...), `case::effective-requirements-0086` (要实现这一目标，有三个要点：一是使用用户母语（在国内就是中文）命名类和字段；二是给图配上图例；三是用业务语言来解读类图。什么叫业务语言读图...), `case::effective-requirements-0087` (在使用的时候，将采用“红→绿、黄→蓝”的顺序执行，也就是先标识过程数据，然后标识自然数据（同时考虑角色数据），最后标识描述类数据。 案例分...), `case::effective-requirements-0088` (自然数据，就是问题域中涉及的“参与者（人、公司等）”、“地点”和“东西（物品、服务）”。在识别自然数据时，还需要考虑是否需要引入“角色”。...), `counter-example::effective-requirements-0085` (这4种关系中，关联关系最简单，如“客户和订单关联”；类别关系也不复杂，如“银行卡分为三种，信用卡、贷记卡、借记卡”；整体部分关系则表示“x...), `evidence::effective-requirements-0082` (在信息系统需求分析中，数据需求主线的重点在于范围与关系，也就是哪些数据要纳入系统，它们之间的关系是什么，而领域建模正是解决这两个问题的关键...), `evidence::effective-requirements-0083` (在执行领域建模任务之前，首先应该深入理解“数据范围与关系”对系统的价值与影响，掌握类图基础知识。 生活悟道场 （注：本故事发生在很多年前，...), `evidence::effective-requirements-0084` (对于类、属性的命名方式，很多书都推荐采用CamelCase格式，但你真的理解这种格式的真谛吗？你想过这个规则是怎么来的吗？ 生活悟道场 有...), `evidence::effective-requirements-0085` (这4种关系中，关联关系最简单，如“客户和订单关联”；类别关系也不复杂，如“银行卡分为三种，信用卡、贷记卡、借记卡”；整体部分关系则表示“x...), `evidence::effective-requirements-0086` (要实现这一目标，有三个要点：一是使用用户母语（在国内就是中文）命名类和字段；二是给图配上图例；三是用业务语言来解读类图。什么叫业务语言读图...), `evidence::effective-requirements-0087` (在使用的时候，将采用“红→绿、黄→蓝”的顺序执行，也就是先标识过程数据，然后标识自然数据（同时考虑角色数据），最后标识描述类数据。 案例分...), `evidence::effective-requirements-0088` (自然数据，就是问题域中涉及的“参与者（人、公司等）”、“地点”和“东西（物品、服务）”。在识别自然数据时，还需要考虑是否需要引入“角色”。...), `evidence::effective-requirements-0089` (到这里，我们就用“彩色建模法”（或称四色建模法）完成了一次领域建模的工作。我们还可以对模型做如下一个简单的回顾。 (1)缺红色吗？显然不对...), `principle::0029` (数据需求主线子篇), `term::description` (Description), `term::role` (Role)
- Supporting edges: `derives_case_signal::principle::0030->case::effective-requirements-0083` (derives_case_signal: principle::0030 -> case::effective-requirements-0083), `derives_case_signal::principle::0030->case::effective-requirements-0085` (derives_case_signal: principle::0030 -> case::effective-requirements-0085), `derives_case_signal::principle::0030->case::effective-requirements-0086` (derives_case_signal: principle::0030 -> case::effective-requirements-0086), `derives_case_signal::principle::0030->case::effective-requirements-0087` (derives_case_signal: principle::0030 -> case::effective-requirements-0087), `derives_case_signal::principle::0030->case::effective-requirements-0088` (derives_case_signal: principle::0030 -> case::effective-requirements-0088), `derives_counter_example_signal::principle::0030->counter-example::effective-requirements-0085` (derives_counter_example_signal: principle::0030 -> counter-example::effective-requirements-0085), `derives_term_signal::principle::0030->term::description` (derives_term_signal: principle::0030 -> term::description), `derives_term_signal::principle::0030->term::role` (derives_term_signal: principle::0030 -> term::role), `section-parent::principle::0029->principle::0030` (section_parent: principle::0029 -> principle::0030), `supported-by::principle::0030->evidence::effective-requirements-0082` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0082), `supported-by::principle::0030->evidence::effective-requirements-0083` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0083), `supported-by::principle::0030->evidence::effective-requirements-0084` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0084), `supported-by::principle::0030->evidence::effective-requirements-0085` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0085), `supported-by::principle::0030->evidence::effective-requirements-0086` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0086), `supported-by::principle::0030->evidence::effective-requirements-0087` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0087), `supported-by::principle::0030->evidence::effective-requirements-0088` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0088), `supported-by::principle::0030->evidence::effective-requirements-0089` (supported_by_evidence: principle::0030 -> evidence::effective-requirements-0089)
- Communities: `community::principle::0029` (数据需求主线子篇 Cluster), `community::principle::0030` (17 领域建模 Cluster)
