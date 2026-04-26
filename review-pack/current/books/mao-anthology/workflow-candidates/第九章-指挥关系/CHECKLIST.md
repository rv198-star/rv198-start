# 第九章-指挥关系

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
- Primary node: `principle::0159` (第九章　指挥关系)
- Supporting nodes: `case::mao-0190` (抗日游击战争战略问题的最后一个问题，是指挥关系的问题。这个问题的正确解决，是游击战争顺利发展的条件之一。 游击战争的指挥方法，由于游击部队...), `counter-example::mao-0190` (抗日游击战争战略问题的最后一个问题，是指挥关系的问题。这个问题的正确解决，是游击战争顺利发展的条件之一。 游击战争的指挥方法，由于游击部队...), `evidence::mao-0190` (抗日游击战争战略问题的最后一个问题，是指挥关系的问题。这个问题的正确解决，是游击战争顺利发展的条件之一。 游击战争的指挥方法，由于游击部队...), `evidence::mao-0191` (------------------ 注 释 〔1〕长白山是中国东北边境的山脉。一九三一年九一八事变后，中国共产党领导的抗日游击队，与其他...), `framework::0143` (抗日游击战争的战略问题)
- Supporting edges: `derives_case_signal::principle::0159->case::mao-0190` (derives_case_signal: principle::0159 -> case::mao-0190), `derives_counter_example_signal::principle::0159->counter-example::mao-0190` (derives_counter_example_signal: principle::0159 -> counter-example::mao-0190), `section-parent::framework::0143->principle::0159` (section_parent: framework::0143 -> principle::0159), `supported-by::principle::0159->evidence::mao-0190` (supported_by_evidence: principle::0159 -> evidence::mao-0190), `supported-by::principle::0159->evidence::mao-0191` (supported_by_evidence: principle::0159 -> evidence::mao-0191)
- Communities: `community::principle::0159` (第九章　指挥关系 Cluster)
