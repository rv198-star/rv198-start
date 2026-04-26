# 14-管理需求分析

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
- Primary node: `principle::0025` (14 管理需求分析)
- Supporting nodes: `case::effective-requirements-0071` (正如我们前面所说，信息系统的核心价值之一是支持管理，而管理支持的核心是通过管理流程事前规避风险，通过规则和审批事中控制风险，通过数据分析进...), `case::effective-requirements-0072` (要想有效地识别出系统应该支持的管控点，首先需要深入理解数据不是信息、什么是管控点两个知识点。 生活悟道场 当你要去某城市出差，查天气预报，...), `case::effective-requirements-0073` (让我感到遗憾的是，要把这里的技巧讲得更透彻已经超出我的能力范围了，只希望第14.2节中的故事、这里的逻辑树及第14.4节中的示例能够激发读...), `case::effective-requirements-0074` (案例分析（续） 针对“业务设置合理性分析”而言，显然是可以从固定数据源中用固定条件分析的，因此只需要一组报表就可以实现。小李通过一些分析，...), `counter-example::effective-requirements-0072` (要想有效地识别出系统应该支持的管控点，首先需要深入理解数据不是信息、什么是管控点两个知识点。 生活悟道场 当你要去某城市出差，查天气预报，...), `evidence::effective-requirements-0071` (正如我们前面所说，信息系统的核心价值之一是支持管理，而管理支持的核心是通过管理流程事前规避风险，通过规则和审批事中控制风险，通过数据分析进...), `evidence::effective-requirements-0072` (要想有效地识别出系统应该支持的管控点，首先需要深入理解数据不是信息、什么是管控点两个知识点。 生活悟道场 当你要去某城市出差，查天气预报，...), `evidence::effective-requirements-0073` (让我感到遗憾的是，要把这里的技巧讲得更透彻已经超出我的能力范围了，只希望第14.2节中的故事、这里的逻辑树及第14.4节中的示例能够激发读...), `evidence::effective-requirements-0074` (案例分析（续） 针对“业务设置合理性分析”而言，显然是可以从固定数据源中用固定条件分析的，因此只需要一组报表就可以实现。小李通过一些分析，...), `evidence::effective-requirements-0075` (该模板除了管控点名称，还有四个栏目，其中前两个是对其意义、人群的分析；后两个则是实现的分析。 (1)相关干系人：指出该管控点有哪些管理层用...), `principle::0024` (功能需求主线子篇——管理支持部分)
- Supporting edges: `derives_case_signal::principle::0025->case::effective-requirements-0071` (derives_case_signal: principle::0025 -> case::effective-requirements-0071), `derives_case_signal::principle::0025->case::effective-requirements-0072` (derives_case_signal: principle::0025 -> case::effective-requirements-0072), `derives_case_signal::principle::0025->case::effective-requirements-0073` (derives_case_signal: principle::0025 -> case::effective-requirements-0073), `derives_case_signal::principle::0025->case::effective-requirements-0074` (derives_case_signal: principle::0025 -> case::effective-requirements-0074), `derives_counter_example_signal::principle::0025->counter-example::effective-requirements-0072` (derives_counter_example_signal: principle::0025 -> counter-example::effective-requirements-0072), `section-parent::principle::0024->principle::0025` (section_parent: principle::0024 -> principle::0025), `supported-by::principle::0025->evidence::effective-requirements-0071` (supported_by_evidence: principle::0025 -> evidence::effective-requirements-0071), `supported-by::principle::0025->evidence::effective-requirements-0072` (supported_by_evidence: principle::0025 -> evidence::effective-requirements-0072), `supported-by::principle::0025->evidence::effective-requirements-0073` (supported_by_evidence: principle::0025 -> evidence::effective-requirements-0073), `supported-by::principle::0025->evidence::effective-requirements-0074` (supported_by_evidence: principle::0025 -> evidence::effective-requirements-0074), `supported-by::principle::0025->evidence::effective-requirements-0075` (supported_by_evidence: principle::0025 -> evidence::effective-requirements-0075)
- Communities: `community::principle::0024` (功能需求主线子篇——管理支持部分 Cluster), `community::principle::0025` (14 管理需求分析 Cluster)
