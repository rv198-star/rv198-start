# 12-业务场景识别

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
- Primary node: `principle::0022` (12 业务场景识别)
- Supporting nodes: `case::effective-requirements-0058` (识别出系统相关的业务流程，然后对这些流程进行详细的分析、优化，接下来就需要识别出这些流程中存在哪些和系统相关的业务场景。这也是以业务为中心...), `case::effective-requirements-0059` (在一个信息系统中，业务流程是指不同岗位之间通过协作满足外部服务请求的过程；而业务场景则是以某岗位为主完成的、相对独立的、可以汇报的业务活动...), `case::effective-requirements-0060` (从上面的案例分析中，大家应该可以理解，这一步骤应沿着流程过程对每个活动、分支、判断点进行分析和思考：哪些业务活动需要系统支持、哪些业务活动...), `case::effective-requirements-0061` (在任何时候，Actor与Actor之间都不应直接连接。如果它们之间有协作，那么可以思考这种协作是否与系统有关。如果有关，就在它们之间加一个...), `counter-example::effective-requirements-0060` (从上面的案例分析中，大家应该可以理解，这一步骤应沿着流程过程对每个活动、分支、判断点进行分析和思考：哪些业务活动需要系统支持、哪些业务活动...), `counter-example::effective-requirements-0062` (如果你分析的是弱流程的信息系统（如POS机系统），那么可以采用“第10章业务流程识别”中的方法标识出服务请求，只不过这些服务请求不再需要进...), `evidence::effective-requirements-0058` (识别出系统相关的业务流程，然后对这些流程进行详细的分析、优化，接下来就需要识别出这些流程中存在哪些和系统相关的业务场景。这也是以业务为中心...), `evidence::effective-requirements-0059` (在一个信息系统中，业务流程是指不同岗位之间通过协作满足外部服务请求的过程；而业务场景则是以某岗位为主完成的、相对独立的、可以汇报的业务活动...), `evidence::effective-requirements-0060` (从上面的案例分析中，大家应该可以理解，这一步骤应沿着流程过程对每个活动、分支、判断点进行分析和思考：哪些业务活动需要系统支持、哪些业务活动...), `evidence::effective-requirements-0061` (在任何时候，Actor与Actor之间都不应直接连接。如果它们之间有协作，那么可以思考这种协作是否与系统有关。如果有关，就在它们之间加一个...), `evidence::effective-requirements-0062` (如果你分析的是弱流程的信息系统（如POS机系统），那么可以采用“第10章业务流程识别”中的方法标识出服务请求，只不过这些服务请求不再需要进...), `principle::0018` (功能需求主线子篇——业务支持部分)
- Supporting edges: `derives_case_signal::principle::0022->case::effective-requirements-0058` (derives_case_signal: principle::0022 -> case::effective-requirements-0058), `derives_case_signal::principle::0022->case::effective-requirements-0059` (derives_case_signal: principle::0022 -> case::effective-requirements-0059), `derives_case_signal::principle::0022->case::effective-requirements-0060` (derives_case_signal: principle::0022 -> case::effective-requirements-0060), `derives_case_signal::principle::0022->case::effective-requirements-0061` (derives_case_signal: principle::0022 -> case::effective-requirements-0061), `derives_counter_example_signal::principle::0022->counter-example::effective-requirements-0060` (derives_counter_example_signal: principle::0022 -> counter-example::effective-requirements-0060), `derives_counter_example_signal::principle::0022->counter-example::effective-requirements-0062` (derives_counter_example_signal: principle::0022 -> counter-example::effective-requirements-0062), `section-parent::principle::0018->principle::0022` (section_parent: principle::0018 -> principle::0022), `supported-by::principle::0022->evidence::effective-requirements-0058` (supported_by_evidence: principle::0022 -> evidence::effective-requirements-0058), `supported-by::principle::0022->evidence::effective-requirements-0059` (supported_by_evidence: principle::0022 -> evidence::effective-requirements-0059), `supported-by::principle::0022->evidence::effective-requirements-0060` (supported_by_evidence: principle::0022 -> evidence::effective-requirements-0060), `supported-by::principle::0022->evidence::effective-requirements-0061` (supported_by_evidence: principle::0022 -> evidence::effective-requirements-0061), `supported-by::principle::0022->evidence::effective-requirements-0062` (supported_by_evidence: principle::0022 -> evidence::effective-requirements-0062)
- Communities: `community::principle::0018` (功能需求主线子篇——业务支持部分 Cluster), `community::principle::0022` (12 业务场景识别 Cluster)
