# Workflow Gateway

## Identity
```yaml
skill_id: workflow-gateway
title: Workflow Gateway
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 3
```

## Contract
```yaml
trigger:
  patterns:
  - 我们的具体纲领_decision_required
  - 我们的具体纲领_evidence_grounded
  exclusions:
  - concept_query_only
  - 我们的具体纲领_outside_operating_boundary
intake:
  required:
  - name: user_goal
    type: string
    description: The outcome the user wants from the workflow set.
  - name: available_context
    type: list
    description: Known inputs, constraints, and missing situational facts.
  - name: candidate_workflow_hint
    type: string
    description: Optional workflow id or topic the user thinks may fit.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[route_to_workflow, ask_clarifying_question, defer]
      selected_workflow_id: string
      routing_reason: string
      missing_context: list[string]
      next_action: string
  reasoning_chain_required: true
boundary:
  fails_when:
  - disconfirming_evidence_present
  - 我们的具体纲领_evidence_conflict
  do_not_fire_when:
  - scenario_missing_decision_context
  - 我们的具体纲领_boundary_unclear
```

## Rationale
当一个材料存在 high workflow certainty + high context certainty 的候选时，KiU 不能为了让 bundle 看起来有 skill 而把确定性步骤伪装成厚 skill。但默认产物仍需要一个可安装、可调用的入口，否则用户拿到的包只能审计，不能使用。`workflow-gateway` 的职责就是在这两者之间保持边界：它读取用户目标、现有上下文和可能的 workflow hint，再选择、排序或要求补充上下文；它不改写 workflow_candidates 下的固定步骤，也不把脚本逻辑偷偷并回 agentic skill。因此它是一个薄路由 skill，而不是领域判断 skill。[^anchor:workflow-gateway-primary]

Mechanism chain: source anchor -> mechanism observed -> transferable judgment -> user trigger -> anti-misuse boundary.

- source anchor: `开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经...` — 开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经过南京傀儡政府，也正在和日本密使勾勾搭搭，并未遇到制止。因此，中途妥协的危险并未完全过去。开罗会议又决定将东北四省、台湾、澎湖列岛归还中国，这是很好的。但是根据国民党政府的现行政策，要想依靠它打到鸭绿江边，收复一切失地，是不可能的。在这种情形下，中国人民应该怎么办呢？中国人民应该要求国民党政府彻底消灭[^anchor:workflow-gateway-counter-example::mao-0444]
- mechanism observed: `开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经...` contains mechanism-density `0.65`; extract actor, action, constraint, and consequence before transfer.
- transferable judgment: Use `Workflow Gateway` only when the current decision matches the source mechanism and boundary checks pass.
- user trigger: `我们的具体纲领_decision_required`
- anti-misuse boundary: `scenario_missing_decision_context`

User-facing role: this is a thin workflow router, not a thick judgment skill. It should select, sequence, or defer workflow candidates while keeping deterministic steps in `workflow_candidates/`.

## Evidence Summary
该 gateway 在当前生成轮次存在 workflow_script_candidate 时生成，即使同一 bundle 也包含少量真正判断密集型 skill。这说明材料仍有一部分主要交付物是确定性流程，同时也说明需要一个最小可用入口，把用户请求路由到 workflow_candidates 中的具体 `workflow.yaml` / `CHECKLIST.md`。当前候选 workflow 包括 `五-全党团结起来-为实现党的任务而斗争`, `四-中国革命是世界革命的一部分`, `我们的具体纲领`, `第三节-战略退却`, `第九章-指挥关系`, `第四节-重要的问题在善于学习`, `结-论`, `论认识和实践的关系-知和行的关系`。[^anchor:workflow-gateway-primary]

