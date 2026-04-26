# 5-干系人分析

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
- Primary node: `principle::0012` (5 干系人分析)
- Supporting nodes: `case::effective-requirements-0033` (很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...), `case::effective-requirements-0034` (1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...), `counter-example::effective-requirements-0034` (1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...), `evidence::effective-requirements-0032` (识别出关键干系人只是第一步，选择合适的代表进行调研，分析他们的关注点、阻力点，以及满足关注点、避免阻力点所需的功能、非功能需求也是一个重要...), `evidence::effective-requirements-0033` (很多干系人分析实践都侧重于他们的关注点，也就是正需求；但实际上他们的阻力点（或称之为担心点，即负需求）分析也是十分重要的。理解“干系人负需...), `evidence::effective-requirements-0034` (1.访谈干系人 在访谈干系人之前，应该根据“分而治之提问法”策略，先制订访谈提纲，即列出要访谈的内容树。通常有三种分而治之的角度。 (1)...), `evidence::effective-requirements-0035` (下面给出了两个干系人档案示例（见表5-2和表5-3），以便大家在实践中参考。在示例中“阻力点”需求的描述形式是值得关注的，为了不影响客户阅...), `principle::0010` (3 目标/愿景分析)
- Supporting edges: `derives_case_signal::principle::0012->case::effective-requirements-0033` (derives_case_signal: principle::0012 -> case::effective-requirements-0033), `derives_case_signal::principle::0012->case::effective-requirements-0034` (derives_case_signal: principle::0012 -> case::effective-requirements-0034), `derives_counter_example_signal::principle::0012->counter-example::effective-requirements-0034` (derives_counter_example_signal: principle::0012 -> counter-example::effective-requirements-0034), `section-parent::principle::0010->principle::0012` (section_parent: principle::0010 -> principle::0012), `supported-by::principle::0012->evidence::effective-requirements-0032` (supported_by_evidence: principle::0012 -> evidence::effective-requirements-0032), `supported-by::principle::0012->evidence::effective-requirements-0033` (supported_by_evidence: principle::0012 -> evidence::effective-requirements-0033), `supported-by::principle::0012->evidence::effective-requirements-0034` (supported_by_evidence: principle::0012 -> evidence::effective-requirements-0034), `supported-by::principle::0012->evidence::effective-requirements-0035` (supported_by_evidence: principle::0012 -> evidence::effective-requirements-0035)
- Communities: `community::principle::0010` (3 目标/愿景分析 Cluster), `community::principle::0012` (5 干系人分析 Cluster)
