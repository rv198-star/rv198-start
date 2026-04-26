# 10-业务流程识别

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
- Primary node: `principle::0020` (10 业务流程识别)
- Supporting nodes: `case::effective-requirements-0048` (正如我们前面所说，信息系统的核心价值之一是支持业务，而业务支持的核心是对业务流程的固化、优化和重构。在进行需求分析时，识别出相关的业务流程...), `case::effective-requirements-0049` (或许你已经从中领会到“业务流程图只允许有一个起点，但可以有多个终点”背后的原因了。 识别服务请求这一源头只是手段，我们的任务是识别出业务流...), `case::effective-requirements-0050` (在上面这个案例中，我们使用的识别思路如图10-3所示，先识别出外部客户，然后分别思考主业务流程、变体业务流程和支撑业务流程。 主业务流程体...), `case::effective-requirements-0051` (另外，要注意的是，主、变、支流程的分类是为了帮助大家更好地识别流程，不要陷入它属于哪类流程的细节争论中；而且识别出来后还要判断其是不是端到...), `case::effective-requirements-0052` (案例分析（续3） 在大家识别完所有业务流程之后，应按主营业务/频率两维度进行分析，以判断业务流程的优先级。 (1)住宿流程：主营业务、频率...), `counter-example::effective-requirements-0048` (正如我们前面所说，信息系统的核心价值之一是支持业务，而业务支持的核心是对业务流程的固化、优化和重构。在进行需求分析时，识别出相关的业务流程...), `counter-example::effective-requirements-0051` (另外，要注意的是，主、变、支流程的分类是为了帮助大家更好地识别流程，不要陷入它属于哪类流程的细节争论中；而且识别出来后还要判断其是不是端到...), `counter-example::effective-requirements-0052` (案例分析（续3） 在大家识别完所有业务流程之后，应按主营业务/频率两维度进行分析，以判断业务流程的优先级。 (1)住宿流程：主营业务、频率...), `evidence::effective-requirements-0048` (正如我们前面所说，信息系统的核心价值之一是支持业务，而业务支持的核心是对业务流程的固化、优化和重构。在进行需求分析时，识别出相关的业务流程...), `evidence::effective-requirements-0049` (或许你已经从中领会到“业务流程图只允许有一个起点，但可以有多个终点”背后的原因了。 识别服务请求这一源头只是手段，我们的任务是识别出业务流...), `evidence::effective-requirements-0050` (在上面这个案例中，我们使用的识别思路如图10-3所示，先识别出外部客户，然后分别思考主业务流程、变体业务流程和支撑业务流程。 主业务流程体...), `evidence::effective-requirements-0051` (另外，要注意的是，主、变、支流程的分类是为了帮助大家更好地识别流程，不要陷入它属于哪类流程的细节争论中；而且识别出来后还要判断其是不是端到...), `evidence::effective-requirements-0052` (案例分析（续3） 在大家识别完所有业务流程之后，应按主营业务/频率两维度进行分析，以判断业务流程的优先级。 (1)住宿流程：主营业务、频率...), `principle::0018` (功能需求主线子篇——业务支持部分)
- Supporting edges: `derives_case_signal::principle::0020->case::effective-requirements-0048` (derives_case_signal: principle::0020 -> case::effective-requirements-0048), `derives_case_signal::principle::0020->case::effective-requirements-0049` (derives_case_signal: principle::0020 -> case::effective-requirements-0049), `derives_case_signal::principle::0020->case::effective-requirements-0050` (derives_case_signal: principle::0020 -> case::effective-requirements-0050), `derives_case_signal::principle::0020->case::effective-requirements-0051` (derives_case_signal: principle::0020 -> case::effective-requirements-0051), `derives_case_signal::principle::0020->case::effective-requirements-0052` (derives_case_signal: principle::0020 -> case::effective-requirements-0052), `derives_counter_example_signal::principle::0020->counter-example::effective-requirements-0048` (derives_counter_example_signal: principle::0020 -> counter-example::effective-requirements-0048), `derives_counter_example_signal::principle::0020->counter-example::effective-requirements-0051` (derives_counter_example_signal: principle::0020 -> counter-example::effective-requirements-0051), `derives_counter_example_signal::principle::0020->counter-example::effective-requirements-0052` (derives_counter_example_signal: principle::0020 -> counter-example::effective-requirements-0052), `section-parent::principle::0018->principle::0020` (section_parent: principle::0018 -> principle::0020), `supported-by::principle::0020->evidence::effective-requirements-0048` (supported_by_evidence: principle::0020 -> evidence::effective-requirements-0048), `supported-by::principle::0020->evidence::effective-requirements-0049` (supported_by_evidence: principle::0020 -> evidence::effective-requirements-0049), `supported-by::principle::0020->evidence::effective-requirements-0050` (supported_by_evidence: principle::0020 -> evidence::effective-requirements-0050), `supported-by::principle::0020->evidence::effective-requirements-0051` (supported_by_evidence: principle::0020 -> evidence::effective-requirements-0051), `supported-by::principle::0020->evidence::effective-requirements-0052` (supported_by_evidence: principle::0020 -> evidence::effective-requirements-0052)
- Communities: `community::principle::0018` (功能需求主线子篇——业务支持部分 Cluster), `community::principle::0020` (10 业务流程识别 Cluster)
