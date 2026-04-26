# 论认识和实践的关系-知和行的关系

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
- Primary node: `principle::0110` (论认识和实践的关系——知和行的关系)
- Supporting nodes: `case::mao-0132` (马克思以前的唯物论，离开人的社会性，离开人的历史发展，去观察认识问题，因此不能了解认识对社会实践的依赖关系，即认识对生产和阶级斗争的依赖关...), `counter-example::mao-0131` (（一九三七年七月） > 在中国共产党内，曾经有一部分教条主义的同志长期拒绝中国革命的经验，否认“马克思主义不是教条而是行动的指南”这个真理...), `counter-example::mao-0132` (马克思以前的唯物论，离开人的社会性，离开人的历史发展，去观察认识问题，因此不能了解认识对社会实践的依赖关系，即认识对生产和阶级斗争的依赖关...), `evidence::mao-0131` (（一九三七年七月） > 在中国共产党内，曾经有一部分教条主义的同志长期拒绝中国革命的经验，否认“马克思主义不是教条而是行动的指南”这个真理...), `evidence::mao-0132` (马克思以前的唯物论，离开人的社会性，离开人的历史发展，去观察认识问题，因此不能了解认识对社会实践的依赖关系，即认识对生产和阶级斗争的依赖关...), `evidence::mao-0133` (------------------ 注 释 〔1〕见列宁《黑格尔〈逻辑学〉一书摘要》。新的译文是：“实践高于（理论的）认识，因为它不仅具...), `framework::0109` (实践论)
- Supporting edges: `derives_case_signal::principle::0110->case::mao-0132` (derives_case_signal: principle::0110 -> case::mao-0132), `derives_counter_example_signal::principle::0110->counter-example::mao-0131` (derives_counter_example_signal: principle::0110 -> counter-example::mao-0131), `derives_counter_example_signal::principle::0110->counter-example::mao-0132` (derives_counter_example_signal: principle::0110 -> counter-example::mao-0132), `section-parent::framework::0109->principle::0110` (section_parent: framework::0109 -> principle::0110), `supported-by::principle::0110->evidence::mao-0131` (supported_by_evidence: principle::0110 -> evidence::mao-0131), `supported-by::principle::0110->evidence::mao-0132` (supported_by_evidence: principle::0110 -> evidence::mao-0132), `supported-by::principle::0110->evidence::mao-0133` (supported_by_evidence: principle::0110 -> evidence::mao-0133)
- Communities: `community::principle::0110` (论认识和实践的关系——知和行的关系 Cluster)
