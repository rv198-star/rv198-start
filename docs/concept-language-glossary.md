# 概念语言对照表

这份文档用于把历史/内部术语映射到 v0.8 的 `学以致用` 架构语言，方便追溯旧报告和旧版本证据。

它不是项目主叙事。新的用户侧和评审侧文档应优先使用 v0.8 语言。历史术语仍然可以保留在归档报告、发布证据、归因说明和本对照表中。

## v0.8 公共架构语言

| 公共表述 | 精确含义 | 新文档中的使用位置 |
| --- | --- | --- |
| 读准原书 | 保留原书事实、段落、锚点、结构和来源。 | README、架构叙事、来源忠实度文档。 |
| 提炼判断 | 把原书材料转化为可迁移判断。 | README、架构叙事、生成链路文档。 |
| 生成技能 | 发布能帮助用户判断、取舍、拒绝、行动或复盘的有边界技能。 | README、技能文档、评分卡。 |
| 分流流程 | 确定性步骤保留为流程工件，而不是厚技能。 | README、流程文档、边界审查。 |
| 校准应用 | 隔离地加入当前语境、事实核验、风险提示和安全门。 | README、当前事实核验和应用文档。 |
| 验证行动价值 | 验证产物是否在明确证据等级下产生行动价值。 | README、评分指南、发布说明。 |

## 历史术语到 v0.8 的映射

| 历史或内部术语 | v0.8 对应说法 | 现在应该出现的位置 |
| --- | --- | --- |
| Graphify absorption | 读准原书成熟度 | 仅用于历史证据和归因说明。 |
| graph-backed evidence | 读准原书 / 来源证据 | 需要讨论证据结构时可使用。 |
| cangjie methodology absorption | 提炼判断 + 生成技能的生成纪律 | 仅用于历史 benchmark 和归因说明。 |
| cangjie core closure | 生成方法就绪度 | 仅用于历史证据。 |
| RIA-TV++ | 提炼阶段链路 | 历史实现细节。 |
| triple verification | 证据校验 | 需要时可作为当前公共语言。 |
| C-class action value | 验证行动价值 | 当前公共语言。 |
| A/B/C taxonomy | 方法完整度、来源/事实安全、行动价值、证据可信度 | 内部指标分类。 |
| three-layer review | 来源/生成/使用三层审查 | 内部证据格式。 |
| proxy usage | 内部场景校验 | 证据等级，不是真实用户验证。 |
| same-source benchmark | 同书参照对比 | 证据等级。 |
| blind review pack | 盲评包 | 条件依赖型验证工件。 |
| world alignment | 校准应用 | 当前公共语言。 |
| live fact verification | 当前事实核验 | 校准应用的组成部分。 |
| use-state arbitration | 应用状态门 | 校准应用的组成部分。 |
| application readiness | 应用就绪门 | 校准应用的组成部分。 |
| workflow gateway | 流程路由器 | 当前公共语言。 |
| workflow-vs-agentic boundary | 流程/判断边界 | 当前公共语言。 |
| action-skill identity | 行动技能身份 | 当前公共语言。 |
| RAG / knowledge-base Q&A | 参照概念，不是 KiU 主定位 | 可在 README 和项目叙事中用于说明区别：RAG 偏检索生成答案，KiU 偏生成行动技能。 |
| System Efficiency Over Local Advantage | 系统效率碾压局部优势 | 通用宏观决策工具，详见 `docs/methodologies/top-level-decision-philosophy.md`。 |
| Recursive Five-Step Method | 三层递归五步法 | 通用复杂问题推进工具，详见 `docs/methodologies/recursive-five-step-method.md`。 |
| Extreme Deduction / Scenario Projection | 极限演绎与场景投影法 | 通用结构诊断和场景选型工具，详见 `docs/methodologies/extreme-deduction-and-scenario-projection.md`。 |

## 迁移规则

新文档如果必须提到历史术语，只在第一次出现时说明历史对应关系，例如：

`读准原书（v0.6 历史证据中曾称 Graphify absorption）`

后文继续使用 v0.8 术语。

不要为了改名而重写旧证据包。

## 不要做什么

- 不要把本对照表当作项目开场解释。
- 不要批量替换历史报告。
- 不要隐藏外部影响或归因说明。
- 能用普通动作短语表达时，不要继续造新术语。
