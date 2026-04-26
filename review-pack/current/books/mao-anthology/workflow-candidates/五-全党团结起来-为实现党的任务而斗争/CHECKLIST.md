# 五-全党团结起来-为实现党的任务而斗争

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
- Primary node: `principle::0326` (五　全党团结起来，为实现党的任务而斗争)
- Supporting nodes: `counter-example::mao-0458` (同志们，我们已经了解了我们的任务和我们为完成这些任务所采取的政策，那末，我们应该用怎样的工作态度去执行这些政策和完成这些任务呢？ 目前国际...), `counter-example::mao-0459` (------------------ 注 释 〔1〕 一九三一年九月十八日，日本驻在中国东北境内的“关东军”进攻沈阳，九月十九日晨占领了沈...), `evidence::mao-0458` (同志们，我们已经了解了我们的任务和我们为完成这些任务所采取的政策，那末，我们应该用怎样的工作态度去执行这些政策和完成这些任务呢？ 目前国际...), `evidence::mao-0459` (------------------ 注 释 〔1〕 一九三一年九月十八日，日本驻在中国东北境内的“关东军”进攻沈阳，九月十九日晨占领了沈...), `framework::0304` (论联合政府)
- Supporting edges: `derives_counter_example_signal::principle::0326->counter-example::mao-0458` (derives_counter_example_signal: principle::0326 -> counter-example::mao-0458), `derives_counter_example_signal::principle::0326->counter-example::mao-0459` (derives_counter_example_signal: principle::0326 -> counter-example::mao-0459), `section-parent::framework::0304->principle::0326` (section_parent: framework::0304 -> principle::0326), `supported-by::principle::0326->evidence::mao-0458` (supported_by_evidence: principle::0326 -> evidence::mao-0458), `supported-by::principle::0326->evidence::mao-0459` (supported_by_evidence: principle::0326 -> evidence::mao-0459)
- Communities: `community::principle::0326` (五　全党团结起来，为实现党的任务而斗争 Cluster)
