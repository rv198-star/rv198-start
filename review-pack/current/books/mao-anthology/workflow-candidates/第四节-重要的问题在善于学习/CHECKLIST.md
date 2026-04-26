# 第四节-重要的问题在善于学习

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
- Primary node: `principle::0079` (第四节　重要的问题在善于学习)
- Supporting nodes: `counter-example::mao-0096` (为什么要组织红军？因为要使用它去战胜敌人。为什么要学习战争规律？因为要使用这些规律于战争。 学习不是容易的事情，使用更加不容易。战争的学问...), `evidence::mao-0096` (为什么要组织红军？因为要使用它去战胜敌人。为什么要学习战争规律？因为要使用这些规律于战争。 学习不是容易的事情，使用更加不容易。战争的学问...), `principle::0075` (第一章　如何研究战争)
- Supporting edges: `derives_counter_example_signal::principle::0079->counter-example::mao-0096` (derives_counter_example_signal: principle::0079 -> counter-example::mao-0096), `section-parent::principle::0075->principle::0079` (section_parent: principle::0075 -> principle::0079), `supported-by::principle::0079->evidence::mao-0096` (supported_by_evidence: principle::0079 -> evidence::mao-0096)
- Communities: `community::principle::0075` (第一章　如何研究战争 Cluster), `community::principle::0079` (第四节　重要的问题在善于学习 Cluster)
