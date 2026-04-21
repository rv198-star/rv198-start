# Knowledge in Use (KiU) 背景记录

日期：2026-04-21

## 1. 当前本地状态

- 本地目录：`/Users/william/Github/KiU`
- 当前目录为空，仅有文件夹本身
- 当前目录还不是 Git 仓库
- 这意味着 KiU 目前没有既有代码、文档、命名体系或目录结构需要兼容

## 2. 参考项目拆解

### 2.1 `graphify` 提供的启发

参考：
- https://github.com/safishamsi/graphify
- https://raw.githubusercontent.com/safishamsi/graphify/refs/heads/v4/README.md
- https://raw.githubusercontent.com/safishamsi/graphify/refs/heads/v4/graphify/skill.md
- https://raw.githubusercontent.com/safishamsi/graphify/refs/heads/v4/ARCHITECTURE.md

我对它的理解：

- `graphify` 本质上不是单纯的“总结工具”，而是一个把混合资料变成可导航知识结构的 skill + library
- 它处理的输入是混合知识源：代码、文档、论文、图片、音视频
- 它强调三个核心价值：
  - 持久化知识图谱，而不是一次性上下文压缩
  - 明确区分 `EXTRACTED` / `INFERRED` / `AMBIGUOUS`，保留审计轨迹
  - 用社区聚类和关系发现，暴露“原本不知道有联系的东西”
- 它的工程组织也很清楚：`detect -> extract -> build_graph -> cluster -> analyze -> report -> export`
- 它不仅有“生成图”的离线流程，也有“安装到助手里持续使用”的运行时接入机制，例如 hook、AGENTS.md、规则文件等

对 KiU 的直接启发：

- KiU 如果只是“把知识存起来”，那会停留在笔记层
- `graphify` 提供的是“知识底座”视角：先把异构知识变成可引用、可连接、可持续更新的结构
- 对 KiU 来说，这一层更像“knowledge substrate / context layer”，不是最终目标，但可能是重要基础设施

### 2.2 `cangjie-skill` 提供的启发

参考：
- https://github.com/kangarooking/cangjie-skill
- https://raw.githubusercontent.com/kangarooking/cangjie-skill/main/README.md
- https://raw.githubusercontent.com/kangarooking/cangjie-skill/main/SKILL.md

我对它的理解：

- `cangjie-skill` 的重点不是“做书摘”，而是把一本书蒸馏成一组可执行、可调用、可测试的 skills
- 它的产出单位不是一篇总结，而是多个原子化 skill
- 它最重要的不是内容覆盖率，而是筛选机制和执行结构
- 它通过 `RIA-TV++` 这条严格流水线控制质量：
  - 整书理解
  - 并行提取
  - 三重验证
  - RIA++ skill 构造
  - Zettelkasten 链接
  - 压力测试
- 它特别强调：
  - 不凭记忆蒸馏
  - 保留 `candidates/` 和 `rejected/` 审计轨迹
  - 每个 skill 必须有 trigger、边界、执行步骤、测试样例

对 KiU 的直接启发：

- KiU 如果只是把知识“结构化整理”，依然不够
- `cangjie-skill` 提供的是“knowledge to action unit”的方法论：知识必须被蒸馏成能在真实场景中触发的 skill
- 它尤其适合 KiU 去吸收的点是：
  - 原子 skill 单元设计
  - 触发条件和适用边界
  - 审计轨迹
  - 压力测试 / 反诱饵测试

## 3. 我对 KiU 当前诉求的初步归纳

以下是结合两份参考后的推断，不是最终定稿。

### 3.1 KiU 不是单一方向的“技能仓库”

如果只看 `cangjie-skill`，很容易把 KiU 理解成“又一个蒸馏书籍的方法论 skill”。

但如果把 `graphify` 也放进来，KiU 更像是在回答一个更大的问题：

> 知识如何从原始材料，变成在真实工作流里可被调用、可组合、可校验、可持续进化的使用单元？

### 3.2 KiU 更可能有三层

一个比较稳的初步框架是：

1. **Knowledge Intake / Structure**
   - 接住原始材料
   - 形成结构、关系、来源与上下文

