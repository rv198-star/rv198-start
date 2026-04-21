# circle-of-competence

Created: 2026年4月21日 04:46
Domain: investing (../Domain%20Profiles/investing%2023a10798ca34433e944c45385620d2f9.md)
Eval: adversarial: 100%
Eval: ood: 100%
Eval: real_decisions: 100%
Has `use` Block: Yes
Has ≥3 Traces: Yes
KiU Test: All Pass
Notes: 样本评测 (n=1 per type) 全部通过。下一步扩充至 real_decision=20 / adversarial=20 / ood=10 再判定是否 Published。Contract Schema 验证成功 —— 作为 v0.1 reference implementation.
Priority: P0 · MVP
Source Corpus: 《穷查理宝典》
Stage: Under Evaluation
Tags: decision_making, framework, self_audit
Trigger Summary: 用户考虑投资某个标的 / 判断自己对某领域的理解深度是否足以出手时触发
Updated: 2026年4月21日 05:15

<aside>
🎯

**Skill**: `circle-of-competence` · **Corpus**: 《穷查理宝典》 · **Domain**: investing

**Status**: KiU Test · Q1/Q2/Q3 · **All Pass** (样本评测通过,待扩充到 ≥50 条正式 eval)

</aside>

## use

机器可读契约。按 KiU Contract Schema v0.1 (见 [Skill Contract Schema · `use` block](../Skill%20Contract%20Schema%20%C2%B7%20use%20block%205364dbd0439442e8b4319c55fcbede16.md))。

```yaml
trigger:
  patterns:
    - "用户表达考虑投资某个具体标的(个股/行业/资产类别)"
    - "用户询问自己是否应该建仓/加仓于某领域"
    - "用户在评估自己对某行业/公司的理解深度是否足以出手"
  exclusions:
    - "指数化/分散化被动投资(能力圈概念不直接适用)"
    - "用户明确声明仅为学习理论、不做实际决策"

intake:
  required:
    - name: target
      type: string
      description: "正在考虑的标的或领域(公司名/行业/资产类别)"
    - name: user_background
      type: string
      description: "用户在该领域的真实工作/投资/研究经验"
    - name: claimed_understanding
      type: array<string>
      description: "用户自述理解的关键点(商业模式、护城河、风险、关键指标)"
  optional:
    - name: capital_at_stake
      type: string
      description: "仓位占净资产比例"
    - name: time_horizon
      type: string
      description: "预期持有期"

judgment_schema:
  output:
    type: object
    schema:
      verdict:
        type: enum
        values: ["in_circle", "edge_of_circle", "outside_circle"]
      rationale:
        type: string
      missing_knowledge:
        type: array<string>
      recommended_action:
        type: enum
        values: ["proceed", "study_more", "decline"]
    reasoning_chain_required: true

boundary:
  fails_when:
    - "target 过于泛化(例如 '科技股') —— 无法针对具体公司判断理解深度"
    - "user_background 描述过于简略,无法辨别用户的真实深度"
  do_not_fire_when:
    - "不是投资决策情境(职业/生活/健康等)"
    - "被动指数投资,能力圈概念不适用"
    - "用户是学习者而非决策者"
```

## usage traces

3 条历史真实决策(全量见 [](../Usage%20Traces%20830f937243404f7ab3d0ebd9e06c7482.md),按 Skill 过滤 `circle-of-competence`):

1. **1999-2000 · Buffett 拒绝科技/互联网股** —— `outside_circle` + `decline`。保留大量现金,2000-2002 泡沫破裂后伯克希尔相对收益显著跑赢。
2. **2004 · Buffett/Munger 跳过 Google IPO** —— `edge_of_circle`。Munger 多次公开承认为 mistake of omission,但仍认为守纪正确。
3. **2017-2023 · Munger 反复拒绝加密货币** —— `outside_circle` + 标的本身无商业性判断。避开 2018/2022 两次 crypto 崩盘。

## rationale

为什么这条 skill 值得独立存在 (R / I / A² / E / B 五维):

- **R · Root** — 巴菲特归因其终身超额收益的第一条规则:"我们只在看得懂的地方下注。"同一表达在 Munger / Graham / Klarman 文本中被反复锚定。
- **I · Insight** — 守在圈内不是保守,而是主动选择"放弃大多数机会"。大部分投资失败源于"在懂的 10% 之外出手",而非"在懂的 10% 里犯错"。
- **A² · Actionable** — 本 skill 提供 `verdict + recommended_action` 二维输出,不停留在"你应该了解自己"。
- **E · Evidence** — Berkshire 多次公开决策(dotcom pass / Google / crypto)构成天然 eval 集。
- **B · Boundary** — 对指数化 / ETF / 学习情境主动不触发。与 [invert-the-problem](invert-the-problem%20f2729af6d8114f9cb1a74f2160178899.md) 的分工: 本 skill 过滤"是否该出手",inversion 用于已决定出手后的风险框架。

## anchors

(provenance — L2 Graph 建好后回填真实 node_ids;当前为占位)

- `node://poor-charlies-almanack/ch2/circle-of-competence`
- `node://buffett-letters/1999/sun-valley-speech`
- `node://buffett-letters/2001/tech-avoidance`
- `node://munger-djco/2017/google-omission`
- `node://munger-djco/2023/crypto-rejection`

## kiu test · 样本评测记录

全量用例见 [](../Evaluation%20Cases%205a4b3c0a36e24cb3bc9fe0083b6e6ede.md),按 Skill 过滤。本轮跑 3 条样本(每类 n=1):

| 闸门 | 用例类型 | 期望行为 | 实际输出 | 结果 |
| --- | --- | --- | --- | --- |
| Q1 · Trigger Test | 契约自检 | `use.trigger` 机器可读、有 exclusions | YAML 有效,patterns ×3 + exclusions ×2 | **Pass** |
| Q2 · Fire Test | real_decision (量子 ETF 案例) | fire → outside_circle → decline | fire → outside_circle → decline (含 missing_knowledge ×3) | **Pass** |
| Q3 · Boundary Test | out_of_distribution (职业进退) | not_fire / mark_ood | not_fire — 匹配 [boundary.do](http://boundary.do)_not_fire_when[0] | **Pass** |
| (bonus) | synthetic_adversarial (TSLA 车主圈) | fire → edge_of_circle (不被表层熟悉度骗) | fire → edge_of_circle → study_more | **Pass** |

**结论**: Contract Schema 在这条 skill 上站住了。样本很小 (n=1/类),但三个门都能明确判分,而且 adversarial 用例(最关键)没被"5 年持仓+车友圈"的表层熟悉度骗到。

进入正式 Published 前的扣针:扩充 real_decision 到 20 条(用 Berkshire 历年持仓 + 公开拒绝案例)、adversarial 20 条、ood 10 条。