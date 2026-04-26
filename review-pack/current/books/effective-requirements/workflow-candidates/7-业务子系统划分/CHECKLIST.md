# 7-业务子系统划分

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
- Primary node: `principle::0016` (7 业务子系统划分)
- Supporting nodes: `case::effective-requirements-0039` (从技术实现角度来划分子系统是比较典型和常见的做法，但这种做法并不利于“业务驱动”“以用户为中心”思想的落地。理解为什么要根据业务划分子系统...), `case::effective-requirements-0040` (对于相对复杂的新开发系统而言，最常用的策略包括按业务职能分解、按产品/服务分解、双维度划分、按关键特性分解。而对于基于遗留系统开发的系统而...), `case::effective-requirements-0041` (2.按产品/服务分解 案例分析 在大家接触和使用过的网上银行中，哪家的用户体验最好呢？我发现很多人会提到招商银行，而“四大行”反而并没有太...), `case::effective-requirements-0042` (完成前两步分析之后，我们需要选择一种合适的方法来呈现这种划分。当然，我们也可以直接使用文字列出划分结果，如下所示。 体检医院管理系统由以下...), `counter-example::effective-requirements-0042` (完成前两步分析之后，我们需要选择一种合适的方法来呈现这种划分。当然，我们也可以直接使用文字列出划分结果，如下所示。 体检医院管理系统由以下...), `evidence::effective-requirements-0038` (待开发的系统有时相当复杂，涉及多种不同的业务，为了控制分析的复杂度，我们通常需要先将其分解成更小的部分。可以根据实现结构来划分，但在需求分...), `evidence::effective-requirements-0039` (从技术实现角度来划分子系统是比较典型和常见的做法，但这种做法并不利于“业务驱动”“以用户为中心”思想的落地。理解为什么要根据业务划分子系统...), `evidence::effective-requirements-0040` (对于相对复杂的新开发系统而言，最常用的策略包括按业务职能分解、按产品/服务分解、双维度划分、按关键特性分解。而对于基于遗留系统开发的系统而...), `evidence::effective-requirements-0041` (2.按产品/服务分解 案例分析 在大家接触和使用过的网上银行中，哪家的用户体验最好呢？我发现很多人会提到招商银行，而“四大行”反而并没有太...), `evidence::effective-requirements-0042` (完成前两步分析之后，我们需要选择一种合适的方法来呈现这种划分。当然，我们也可以直接使用文字列出划分结果，如下所示。 体检医院管理系统由以下...), `evidence::effective-requirements-0043` (第二部分则是对模型中的业务子系统、服务接口的简要说明。业务子系统说明分为三部分，如表7-2所示。 (1)业务子系统：填写业务子系统的名称。...), `principle::0015` (系统分解子篇)
- Supporting edges: `derives_case_signal::principle::0016->case::effective-requirements-0039` (derives_case_signal: principle::0016 -> case::effective-requirements-0039), `derives_case_signal::principle::0016->case::effective-requirements-0040` (derives_case_signal: principle::0016 -> case::effective-requirements-0040), `derives_case_signal::principle::0016->case::effective-requirements-0041` (derives_case_signal: principle::0016 -> case::effective-requirements-0041), `derives_case_signal::principle::0016->case::effective-requirements-0042` (derives_case_signal: principle::0016 -> case::effective-requirements-0042), `derives_counter_example_signal::principle::0016->counter-example::effective-requirements-0042` (derives_counter_example_signal: principle::0016 -> counter-example::effective-requirements-0042), `section-parent::principle::0015->principle::0016` (section_parent: principle::0015 -> principle::0016), `supported-by::principle::0016->evidence::effective-requirements-0038` (supported_by_evidence: principle::0016 -> evidence::effective-requirements-0038), `supported-by::principle::0016->evidence::effective-requirements-0039` (supported_by_evidence: principle::0016 -> evidence::effective-requirements-0039), `supported-by::principle::0016->evidence::effective-requirements-0040` (supported_by_evidence: principle::0016 -> evidence::effective-requirements-0040), `supported-by::principle::0016->evidence::effective-requirements-0041` (supported_by_evidence: principle::0016 -> evidence::effective-requirements-0041), `supported-by::principle::0016->evidence::effective-requirements-0042` (supported_by_evidence: principle::0016 -> evidence::effective-requirements-0042), `supported-by::principle::0016->evidence::effective-requirements-0043` (supported_by_evidence: principle::0016 -> evidence::effective-requirements-0043)
- Communities: `community::principle::0015` (系统分解子篇 Cluster), `community::principle::0016` (7 业务子系统划分 Cluster)
