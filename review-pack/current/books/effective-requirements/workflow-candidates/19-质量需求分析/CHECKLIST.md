# 19-质量需求分析

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
- Primary node: `principle::0033` (19 质量需求分析)
- Supporting nodes: `case::effective-requirements-0093` (在一个系统中，用户看不到的绝大部分功能都在实现质量需求，但在大部分需求实践中，这部分做得很不到位。我经常在很多需求规格说明书中看到诸如“高...), `case::effective-requirements-0094` (1）安全性 我常常说，某家被偷无外乎三种原因：太有钱、太有名、门没关好；将这种思维放到系统中，也能够找到对应的关系。 (1)太有钱：系统中...), `case::effective-requirements-0095` (2.关键质量属性排序 要对识别出来的关键质量属性进行排序，最有效的方法是基于“风险曝光度”的逻辑，也就是对威胁影响度、出现频率进行分析。 ...), `case::effective-requirements-0096` (案例分析 （接第19.3.2节第一个案例分析）小赵开心地总结说：“刚才我们完成了第一步，也就是识别质量场景，接下来我们应该开始针对这个质量...), `counter-example::effective-requirements-0093` (在一个系统中，用户看不到的绝大部分功能都在实现质量需求，但在大部分需求实践中，这部分做得很不到位。我经常在很多需求规格说明书中看到诸如“高...), `evidence::effective-requirements-0092` (在信息系统需求分析中，非功能需求主线的重点在于标识出最关键的质量需求，然后针对这些质量需求属性进行细化，再与开发团队一起讨论，通过有效的技...), `evidence::effective-requirements-0093` (在一个系统中，用户看不到的绝大部分功能都在实现质量需求，但在大部分需求实践中，这部分做得很不到位。我经常在很多需求规格说明书中看到诸如“高...), `evidence::effective-requirements-0094` (1）安全性 我常常说，某家被偷无外乎三种原因：太有钱、太有名、门没关好；将这种思维放到系统中，也能够找到对应的关系。 (1)太有钱：系统中...), `evidence::effective-requirements-0095` (2.关键质量属性排序 要对识别出来的关键质量属性进行排序，最有效的方法是基于“风险曝光度”的逻辑，也就是对威胁影响度、出现频率进行分析。 ...), `evidence::effective-requirements-0096` (案例分析 （接第19.3.2节第一个案例分析）小赵开心地总结说：“刚才我们完成了第一步，也就是识别质量场景，接下来我们应该开始针对这个质量...), `evidence::effective-requirements-0097` (在质量需求分析中，“识别并排序关键质量属性”的结果是整理出系统的关键质量需求列表，然后进一步标识具体的质量场景；而“识别质量场景”的结果是...), `principle::0032` (质量需求子篇)
- Supporting edges: `derives_case_signal::principle::0033->case::effective-requirements-0093` (derives_case_signal: principle::0033 -> case::effective-requirements-0093), `derives_case_signal::principle::0033->case::effective-requirements-0094` (derives_case_signal: principle::0033 -> case::effective-requirements-0094), `derives_case_signal::principle::0033->case::effective-requirements-0095` (derives_case_signal: principle::0033 -> case::effective-requirements-0095), `derives_case_signal::principle::0033->case::effective-requirements-0096` (derives_case_signal: principle::0033 -> case::effective-requirements-0096), `derives_counter_example_signal::principle::0033->counter-example::effective-requirements-0093` (derives_counter_example_signal: principle::0033 -> counter-example::effective-requirements-0093), `section-parent::principle::0032->principle::0033` (section_parent: principle::0032 -> principle::0033), `supported-by::principle::0033->evidence::effective-requirements-0092` (supported_by_evidence: principle::0033 -> evidence::effective-requirements-0092), `supported-by::principle::0033->evidence::effective-requirements-0093` (supported_by_evidence: principle::0033 -> evidence::effective-requirements-0093), `supported-by::principle::0033->evidence::effective-requirements-0094` (supported_by_evidence: principle::0033 -> evidence::effective-requirements-0094), `supported-by::principle::0033->evidence::effective-requirements-0095` (supported_by_evidence: principle::0033 -> evidence::effective-requirements-0095), `supported-by::principle::0033->evidence::effective-requirements-0096` (supported_by_evidence: principle::0033 -> evidence::effective-requirements-0096), `supported-by::principle::0033->evidence::effective-requirements-0097` (supported_by_evidence: principle::0033 -> evidence::effective-requirements-0097)
- Communities: `community::principle::0032` (质量需求子篇 Cluster), `community::principle::0033` (19 质量需求分析 Cluster)
