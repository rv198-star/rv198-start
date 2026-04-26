# 11-业务流程分析与优化

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
- Primary node: `principle::0021` (11 业务流程分析与优化)
- Supporting nodes: `case::effective-requirements-0053` (在标识出相关的业务流程之后，接下来的关键任务就是逐个流程进行了解与分析，绘制出流程图，并对关键流程进行适当的优化。 业务流程分析与优化任务...), `case::effective-requirements-0054` (生活悟道场 大家想想，对于一个个体户企业而言，需要进行业务流程规划吗？显然不用，因为所有事情都是他一个人负责的，自己进货、自己销售、自己发...), `case::effective-requirements-0055` (我们可以根据意图来从四种典型图表中选择合适的描述方式，如图11-8所示。 如果分析的是业务流程图，那么大部分时候我们需要强调的不仅是分工，...), `case::effective-requirements-0056` (在上面的这个案例中，我们用一个小例子简单地示范了流程图从草图到初稿的演化过程。在业务流程图绘制的过程中，还有几个要点需要提醒大家注意，具体...), `counter-example::effective-requirements-0054` (生活悟道场 大家想想，对于一个个体户企业而言，需要进行业务流程规划吗？显然不用，因为所有事情都是他一个人负责的，自己进货、自己销售、自己发...), `counter-example::effective-requirements-0056` (在上面的这个案例中，我们用一个小例子简单地示范了流程图从草图到初稿的演化过程。在业务流程图绘制的过程中，还有几个要点需要提醒大家注意，具体...), `evidence::effective-requirements-0053` (在标识出相关的业务流程之后，接下来的关键任务就是逐个流程进行了解与分析，绘制出流程图，并对关键流程进行适当的优化。 业务流程分析与优化任务...), `evidence::effective-requirements-0054` (生活悟道场 大家想想，对于一个个体户企业而言，需要进行业务流程规划吗？显然不用，因为所有事情都是他一个人负责的，自己进货、自己销售、自己发...), `evidence::effective-requirements-0055` (我们可以根据意图来从四种典型图表中选择合适的描述方式，如图11-8所示。 如果分析的是业务流程图，那么大部分时候我们需要强调的不仅是分工，...), `evidence::effective-requirements-0056` (在上面的这个案例中，我们用一个小例子简单地示范了流程图从草图到初稿的演化过程。在业务流程图绘制的过程中，还有几个要点需要提醒大家注意，具体...), `evidence::effective-requirements-0057` (下面是一个简单的业务流程描述示例，以便大家在实践中作为参考，如表11-2所示。 在“业务流程识别”任务中找到的业务流程有时并不涉及多个岗位...), `principle::0018` (功能需求主线子篇——业务支持部分)
- Supporting edges: `derives_case_signal::principle::0021->case::effective-requirements-0053` (derives_case_signal: principle::0021 -> case::effective-requirements-0053), `derives_case_signal::principle::0021->case::effective-requirements-0054` (derives_case_signal: principle::0021 -> case::effective-requirements-0054), `derives_case_signal::principle::0021->case::effective-requirements-0055` (derives_case_signal: principle::0021 -> case::effective-requirements-0055), `derives_case_signal::principle::0021->case::effective-requirements-0056` (derives_case_signal: principle::0021 -> case::effective-requirements-0056), `derives_counter_example_signal::principle::0021->counter-example::effective-requirements-0054` (derives_counter_example_signal: principle::0021 -> counter-example::effective-requirements-0054), `derives_counter_example_signal::principle::0021->counter-example::effective-requirements-0056` (derives_counter_example_signal: principle::0021 -> counter-example::effective-requirements-0056), `section-parent::principle::0018->principle::0021` (section_parent: principle::0018 -> principle::0021), `supported-by::principle::0021->evidence::effective-requirements-0053` (supported_by_evidence: principle::0021 -> evidence::effective-requirements-0053), `supported-by::principle::0021->evidence::effective-requirements-0054` (supported_by_evidence: principle::0021 -> evidence::effective-requirements-0054), `supported-by::principle::0021->evidence::effective-requirements-0055` (supported_by_evidence: principle::0021 -> evidence::effective-requirements-0055), `supported-by::principle::0021->evidence::effective-requirements-0056` (supported_by_evidence: principle::0021 -> evidence::effective-requirements-0056), `supported-by::principle::0021->evidence::effective-requirements-0057` (supported_by_evidence: principle::0021 -> evidence::effective-requirements-0057)
- Communities: `community::principle::0018` (功能需求主线子篇——业务支持部分 Cluster), `community::principle::0021` (11 业务流程分析与优化 Cluster)
