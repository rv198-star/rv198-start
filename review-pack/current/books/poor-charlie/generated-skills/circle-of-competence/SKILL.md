# Circle of Competence

## Identity
```yaml
skill_id: circle-of-competence
title: Circle of Competence
status: under_evaluation
bundle_version: 0.2.0
skill_revision: 1
```

## Contract
```yaml
trigger:
  patterns:
  - user_considering_specific_investment
  - user_asking_if_understanding_is_deep_enough_to_act
  exclusions:
  - user_choosing_passive_index_fund
  - user_request_is_non_investing_decision
intake:
  required:
  - name: target
    type: entity
    description: Asset, company, or domain under consideration.
  - name: user_background
    type: structured
    description: Demonstrated exposure and depth in the target domain.
  - name: capital_at_risk
    type: number
    description: Share of net worth or portfolio at stake.
judgment_schema:
  output:
    type: structured
    schema:
      verdict: enum[in_circle, edge_of_circle, outside_circle]
      missing_knowledge: list[string]
      recommended_action: enum[proceed, study_more, decline]
  reasoning_chain_required: true
boundary:
  fails_when:
  - user_confuses_product_familiarity_with_business_understanding
  - user_describes_background_too_vaguely_to_test_depth
  do_not_fire_when:
  - user_chooses_passive_index_fund
  - user_request_is_non_investing_decision
```

## Rationale
这条 skill 不是一句“保持谦虚”的空话，而是在做重大投资或职业承诺前，先判断你有没有资格独立下判断。凡是用户出现“我可以学”“应该差不多”“大家都说这是好机会”“我好像懂了但说不清楚”这类信号，都要立刻做否定测试：能不能用自己的话讲清核心运作逻辑、主要收入来源、关键成本、行业结构、管理层激励、会怎么失败、什么证据会推翻当前想法。如果说不清，只能借别人的判断、只会讲产品体验、或者只是觉得趋势很好，就不能算在圈内。[^anchor:circle-source-note]

输出必须是可执行判断，而不是抽象提醒。先给出 `in_circle / edge_of_circle / outside_circle` 三分法，再列出 `missing_knowledge`，最后给出 `recommended_action`：圈内才允许推进，边界地带要先补关键知识或找第二意见，圈外则应拒绝独立决策、找专家、或把投入压到可承受的试错级别。真实决策案例和对抗案例共同说明了一件事：学历、产品熟悉度、日常使用、甚至已经持有标的，都可能制造“我懂了”的幻觉，但并不等于你真正理解了这门生意。[^anchor:circle-eval] [^trace:canonical/dotcom-refusal.yaml]

## Evidence Summary
三条 canonical trace 把“能力圈”从概念变成动作。`dotcom-refusal` 展示的是最干净的拒绝模式：当用户讲不清商业逻辑、现金流来源、行业结构时，正确动作不是硬凑乐观理由，而是直接 `decline`。[^trace:canonical/dotcom-refusal.yaml] `google-omission` 说明更难的一层：哪怕事后结果很好，如果当时并没有真正理解护城河和长期经济性，错过也不代表当时应该硬上；这条证据用来压制“因为后来涨了，所以我当时其实懂”的 hindsight 幻觉。[^trace:canonical/google-omission.yaml] `crypto-rejection` 则对应“大家都说能赚钱、我也想试试”的 FOMO 场景：当连价值引擎和分析对象都说不清时，圈外判断就应触发强拒绝。[^trace:canonical/crypto-rejection.yaml]

这些证据共同支持同一个结论：能力圈不是“听过、用过、喜欢过”，而是“我能清楚解释、能识别关键风险、能说出自己还不懂什么”。只要这三点不成立，就不能把熟悉感误当成理解。[^anchor:circle-source-note] [^anchor:circle-eval]

The v0.2 seed preserves graph/source double anchoring and records the workflow-vs-agentic routing decision in `candidate.yaml`.

Scenario-family anchor coverage: `should_trigger` `domain-transfer-boundary` -> `circle-source-note`, `circle-trace-dotcom` (这是在判断自己是否有资格独立下判断，而不是做概念解释或客观技术比较。); `should_trigger` `social-proof-fomo` -> `circle-trace-crypto`, `circle-eval` (这类场景需要先验证独立理解，而不是让社交证明替代能力圈。); `should_not_trigger` `concept-or-objective-comparison` -> `circle-source-note` (这不是资格判断，而是概念学习或客观分析。); `edge_case` `transferable-skill-vs-domain-gap` -> `circle-real-decision`, `circle-eval` (一部分能力可迁移，但真正的行业风险点仍可能在圈外。); `edge_case` `graph-ambiguous-boundary-n_eval_ood_career_offer` -> `n_eval_ood_career_offer` (Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.); `refusal` `cannot-explain-business-clearly` -> `circle-trace-google`, `circle-trace-crypto` (说不清商业逻辑和失败机制，本身就是还不在圈内的证据。).

