# 3-目标-愿景分析

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
- Primary node: `principle::0010` (3 目标/愿景分析)
- Supporting nodes: `case::effective-requirements-0021` (项目目标也可以称为愿景，是组织应用类软件系统项目、产品的灵魂，是对于出资人（或发起人、属主）而言价值的体现。但在很多需求实践中，目标、愿景...), `case::effective-requirements-0022` (生活悟道场 我一直都是一个纸质书的狂热爱好者，身边也有几位“同道中人”，都认为不可能因为电子书而放弃纸质书，因为电子书没有“书香气”，因此...), `case::effective-requirements-0023` (1.外因触发 有些时候，项目发起人会因为受到外部因素触动而提出一个项目，这时通常只有一个宏观的方向，但具体要解决的问题不够清晰，从而给目标...), `case::effective-requirements-0024` (1.新业务 案例分析 美国的Apple公司在产品方面凭借iPhone、iPad等一系列“杀手级”硬件，iTunes、App Store等创...), `case::effective-requirements-0025` ((1)1966年前出生：他们生活在一个相信权威的年代，电视、报纸、专家都是他们坚定信念的来源，相对保守。“电视购物”则是为他们量身定做的“...), `evidence::effective-requirements-0021` (项目目标也可以称为愿景，是组织应用类软件系统项目、产品的灵魂，是对于出资人（或发起人、属主）而言价值的体现。但在很多需求实践中，目标、愿景...), `evidence::effective-requirements-0022` (生活悟道场 我一直都是一个纸质书的狂热爱好者，身边也有几位“同道中人”，都认为不可能因为电子书而放弃纸质书，因为电子书没有“书香气”，因此...), `evidence::effective-requirements-0023` (1.外因触发 有些时候，项目发起人会因为受到外部因素触动而提出一个项目，这时通常只有一个宏观的方向，但具体要解决的问题不够清晰，从而给目标...), `evidence::effective-requirements-0024` (1.新业务 案例分析 美国的Apple公司在产品方面凭借iPhone、iPad等一系列“杀手级”硬件，iTunes、App Store等创...), `evidence::effective-requirements-0025` ((1)1966年前出生：他们生活在一个相信权威的年代，电视、报纸、专家都是他们坚定信念的来源，相对保守。“电视购物”则是为他们量身定做的“...), `evidence::effective-requirements-0026` (在这个模板中主要包括四部分内容：问题描述与评估（包括频率、厌恶度、可替代性三个方面）、方案说明、预期结果、价值主张。 (1)问题描述与评估...), `framework::0009` (Part 2 价值需求篇), `principle::0011` (4 干系人识别), `principle::0012` (5 干系人分析), `principle::0013` (6 价值需求分析总结), `term::attainable` (Attainable), `term::measurable` (Measurable), `term::relevant` (Relevant), `term::specific` (Specific), `term::time-based` (Time-based)
- Supporting edges: `derives_case_signal::principle::0010->case::effective-requirements-0021` (derives_case_signal: principle::0010 -> case::effective-requirements-0021), `derives_case_signal::principle::0010->case::effective-requirements-0022` (derives_case_signal: principle::0010 -> case::effective-requirements-0022), `derives_case_signal::principle::0010->case::effective-requirements-0023` (derives_case_signal: principle::0010 -> case::effective-requirements-0023), `derives_case_signal::principle::0010->case::effective-requirements-0024` (derives_case_signal: principle::0010 -> case::effective-requirements-0024), `derives_case_signal::principle::0010->case::effective-requirements-0025` (derives_case_signal: principle::0010 -> case::effective-requirements-0025), `derives_term_signal::principle::0010->term::attainable` (derives_term_signal: principle::0010 -> term::attainable), `derives_term_signal::principle::0010->term::measurable` (derives_term_signal: principle::0010 -> term::measurable), `derives_term_signal::principle::0010->term::relevant` (derives_term_signal: principle::0010 -> term::relevant), `derives_term_signal::principle::0010->term::specific` (derives_term_signal: principle::0010 -> term::specific), `derives_term_signal::principle::0010->term::time-based` (derives_term_signal: principle::0010 -> term::time-based), `section-parent::framework::0009->principle::0010` (section_parent: framework::0009 -> principle::0010), `section-parent::principle::0010->principle::0011` (section_parent: principle::0010 -> principle::0011), `section-parent::principle::0010->principle::0012` (section_parent: principle::0010 -> principle::0012), `section-parent::principle::0010->principle::0013` (section_parent: principle::0010 -> principle::0013), `supported-by::principle::0010->evidence::effective-requirements-0021` (supported_by_evidence: principle::0010 -> evidence::effective-requirements-0021), `supported-by::principle::0010->evidence::effective-requirements-0022` (supported_by_evidence: principle::0010 -> evidence::effective-requirements-0022), `supported-by::principle::0010->evidence::effective-requirements-0023` (supported_by_evidence: principle::0010 -> evidence::effective-requirements-0023), `supported-by::principle::0010->evidence::effective-requirements-0024` (supported_by_evidence: principle::0010 -> evidence::effective-requirements-0024), `supported-by::principle::0010->evidence::effective-requirements-0025` (supported_by_evidence: principle::0010 -> evidence::effective-requirements-0025), `supported-by::principle::0010->evidence::effective-requirements-0026` (supported_by_evidence: principle::0010 -> evidence::effective-requirements-0026)
- Communities: `community::principle::0010` (3 目标/愿景分析 Cluster), `community::principle::0011` (4 干系人识别 Cluster), `community::principle::0012` (5 干系人分析 Cluster), `community::principle::0013` (6 价值需求分析总结 Cluster)
