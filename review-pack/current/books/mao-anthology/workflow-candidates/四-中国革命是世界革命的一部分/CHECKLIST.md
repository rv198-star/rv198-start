# 四-中国革命是世界革命的一部分

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
- Primary node: `principle::0242` (四　中国革命是世界革命的一部分)
- Supporting nodes: `counter-example::mao-0296` (中国革命的历史特点是分为民主主义和社会主义两个步骤，而其第一步现在已不是一般的民主主义，而是中国式的、特殊的、新式的民主主义，而是新民主主...), `counter-example::mao-0298` (由此可见，有两种世界革命，第一种是属于资产阶级和资本主义范畴的世界革命。这种世界革命的时期早已过去了，还在一九一四年第一次帝国主义世界大战...), `evidence::mao-0296` (中国革命的历史特点是分为民主主义和社会主义两个步骤，而其第一步现在已不是一般的民主主义，而是中国式的、特殊的、新式的民主主义，而是新民主主...), `evidence::mao-0297` (“十月革命的伟大的世界意义，主要的是：第一，它扩大了民族问题的范围，把它从欧洲反对民族压迫的斗争的局部问题，变为各被压迫民族、各殖民地及半...), `evidence::mao-0298` (由此可见，有两种世界革命，第一种是属于资产阶级和资本主义范畴的世界革命。这种世界革命的时期早已过去了，还在一九一四年第一次帝国主义世界大战...), `framework::0238` (新民主主义论)
- Supporting edges: `derives_counter_example_signal::principle::0242->counter-example::mao-0296` (derives_counter_example_signal: principle::0242 -> counter-example::mao-0296), `derives_counter_example_signal::principle::0242->counter-example::mao-0298` (derives_counter_example_signal: principle::0242 -> counter-example::mao-0298), `section-parent::framework::0238->principle::0242` (section_parent: framework::0238 -> principle::0242), `supported-by::principle::0242->evidence::mao-0296` (supported_by_evidence: principle::0242 -> evidence::mao-0296), `supported-by::principle::0242->evidence::mao-0297` (supported_by_evidence: principle::0242 -> evidence::mao-0297), `supported-by::principle::0242->evidence::mao-0298` (supported_by_evidence: principle::0242 -> evidence::mao-0298)
- Communities: `community::principle::0242` (四　中国革命是世界革命的一部分 Cluster)
