# 第三节-战略退却

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
- Primary node: `principle::0089` (第三节　战略退却)
- Supporting nodes: `case::mao-0106` (当时的情况是弱国抵抗强国。文中指出了战前的政治准备——取信于民，叙述了利于转入反攻的阵地——长勺，叙述了利于开始反攻的时机——彼竭我盈之时...), `counter-example::mao-0105` (战略退却，是劣势军队处在优势军队进攻面前，因为顾到不能迅速地击破其进攻，为了保存军力，待机破敌，而采取的一个有计划的战略步骤。可是，军事冒...), `counter-example::mao-0106` (当时的情况是弱国抵抗强国。文中指出了战前的政治准备——取信于民，叙述了利于转入反攻的阵地——长勺，叙述了利于开始反攻的时机——彼竭我盈之时...), `evidence::mao-0105` (战略退却，是劣势军队处在优势军队进攻面前，因为顾到不能迅速地击破其进攻，为了保存军力，待机破敌，而采取的一个有计划的战略步骤。可是，军事冒...), `evidence::mao-0106` (当时的情况是弱国抵抗强国。文中指出了战前的政治准备——取信于民，叙述了利于转入反攻的阵地——长勺，叙述了利于开始反攻的时机——彼竭我盈之时...), `principle::0086` (第五章　战略防御)
- Supporting edges: `derives_case_signal::principle::0089->case::mao-0106` (derives_case_signal: principle::0089 -> case::mao-0106), `derives_counter_example_signal::principle::0089->counter-example::mao-0105` (derives_counter_example_signal: principle::0089 -> counter-example::mao-0105), `derives_counter_example_signal::principle::0089->counter-example::mao-0106` (derives_counter_example_signal: principle::0089 -> counter-example::mao-0106), `section-parent::principle::0086->principle::0089` (section_parent: principle::0086 -> principle::0089), `supported-by::principle::0089->evidence::mao-0105` (supported_by_evidence: principle::0089 -> evidence::mao-0105), `supported-by::principle::0089->evidence::mao-0106` (supported_by_evidence: principle::0089 -> evidence::mao-0106)
- Communities: `community::principle::0086` (第五章　战略防御 Cluster), `community::principle::0089` (第三节　战略退却 Cluster)