2. **Knowledge Distillation / Skillization**
   - 从知识里筛出真正值得复用的单元
   - 转成原子化、可触发、可组合的 skills

3. **Knowledge in Use / Runtime**
   - 让这些 skills 在真实任务中被调用
   - 记录使用反馈、边界失效、组合效果
   - 形成持续迭代闭环

### 3.3 这件事的关键，不是“知识管理”，而是“知识落地”

从目前信息看，KiU 的核心诉求更像：

- 不满足于知识采集
- 不满足于摘要或笔记
- 不满足于静态 skill 展示
- 要让知识在真实任务中被正确触发和使用

换句话说，KiU 的重点应该是 `in use`，不是 `in storage`

## 4. 当前可明确的设计原则

如果后续要重新生成 KiU 的 skills，当前至少有这些原则值得保留：

- 技能必须是可触发的，不是百科条目
- 技能必须保留来源和证据，不是只给结论
- 技能必须写清边界，不是假设万能
- 技能之间应该可以组合，而不是彼此孤立
- 技能需要可验证，不只是“看起来合理”
- 技能产物要考虑运行时接入，而不是只停留在离线文档

## 5. Notion 初版设计的已确认信息

我现在已经通过本地导出包读到了 Notion 正文。导出文件位于：

- `Knowledge in Use.zip`
- 解压后可读目录：`notion-export/unpacked-ditto/私人与共享/Knowledge in Use (KiU)/`

### 5.1 根本立场已经非常清楚

KiU 的核心句子不是装饰，而是项目定义本身：

> If it can't fire, it's not knowledge. It's notes.

这意味着 KiU 的最小单位不是：

- 笔记
- 摘要
- 图谱节点
- 检索块

而是一个**在特定情境下会触发、并给出判断的可执行契约**。

这是你和 `graphify`、`cangjie-skill` 的真正分叉点：

- 相对 `graphify`：KiU 不把“更好的表征层”当终点
- 相对 `cangjie-skill`：KiU 不把“一次性蒸馏出 skill 包”当终点

### 5.2 KiU 的核心判断，不是 representation，而是 contract

Notion 里最关键的一层判断是：

- 笔记 / RAG / 知识图谱回答的是“这是什么，它和什么相连”
- KiU 回答的是“这个情境下我该怎么判断”

也就是：

- representation 是对世界的描述
- contract 是对触发条件和判断输出的承诺

这和我之前对项目的推断基本一致，但现在更精确：

- KiU 不是“知识管理”
- KiU 是“情境触发式判断系统”

### 5.3 KiU 的五层架构已经成型

Notion 里定义的是一个明确的五层结构：

1. `L1 Input`
   - `knowledge_corpus`
   - `scenario_corpus`
   - `evaluation_corpus`
   - `manifest.yaml`

2. `L2 Graph`
   - `knowledge.graph.json`
   - `scenario.graph.json`
   - `activation_edges`
   - 保留 `EXTRACTED / INFERRED / AMBIGUOUS`

3. `L3 Strategy Router`
   - 不是附属配置，而是一等公民
   - 负责领域敏感策略，例如 `union_mode`、`verification_weights`、`preserve_contradiction`

4. `L4 KiU Extraction`
   - 目标不是抽原则，而是抽“可触发契约”
   - 每个候选都要绑定图锚点
   - 不过 KiU Test 就拒绝

5. `L5 Refinement Loop`
   - 内部自检
   - 外部评测闸门
   - live feedback
   - failure 再反向 patch graph

这里最重要的，不只是“五层”，而是它的方向性：

- **契约自上而下**
- **证据自下而上**

这句很关键，因为它明确否定了“graph 自动长出 skill”的想法。

### 5.4 `use block` 是 KiU 的最小硬核对象

Notion 把 `use block` 定义成 KiU 的最小硬约束。它至少包含四部分：

- `trigger`
- `intake`
- `judgment_schema`
- `boundary`

其中最重要的不是 YAML 这种表面形式，而是它要求 skill 成为真正可调度的运行时对象：

- `trigger.patterns` 必须机器可匹配
- `intake.required` 必须明确
- `judgment_schema` 必须定义具体输出结构
- `boundary` 必须明确失败场景和不触发场景

