# 价值驱动增值器

## 定位

价值驱动增值器是 KiU 调用外部 `Thinking Value-Gain Methodology v0.1` 后沉淀出的生成末端增强器。

它不是 KiU 原生顶层方法论，也不是原书内容的一部分。它的作用是放在 `生成技能` 之后、发布评估之前，检查一条 skill 是否真的能帮助用户形成更好的判断、行动、复审、交接或复用。

一句话定位：当 skill 已经结构完整时，价值驱动增值器负责追问“用户拿到它以后，是否更知道下一步怎么用”。

## 当前实现

当前只保留最新版实现，不维护 B/C 等并行路径。

最新版实现包括三部分：

1. `value_gain_*` 输出字段：要求 skill 明确写出决策价值、证据价值、风险边界和下一步交接。
2. `Downstream Use Check`：在 Rationale 中追加用户视角的下游使用检查。
3. `Minimum Pressure Pass`：对 skill 做一次最小压力测试，避免“结构完整但价值偏薄”的假完成。

生成物中不得出现外部方法论名称，例如 `模块价值增益法`、`thinking-value-gain` 或 `Premature Exit Check`。生成物只保留操作性检查语言，避免污染 source-derived `SKILL.md`。

## 压力类型

增值器在生成阶段按 skill 形态选择一种压力，不默认多跑流程，也不把所有压力都堆进产物。

| 压力 | 适用形态 | 检查问题 |
| --- | --- | --- |
| `failure pressure` | 偏差审计、风险控制、仓位/安全边界 | 这条 skill 在什么失败条件下会误导用户？ |
| `alternative pressure` | 取舍、矛盾、阻力、机会成本、问题框架 | 是否存在更好、更便宜、更安全或更准确的问题框架？ |
| `evidence pressure` | 价值判断、来源锚点、历史类比、角色边界、后果判断 | 当前结论是否超过证据？相似性是否只是故事相似？ |
| `downstream pressure` | 工作流入口、问题重构、交接型 skill | 下游用户还需要自己补什么关键判断才能行动？ |

## 调用机制

价值驱动增值器的默认调用位置是生成链路内部，而不是人工后处理：

1. 先由 KiU 正常完成读准原书、提炼判断、生成技能、分流流程。
2. 对进入 `bundle/skills/` 的 skill 增强 contract：追加 `value_gain_decision`、`value_gain_evidence`、`value_gain_risk_boundary`、`value_gain_next_handoff`。
3. 根据 skill id、输出 schema 和语义形态选择一个最小压力类型。
4. 在 Rationale 中追加 `Downstream Use Check` 和对应 `Minimum Pressure Pass`。
5. 重新跑 preflight、三层评分、污染扫描和必要的用户视角 review。
6. 如果压力检查只增加长度、术语或流程重量，而没有改变决策、行动、证据、交接或复审价值，应冻结而不是继续加内容。

## 使用边界

必须遵守以下边界：

- 不把外部方法论文本粘进原书派生的 `SKILL.md`。
- 不替代原书证据，不新增原书没有支持的主张。
- 不把内部用户视角 review 说成外部真人验证。
- 不用它为结构漂移、流程/判断边界漂移或来源污染辩护。
- 不为了“显得深”而增加流程重量；只有能提升决策、行动、证据、交接或复审价值时才保留。

## 验证状态

截至 2026-04-26，最新版价值驱动增值器已经完成五本书生成链路验证：Financial Statement、Effective Requirements、Mao Anthology、Poor Charlie、Shiji。

五本三层评分均保持 release gate PASS，且污染扫描没有发现外部方法论名称进入生成物。

内部用户视角 A/B/C 评审显示：

- A 原版平均 `20.92/25`
- B 早期 value-gain chain 平均 `22.20/25`
- 当前最新版平均 `23.08/25`

该结果支持“保留最新版增值器为默认生成链路的一部分”。它仍然不是外部用户验证。

## 后续改进方向

下一步不应增加更多流程。优先方向是提升 shape detection 和 source-aware wording，让压力检查更贴近每本书和每类 skill 的机制，同时继续避免来源污染。