Graph-to-skill distillation: `INFERRED` graph links `e_circle_bias_complements` (`Circle of competence` -> `Bias self audit`, source_location `sources/circle-of-competence.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `n_eval_ood_career_offer` at source_location `evaluation/out_of_distribution/career-offer-choice.yaml:1-8`, `n_eval_surface_familiarity` at source_location `evaluation/synthetic_adversarial/tsla-surface-familiarity.yaml:1-8`, `e_circle_ood_boundary_ambiguous` at source_location `evaluation/out_of_distribution/career-offer-choice.yaml:1-8` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_boundary_discipline`/Boundary discipline; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先做能力边界测试：列出 missing_knowledge、判断 in_circle / edge_of_circle / outside_circle，再给 study_more 或 decline。

## Relations
```yaml
depends_on: []
delegates_to:
- bias-self-audit
constrained_by:
- margin-of-safety-sizing
complements:
- invert-the-problem
- opportunity-cost-of-the-next-best-idea
contradicts: []
```

## Usage Summary
Current trace attachments: 3.

Graph-to-skill distillation: `INFERRED` graph links `e_circle_bias_complements` (`Circle of competence` -> `Bias self audit`, source_location `sources/circle-of-competence.md:1-9`) are rendered as bounded trigger expansion, never as standalone proof.

Graph-to-skill distillation: `AMBIGUOUS` signals `n_eval_ood_career_offer` at source_location `evaluation/out_of_distribution/career-offer-choice.yaml:1-8`, `n_eval_surface_familiarity` at source_location `evaluation/synthetic_adversarial/tsla-surface-familiarity.yaml:1-8`, `e_circle_ood_boundary_ambiguous` at source_location `evaluation/out_of_distribution/career-offer-choice.yaml:1-8` are rendered as edge_case/refusal boundaries before any broad firing.

Graph navigation: `GRAPH_REPORT.md` places this candidate near `c_boundary_discipline`/Boundary discipline; use this for related-skill handoff, not as independent evidence.

Action-language transfer: 先做能力边界测试：列出 missing_knowledge、判断 in_circle / edge_of_circle / outside_circle，再给 study_more 或 decline。

Scenario families:
- `should_trigger` `domain-transfer-boundary`; 当用户准备进入陌生行业、陌生资产或陌生岗位，并出现“应该差不多能搞明白”“我可以边做边学”这类语言时触发。; signals: 我可以学 / 应该差不多 / 没做过但想试试; boundary: 这是在判断自己是否有资格独立下判断，而不是做概念解释或客观技术比较。; next: 区分可迁移能力与缺失的专业知识边界，给出 in_circle / edge_of_circle / outside_circle，并写出 proceed / study_more / decline。
- `should_trigger` `social-proof-fomo`; 当用户把“大家都说这是好机会”当成理解替代品时触发。; signals: 大家都说这是好机会 / 想先投一点试试 / 搞不太懂但感觉会涨; boundary: 这类场景需要先验证独立理解，而不是让社交证明替代能力圈。; next: 要求用户解释核心运作逻辑、失败路径和关键证伪点，再决定 study_more 还是 decline。
- `should_trigger` `graph-inferred-link-e_circle_bias_complements`; Graph-to-skill distillation: `INFERRED` edge `e_circle_bias_complements` expands trigger language only when a live decision links `Circle of competence` and `Bias self audit`.; signals: Circle of competence / Bias self audit / # Circle of Competence Source Note Skill ID: circle-of-competence Primary Cla...; boundary: This relation is INFERRED, so it can widen trigger recall only with concrete decision context, explicit source evidence, and the existing do_not_fire_when boundary still active.; next: 先做能力边界测试：列出 missing_knowledge、判断 in_circle / edge_of_circle / outside_circle，再给 study_more 或 decline。 Evidence check: verify source_location `sources/circle-of-competence.md:1-9` before expanding the trigger.
- `should_not_trigger` `concept-or-objective-comparison`; 纯概念查询或客观比较问题不应触发，例如解释能力圈概念，或比较 Python 和 Go 的工程适配性。; signals: 能力圈是什么意思 / Python 和 Go 哪个更适合做微服务; boundary: 这不是资格判断，而是概念学习或客观分析。
- `edge_case` `transferable-skill-vs-domain-gap`; 用户拥有可迁移通用能力，但缺少行业专有知识时，应用边界态而不是直接判圈内或圈外。; signals: 做了5年产品经理 / 完全不同行业 / 怕自己搞不定; boundary: 一部分能力可迁移，但真正的行业风险点仍可能在圈外。; next: 拆出哪些能力在圈内、哪些行业知识在圈外，再决定是否先小规模试错或找第二意见。
- `edge_case` `graph-ambiguous-boundary-n_eval_ood_career_offer`; Graph-to-skill distillation: `AMBIGUOUS` signal `n_eval_ood_career_offer` is a boundary probe, not a permission to fire broadly.; signals: Career offer OOD case / case_id: career-offer-choice subset: out_of_distribution primary_skill: circl... / 不熟悉领域; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `evaluation/out_of_distribution/career-offer-choice.yaml:1-8`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-n_eval_surface_familiarity`; Graph-to-skill distillation: `AMBIGUOUS` signal `n_eval_surface_familiarity` is a boundary probe, not a permission to fire broadly.; signals: Surface familiarity trap / case_id: tsla-surface-familiarity subset: synthetic_adversarial primary_skill... / 不熟悉领域; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `evaluation/synthetic_adversarial/tsla-surface-familiarity.yaml:1-8`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-e_circle_ood_boundary_ambiguous`; Graph-to-skill distillation: `AMBIGUOUS` signal `e_circle_ood_boundary_ambiguous` is a boundary probe, not a permission to fire broadly.; signals: boundary_probe / case_id: career-offer-choice subset: out_of_distribution primary_skill: circl... / 不熟悉领域; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `evaluation/out_of_distribution/career-offer-choice.yaml:1-8`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `edge_case` `graph-ambiguous-boundary-e_circle_surface_boundary_ambiguous`; Graph-to-skill distillation: `AMBIGUOUS` signal `e_circle_surface_boundary_ambiguous` is a boundary probe, not a permission to fire broadly.; signals: boundary_probe / case_id: tsla-surface-familiarity subset: synthetic_adversarial primary_skill... / 不熟悉领域; boundary: Because this graph signal is AMBIGUOUS, the skill should use partial_review or defer unless live decision context, source evidence, and disconfirming evidence are explicit.; next: Check source_location `evaluation/synthetic_adversarial/tsla-surface-familiarity.yaml:1-8`, name the boundary uncertainty, and either narrow the output or decline with a concrete decline_reason.
- `refusal` `cannot-explain-business-clearly`; 当用户说“好像懂了，但说不清楚怎么变现/怎么失败”时，应拒绝给出圈内判断。; signals: 说不清楚怎么变现 / 好像懂了 / 具体失败点还没想清楚; boundary: 说不清商业逻辑和失败机制，本身就是还不在圈内的证据。; next: 列出真正理解和不理解的部分，先 study_more，再决定是否投入或直接 decline。

Representative cases:
- `traces/canonical/dotcom-refusal.yaml`
- `traces/canonical/google-omission.yaml`
- `traces/canonical/crypto-rejection.yaml`

## Evaluation Summary
当前 KiU Test 状态：trigger_test=`pass`，fire_test=`pass`，boundary_test=`pass`。

已绑定最小评测集：
- `real_decisions`: passed=20 / total=20, threshold=0.7, status=`pass`
- `synthetic_adversarial`: passed=20 / total=20, threshold=0.85, status=`pass`
- `out_of_distribution`: passed=10 / total=10, threshold=0.9, status=`pass`

关键失败模式：
- Surface familiarity can look like depth unless the contract asks for missing knowledge explicitly.
- Users can reinterpret disciplined refusal as failure after a missed winner unless process quality stays explicit.
- Domain-adjacent credentials can create false positives when the actual business model remains outside demonstrated understanding.

场景族覆盖：`should_trigger`=3，`should_not_trigger`=1，`edge_case`=5，`refusal`=1。详见 `usage/scenarios.yaml`。

详见 `eval/summary.yaml` 与共享 `evaluation/`。

## Revision Summary
Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。核心改动不是再加结构，而是把此前偏英文、偏审计口吻的正文改成中文、action-facing 的使用说明，明确补上了四类触发语（“我可以学 / 应该差不多 / 大家都说 / 说不清楚”）、三分法输出（圈内 / 边界 / 圈外），以及纯概念查询、圈内熟手、可迁移能力边界等非触发或灰区裁定。

这轮修订的目标是缩小和 `cangjie-skill` 在 same-scenario benchmark 上的 lexical / usage gap，但不通过放松边界来换分数。为避免误触发，本轮还额外写明：像“比较 Python 和 Go 哪个更适合做微服务”这类客观技术选型或信息比较问题，不属于能力圈资格判断，默认应转去做一般分析，不应强拉进本 skill。剩余缺口仍然是：继续提升跨案例的边界清晰度，并跑出真实 loop 驱动的修订记录。详见 `iterations/revisions.yaml`。

本轮补入：
- Added Chinese trigger phrases such as "我可以学", "应该差不多", "大家都说", and "说不清楚" to the published rationale and usage guidance.
- Expanded boundary and evaluation summaries with explicit non-trigger and edge-case rulings for concept queries, in-circle experts, and transferable-skill scenarios.
- Kept the existing evidence anchors intact while making next-step outputs more action-facing for benchmarked usage.

当前待补缺口：
- Continue tightening non-trigger boundary phrasing and edge-case handling across the full investing bundle.
- Run a real refinement_scheduler pass before describing this skill as loop-driven.
