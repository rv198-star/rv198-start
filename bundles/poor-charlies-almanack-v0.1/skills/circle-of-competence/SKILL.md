# Circle of Competence

## Identity
```yaml
skill_id: circle-of-competence
title: Circle of Competence
status: published
bundle_version: 0.1.0
skill_revision: 5
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
当前挂载 trace：3 条。

代表性案例：
- `traces/canonical/dotcom-refusal.yaml`
- `traces/canonical/google-omission.yaml`
- `traces/canonical/crypto-rejection.yaml`

推荐输出骨架：
1. 先判断是否触发：是否存在“我可以学 / 应该差不多 / 大家都说 / 说不清楚”的语言信号，且用户正准备做真实承诺。
2. 再给圈内分类：`in_circle / edge_of_circle / outside_circle`。
3. 明确写出“真正理解什么 / 还不理解什么”，尤其是变现逻辑、失败模式、关键证伪点。
4. 给下一步动作：`proceed`、`study_more`、`decline`，必要时补一句“找谁、补什么、暂停到什么程度”。

高频触发场景包括：投资陌生行业、从熟悉岗位跳到陌生赛道、看到热门机会想跟投、以及“我好像懂了但说不清楚”的重大职业或资本决策。

## Evaluation Summary
KiU Test 当前为 green，且仍绑定完整的 v0.1 shared evaluation corpus。当前摘要覆盖 20 条真实决策、20 条 adversarial trap、10 条 OOD refusal；主失败簇集中在三类：把产品熟悉度当成商业理解、把外部权威意见当成自己的独立判断、以及因为事后涨了就倒推“我当时其实应该懂”。这也是本轮 v0.5.1 要重点压缩的 usage gap。

判定边界要写清楚：
- 纯概念查询，例如“能力圈是什么概念”，不触发。
- 已在熟悉领域内有长期成功记录的用户，例如“我做了 10 年后端开发，现在做新架构设计”，不应被强行拉入能力圈怀疑。
- 边界案例可以触发，但必须区分可迁移能力和缺失知识，例如“做了 5 年产品经理，要去完全不同行业做产品”。

详见 `eval/summary.yaml`。

## Revision Summary
Revision 5 是一次面向 `v0.5.1` 的手工补强，不是 refinement_scheduler 自动 loop。核心改动不是再加结构，而是把此前偏英文、偏审计口吻的正文改成中文、action-facing 的使用说明，明确补上了四类触发语（“我可以学 / 应该差不多 / 大家都说 / 说不清楚”）、三分法输出（圈内 / 边界 / 圈外），以及纯概念查询、圈内熟手、可迁移能力边界等非触发或灰区裁定。

这轮修订的目标是缩小和 `cangjie-skill` 在 same-scenario benchmark 上的 lexical / usage gap，但不通过放松边界来换分数。为避免误触发，本轮还额外写明：像“比较 Python 和 Go 哪个更适合做微服务”这类客观技术选型或信息比较问题，不属于能力圈资格判断，默认应转去做一般分析，不应强拉进本 skill。剩余缺口仍然是：继续提升跨案例的边界清晰度，并跑出真实 loop 驱动的修订记录。详见 `iterations/revisions.yaml`。