也就是说，KiU 想产出的 skill 不是“一个解释性文档”，而是“一个可以被 dispatcher 解析和调用的契约单元”。

### 5.5 KiU Test 是真正的入库闸门

Notion 给出的三问非常关键：

1. `Trigger Test`
   - 能不能机器可读地说明“何时触发”

2. `Fire Test`
   - 给一个新情境，能不能输出具体判断

3. `Boundary Test`
   - 给一个错配情境，会不会主动拒绝触发

而且你已经把一件更重要的事补上了：

- 三问只是结构校验
- 真正的硬门槛还包括 `external evaluation corpus`

这个外部评测集包含：

- `real_decisions`
- `synthetic_adversarial`
- `out_of_distribution`

这一步是 KiU 和大部分“技能项目”最本质的区分之一，因为它把验证标准从“像不像原文”改成了“对不对真实决策”。

### 5.6 v0.1 MVP 的边界已经非常具体

你现在不是在做一个大而空的平台，而是在做一个很收敛的验证：

- 单 corpus：`《穷查理宝典》`
- 手工构造 5 个 skills
- 验证 `use` schema
- 验证 KiU Test
- 构建 `scenario_corpus`
- 构建 `evaluation_corpus`
- 与 `cangjie-skill` 的《穷查理宝典》版本盲评比较

当前 5 个 P0 候选 skill 是：

1. `circle-of-competence`
2. `invert-the-problem`
3. `margin-of-safety-sizing`
4. `bias-self-audit`
5. `opportunity-cost-of-the-next-best-idea`

这个边界比我上一版记录里想得更清楚：你现在要验证的不是整条自动流水线，而是**“契约化 skill”这个最小范式是否成立**。

### 5.7 数据库已经不是空壳，而是有真实样例

当前导出里已经能看到：

- `Domain Profiles`
  - `default`
  - `investing`
  - `engineering`

- `Skills Registry`
  - 5 个 P0 候选已建档
  - `circle-of-competence` 已进入 `Under Evaluation`

- `Usage Traces`
  - 已有 Buffett / Munger 的历史案例

- `Evaluation Cases`
  - 已有 `real_decision`
  - 已有 `adversarial`
  - 已有 `ood`

这说明 KiU 不是还停在概念层，而是已经开始形成“契约 + 轨迹 + 评测”的完整雏形。

### 5.8 一个特别关键的新洞见：领域策略必须一等化

`Domain Profiles` 里最值得注意的是 `investing`：

- `preserve_contradiction = Yes`
- `union_mode = disagreement_only`
- `cross_domain_evidence` 权重降低
- `predictive_power` 权重提高

这不是参数细节，而是在表达：

- 不同领域不能共用一套蒸馏逻辑
- 投资这类领域，本来就应该保留矛盾，而不是强行收敛成统一答案

这使 KiU 不只是“book-to-skill”，而是在朝“domain-sensitive judgment system”走。

## 6. 目前还缺的关键信息

### 6.1 还不清楚 KiU 第一阶段的主战场

下一轮需要尽快明确：

- KiU 第一版主要处理什么知识源：目前明确是“单书 dogfood”，但中期是否坚持书为主，还是扩展到混合 corpus，尚未确定
- KiU 第一版最小产物是什么：现在更接近“5 个经评测的 reference skills”，但项目仓库最终是否以 research prototype、skill pack、还是 runtime system 形式落地，还没拍板
- KiU 第一版的使用宿主是什么：Notion 中提到 v0.5 才会上 MCP server + dispatcher，因此早期宿主形态仍待定

## 7. 下一步建议对话焦点

下一轮沟通建议优先收敛三件事：

1. 你想让 KiU 先成为“研究型方法仓库”，还是尽快成为“可运行的 skill 系统”
2. 当前这 5 个 P0 skill 中，哪些是你真正相信值得继续推进的，哪些只是占位
3. 你接下来希望我重建的是哪一层：仓库结构、SKILLS 规范、数据目录，还是整套 v0.1 dogfood 工程骨架

如果这三件事收敛了，后面再重新生成 KiU 的 SKILLS，会比直接开写稳很多。