Scenario-family anchor coverage: `should_trigger` `choose-workflow-entrypoint` -> `workflow-gateway-primary` (这是路由问题，不是重新生成领域答案。); `should_trigger` `graph-inferred-link-derives_case_signal::principle::0322->case::mao-0443` -> `derives_case_signal::principle::0322->case::mao-0443` (This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.); `should_not_trigger` `exact-workflow-already-known` -> `workflow-gateway-primary` (这时应直接执行对应 workflow，而不是再做 agentic 路由。); `edge_case` `goal-too-vague-for-routing` -> `workflow-gateway-primary` (目标不足时只能 ask_clarifying_question，不能猜一个 workflow。); `edge_case` `graph-ambiguous-boundary-counter-example::mao-0443` -> `counter-example::mao-0443` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `agentic-judgment-request` -> `workflow-gateway-primary` (这超出薄 gateway 职责，应转交厚 skill 或要求新建 agentic candidate。).

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0322->case::mao-0443` (`我们的具体纲领` -> `根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是...`, source_location `sources/mao/082-论联合政府.md:135-143`), `derives_case_signal::principle::0322->case::mao-0449` (`我们的具体纲领` -> `为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的...`, source_location `sources/mao/082-论联合政府.md:182-207`), `derives_case_signal::principle::0322->case::mao-0453` (`我们的具体纲领` -> `中国共产党同意大西洋宪章和莫斯科、开罗、德黑兰、克里米亚各次国际会议(27)的决议，因为这些国际会议的决议都是有利于打败法西斯侵略者和维持...`, source_location `sources/mao/082-论联合政府.md:233-243`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::mao-0443` at source_location `sources/mao/082-论联合政府.md:135-143`, `counter-example::mao-0444` at source_location `sources/mao/082-论联合政府.md:145-146`, `counter-example::mao-0445` at source_location `sources/mao/082-论联合政府.md:148-160` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0320`/四　中国共产党的政策 Cluster, `community::principle::0322`/我们的具体纲领 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

## Relations
```yaml
depends_on: []
delegates_to: []
constrained_by: []
complements: []
contradicts: []
```

## Usage Summary
Current trace attachments: 1.

- 把用户目标映射到一个 workflow id；如果目标不足，先问缺失上下文。
- 输出 selected_workflow_id、routing_reason、missing_context 和 next_action。
- 不要把 workflow_candidates 下的确定性步骤复制成新的厚 skill。

Graph-to-skill distillation: `INFERRED` graph links `derives_case_signal::principle::0322->case::mao-0443` (`我们的具体纲领` -> `根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是...`, source_location `sources/mao/082-论联合政府.md:135-143`), `derives_case_signal::principle::0322->case::mao-0449` (`我们的具体纲领` -> `为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的...`, source_location `sources/mao/082-论联合政府.md:182-207`), `derives_case_signal::principle::0322->case::mao-0453` (`我们的具体纲领` -> `中国共产党同意大西洋宪章和莫斯科、开罗、德黑兰、克里米亚各次国际会议(27)的决议，因为这些国际会议的决议都是有利于打败法西斯侵略者和维持...`, source_location `sources/mao/082-论联合政府.md:233-243`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `counter-example::mao-0443` at source_location `sources/mao/082-论联合政府.md:135-143`, `counter-example::mao-0444` at source_location `sources/mao/082-论联合政府.md:145-146`, `counter-example::mao-0445` at source_location `sources/mao/082-论联合政府.md:148-160` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `community::principle::0320`/四　中国共产党的政策 Cluster, `community::principle::0322`/我们的具体纲领 Cluster; use this for related-skill handoff, not as independent evidence.

Action-language transfer: Use graph evidence to choose apply / defer / do_not_apply with explicit evidence_to_check.

Scenario families:
- `should_trigger` `choose-workflow-entrypoint`; 用户拿到一组 workflow candidates，但不知道应该从哪一个开始。; signals: 应该先跑哪个流程 / 这些步骤哪个适合当前目标 / 帮我选一个工作流入口; boundary: 这是路由问题，不是重新生成领域答案。; next: 返回 selected_workflow_id、routing_reason、missing_context、next_action。
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0322->case::mao-0443`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0322->case::mao-0443` expands trigger language only when a live decision links `我们的具体纲领` and `根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是...`.; signals: 我们的具体纲领 / 根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是... / 根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是在这个大阶段的各...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:135-143` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0322->case::mao-0449`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0322->case::mao-0449` expands trigger language only when a live decision links `我们的具体纲领` and `为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的...`.; signals: 我们的具体纲领 / 为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的... / 为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的正确的主张。 为...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:182-207` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_case_signal::principle::0322->case::mao-0453`; Graph-to-skill distillation: `INFERRED` edge `derives_case_signal::principle::0322->case::mao-0453` expands trigger language only when a live decision links `我们的具体纲领` and `中国共产党同意大西洋宪章和莫斯科、开罗、德黑兰、克里米亚各次国际会议(27)的决议，因为这些国际会议的决议都是有利于打败法西斯侵略者和维持...`.; signals: 我们的具体纲领 / 中国共产党同意大西洋宪章和莫斯科、开罗、德黑兰、克里米亚各次国际会议(27)的决议，因为这些国际会议的决议都是有利于打败法西斯侵略者和维持... / 中国共产党同意大西洋宪章和莫斯科、开罗、德黑兰、克里米亚各次国际会议(27)的决议，因为这些国际会议的决议都是有利于打败法西斯侵略者和维持世界和平的。 中...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:233-243` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0443`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0443` expands trigger language only when a live decision links `我们的具体纲领` and `根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是...`.; signals: 我们的具体纲领 / 根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是... / 根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是在这个大阶段的各...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:135-143` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0444`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0444` expands trigger language only when a live decision links `我们的具体纲领` and `开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经...`.; signals: 我们的具体纲领 / 开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经... / 开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经过南京傀儡政府，...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:145-146` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0445`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0445` expands trigger language only when a live decision links `我们的具体纲领` and `为着彻底消灭日本侵略者，必须在全国范围内实行民主改革。而要这样做，不废止国民党的一党专政，建立民主的联合政府，是不可能的。 所谓国民党的一...`.; signals: 我们的具体纲领 / 为着彻底消灭日本侵略者，必须在全国范围内实行民主改革。而要这样做，不废止国民党的一党专政，建立民主的联合政府，是不可能的。 所谓国民党的一... / 为着彻底消灭日本侵略者，必须在全国范围内实行民主改革。而要这样做，不废止国民党的一党专政，建立民主的联合政府，是不可能的。 所谓国民党的一党专政，实际上是...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:148-160` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0446`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0446` expands trigger language only when a live decision links `我们的具体纲领` and `目前中国人民争自由的目标，首先地和主要地是向着日本侵略者。但是国民党政府剥夺人民的自由，捆起人民的手足，使他们不能反对日本侵略者。不解决这...`.; signals: 我们的具体纲领 / 目前中国人民争自由的目标，首先地和主要地是向着日本侵略者。但是国民党政府剥夺人民的自由，捆起人民的手足，使他们不能反对日本侵略者。不解决这... / 目前中国人民争自由的目标，首先地和主要地是向着日本侵略者。但是国民党政府剥夺人民的自由，捆起人民的手足，使他们不能反对日本侵略者。不解决这个问题，就不能在...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:162-166` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0447`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0447` expands trigger language only when a live decision links `我们的具体纲领` and `为着消灭日本侵略者，为着防止内战，为着建设新中国，必须将分裂的中国变为统一的中国，这是中国人民的历史任务。 但是如何统一呢？独裁者的专制的...`.; signals: 我们的具体纲领 / 为着消灭日本侵略者，为着防止内战，为着建设新中国，必须将分裂的中国变为统一的中国，这是中国人民的历史任务。 但是如何统一呢？独裁者的专制的... / 为着消灭日本侵略者，为着防止内战，为着建设新中国，必须将分裂的中国变为统一的中国，这是中国人民的历史任务。 但是如何统一呢？独裁者的专制的统一，还是人民的...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:168-171` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0448`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0448` expands trigger language only when a live decision links `我们的具体纲领` and `中国人民要自由，要统一，要联合政府，要彻底地打倒日本侵略者和建设新中国，没有一支站在人民立场上的军队，那是不行的。彻底地站在人民立场的军队...`.; signals: 我们的具体纲领 / 中国人民要自由，要统一，要联合政府，要彻底地打倒日本侵略者和建设新中国，没有一支站在人民立场上的军队，那是不行的。彻底地站在人民立场的军队... / 中国人民要自由，要统一，要联合政府，要彻底地打倒日本侵略者和建设新中国，没有一支站在人民立场上的军队，那是不行的。彻底地站在人民立场的军队，现在还只有解放...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:173-180` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0449`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0449` expands trigger language only when a live decision links `我们的具体纲领` and `为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的...`.; signals: 我们的具体纲领 / 为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的... / 为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的正确的主张。 为...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:182-207` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0450`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0450` expands trigger language only when a live decision links `我们的具体纲领` and `为着打败日本侵略者和建设新中国，必须发展工业。但是，在国民党政府统治之下，一切依赖外国，它的财政经济政策是破坏人民的一切经济生活的。国民党...`.; signals: 我们的具体纲领 / 为着打败日本侵略者和建设新中国，必须发展工业。但是，在国民党政府统治之下，一切依赖外国，它的财政经济政策是破坏人民的一切经济生活的。国民党... / 为着打败日本侵略者和建设新中国，必须发展工业。但是，在国民党政府统治之下，一切依赖外国，它的财政经济政策是破坏人民的一切经济生活的。国民党统治区内仅有的一...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:209-216` before expanding the trigger.
- `should_trigger` `graph-inferred-link-derives_counter_example_signal::principle::0322->counter-example::mao-0451`; Graph-to-skill distillation: `INFERRED` edge `derives_counter_example_signal::principle::0322->counter-example::mao-0451` expands trigger language only when a live decision links `我们的具体纲领` and `民族压迫和封建压迫所给予中国人民的灾难中，包括着民族文化的灾难。特别是具有进步意义的文化事业和教育事业，进步的文化人和教育家，所受灾难，更...`.; signals: 我们的具体纲领 / 民族压迫和封建压迫所给予中国人民的灾难中，包括着民族文化的灾难。特别是具有进步意义的文化事业和教育事业，进步的文化人和教育家，所受灾难，更... / 民族压迫和封建压迫所给予中国人民的灾难中，包括着民族文化的灾难。特别是具有进步意义的文化事业和教育事业，进步的文化人和教育家，所受灾难，更为深重。为着扫除...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: Use the inferred relation to choose apply / defer / do_not_apply with explicit evidence_to_check. Evidence check: verify source_location `sources/mao/082-论联合政府.md:218-225` before expanding the trigger.
- `should_not_trigger` `exact-workflow-already-known`; 用户已经明确指定 workflow id 时，不需要 gateway 再判断。; signals: 运行 10-业务流程识别 / 打开这个 workflow.yaml; boundary: 这时应直接执行对应 workflow，而不是再做 agentic 路由。
- `edge_case` `goal-too-vague-for-routing`; 用户只说想分析材料，但没有说明目标、输入或约束。; signals: 帮我分析一下 / 看看这个材料; boundary: 目标不足时只能 ask_clarifying_question，不能猜一个 workflow。; next: 列 missing_context 并提出最少澄清问题。
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0443`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0443` is a boundary probe, not a permission to fire broadly.; signals: 根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是... / 根据上述一般纲领，我们党在各个时期中还应当有具体的纲领。在整个资产阶级民主革命阶段中，在几十年中，我们的新民主主义的一般纲领是不变的。但是在这个大阶段的各...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:135-143`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0444`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0444` is a boundary probe, not a permission to fire broadly.; signals: 开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经... / 开罗会议⒂决定应使日本侵略者无条件投降，这是正确的。但是，现在日本侵略者正在暗地里进行活动，企图获得妥协的和平；国民党政府中的亲日分子，经过南京傀儡政府，...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:145-146`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0445`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0445` is a boundary probe, not a permission to fire broadly.; signals: 为着彻底消灭日本侵略者，必须在全国范围内实行民主改革。而要这样做，不废止国民党的一党专政，建立民主的联合政府，是不可能的。 所谓国民党的一... / 为着彻底消灭日本侵略者，必须在全国范围内实行民主改革。而要这样做，不废止国民党的一党专政，建立民主的联合政府，是不可能的。 所谓国民党的一党专政，实际上是...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:148-160`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0446`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0446` is a boundary probe, not a permission to fire broadly.; signals: 目前中国人民争自由的目标，首先地和主要地是向着日本侵略者。但是国民党政府剥夺人民的自由，捆起人民的手足，使他们不能反对日本侵略者。不解决这... / 目前中国人民争自由的目标，首先地和主要地是向着日本侵略者。但是国民党政府剥夺人民的自由，捆起人民的手足，使他们不能反对日本侵略者。不解决这个问题，就不能在...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:162-166`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0447`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0447` is a boundary probe, not a permission to fire broadly.; signals: 为着消灭日本侵略者，为着防止内战，为着建设新中国，必须将分裂的中国变为统一的中国，这是中国人民的历史任务。 但是如何统一呢？独裁者的专制的... / 为着消灭日本侵略者，为着防止内战，为着建设新中国，必须将分裂的中国变为统一的中国，这是中国人民的历史任务。 但是如何统一呢？独裁者的专制的统一，还是人民的...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:168-171`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0448`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0448` is a boundary probe, not a permission to fire broadly.; signals: 中国人民要自由，要统一，要联合政府，要彻底地打倒日本侵略者和建设新中国，没有一支站在人民立场上的军队，那是不行的。彻底地站在人民立场的军队... / 中国人民要自由，要统一，要联合政府，要彻底地打倒日本侵略者和建设新中国，没有一支站在人民立场上的军队，那是不行的。彻底地站在人民立场的军队，现在还只有解放...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:173-180`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-counter-example::mao-0449`; Graph-to-skill distillation: `AMBIGUOUS` signal `counter-example::mao-0449` is a boundary probe, not a permission to fire broadly.; signals: 为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的... / 为着消灭日本侵略者和建设新中国，必须实行土地制度的改革，解放农民。孙中山先生的“耕者有其田”的主张，是目前资产阶级民主主义性质的革命时代的正确的主张。 为...; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `sources/mao/082-论联合政府.md:182-207`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `refusal` `agentic-judgment-request`; 用户要求直接给复杂判断结论，而不是选择 workflow。; signals: 直接告诉我战略怎么定 / 不要流程，给结论; boundary: 这超出薄 gateway 职责，应转交厚 skill 或要求新建 agentic candidate。; next: 说明 gateway 只能路由 workflow，不能替代判断密集型 skill。

Representative cases:
- `traces/workflow-gateway-routing-smoke.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=0 / total=0, threshold=0.0, status=`under_evaluation`
- `synthetic_adversarial`: passed=0 / total=0, threshold=0.0, status=`under_evaluation`
- `out_of_distribution`: passed=0 / total=0, threshold=0.0, status=`under_evaluation`

关键失败模式：
- 把 workflow 步骤内联成 agentic skill。
- 在目标和上下文不足时猜测 workflow。

场景族覆盖：`should_trigger`=13，`should_not_trigger`=1，`edge_case`=8，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Refinement scheduler round 2 tightened boundary signals and improved evaluation support.

本轮补入：
- Refinement scheduler round 2 tightened boundary signals and improved evaluation support.

当前待补缺口：
- Replace smoke usage review with real user routing logs before publication.
- Confirm whether each routed workflow should later gain a dedicated agentic wrapper.

