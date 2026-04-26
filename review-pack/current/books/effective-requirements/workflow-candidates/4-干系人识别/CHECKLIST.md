# 4-干系人识别

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
- Primary node: `principle::0011` (4 干系人识别)
- Supporting nodes: `case::effective-requirements-0028` (“干系人”的英文原词是Stakeholder，在各种中文文献中还常被译作涉众(RUP)、相关人员、利益相关者、风险承担人。而在金山词霸中给...), `case::effective-requirements-0029` (如果这些部门都在同一个地方办公，那么只要将每个部门的负责人标识为关键干系人即可，如图4-4所示。 如果这些部门是分支机构，也就是不在同一个...), `case::effective-requirements-0030` (1.众多基层受影响 案例分析 某局新来了一位领导，有一天在政务大厅里看到了许多排队办理各种业务的群众，发现有一部分群众都排到了，却又到另一...), `counter-example::effective-requirements-0028` (“干系人”的英文原词是Stakeholder，在各种中文文献中还常被译作涉众(RUP)、相关人员、利益相关者、风险承担人。而在金山词霸中给...), `counter-example::effective-requirements-0029` (如果这些部门都在同一个地方办公，那么只要将每个部门的负责人标识为关键干系人即可，如图4-4所示。 如果这些部门是分支机构，也就是不在同一个...), `counter-example::effective-requirements-0030` (1.众多基层受影响 案例分析 某局新来了一位领导，有一天在政务大厅里看到了许多排队办理各种业务的群众，发现有一部分群众都排到了，却又到另一...), `evidence::effective-requirements-0027` (对于任何产品、项目而言，都会涉及各种干系人，他们有着不同的诉求、关注点，甚至存在各种冲突。在需求分析过程中，识别出关键干系人是一件十分重要...), `evidence::effective-requirements-0028` (“干系人”的英文原词是Stakeholder，在各种中文文献中还常被译作涉众(RUP)、相关人员、利益相关者、风险承担人。而在金山词霸中给...), `evidence::effective-requirements-0029` (如果这些部门都在同一个地方办公，那么只要将每个部门的负责人标识为关键干系人即可，如图4-4所示。 如果这些部门是分支机构，也就是不在同一个...), `evidence::effective-requirements-0030` (1.众多基层受影响 案例分析 某局新来了一位领导，有一天在政务大厅里看到了许多排队办理各种业务的群众，发现有一部分群众都排到了，却又到另一...), `evidence::effective-requirements-0031` (这个模板由类型、名称、说明、相关度、影响度五个栏目构成。 (1)类型：包括出资人/发起人、使用者、评价者、其他四种类型。出资人/发起人通常...), `principle::0010` (3 目标/愿景分析), `term::rup` (RUP), `term::stakeholder` (Stakeholder)
- Supporting edges: `derives_case_signal::principle::0011->case::effective-requirements-0028` (derives_case_signal: principle::0011 -> case::effective-requirements-0028), `derives_case_signal::principle::0011->case::effective-requirements-0029` (derives_case_signal: principle::0011 -> case::effective-requirements-0029), `derives_case_signal::principle::0011->case::effective-requirements-0030` (derives_case_signal: principle::0011 -> case::effective-requirements-0030), `derives_counter_example_signal::principle::0011->counter-example::effective-requirements-0028` (derives_counter_example_signal: principle::0011 -> counter-example::effective-requirements-0028), `derives_counter_example_signal::principle::0011->counter-example::effective-requirements-0029` (derives_counter_example_signal: principle::0011 -> counter-example::effective-requirements-0029), `derives_counter_example_signal::principle::0011->counter-example::effective-requirements-0030` (derives_counter_example_signal: principle::0011 -> counter-example::effective-requirements-0030), `derives_term_signal::principle::0011->term::rup` (derives_term_signal: principle::0011 -> term::rup), `derives_term_signal::principle::0011->term::stakeholder` (derives_term_signal: principle::0011 -> term::stakeholder), `section-parent::principle::0010->principle::0011` (section_parent: principle::0010 -> principle::0011), `supported-by::principle::0011->evidence::effective-requirements-0027` (supported_by_evidence: principle::0011 -> evidence::effective-requirements-0027), `supported-by::principle::0011->evidence::effective-requirements-0028` (supported_by_evidence: principle::0011 -> evidence::effective-requirements-0028), `supported-by::principle::0011->evidence::effective-requirements-0029` (supported_by_evidence: principle::0011 -> evidence::effective-requirements-0029), `supported-by::principle::0011->evidence::effective-requirements-0030` (supported_by_evidence: principle::0011 -> evidence::effective-requirements-0030), `supported-by::principle::0011->evidence::effective-requirements-0031` (supported_by_evidence: principle::0011 -> evidence::effective-requirements-0031)
- Communities: `community::principle::0010` (3 目标/愿景分析 Cluster), `community::principle::0011` (4 干系人识别 Cluster)
