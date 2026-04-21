# Philosophy · Knowledge in Use

<aside>
💡

Knowledge isn't what you've read. **Knowledge is what fires when you face a decision.**

</aside>

## 这条原则从哪里来

起点是 cangjie-skill README 里一段直击要害的判断:

> 看了很多书但用不起来 —— 知识停留在"读过"层面,无法在真实决策中被调用。书摘/读书笔记只是压缩,不是结构化复用。需要**面向执行而非面向阅读**的蒸馏方法。
> 

Graphify 再强,本质也只是把这个"压缩摘要"做得更精致 —— 它给你一张更好的地图,但**地图不会替你走路**。要真正跨过这道坎,项目的整个姿态必须倒过来: 从"描述知识"转向"契约承诺"。

## representation 与 contract 的根本区别

| 维度 | 笔记 / RAG / 知识图谱 | 可执行思想 (KiU) |
| --- | --- | --- |
| 回答的问题 | "这是什么?它和什么连着?" | "此刻我该怎么判断?" |
| 主语 | 作者 / 文本 | 使用者 / 情境 |
| 激活方式 | 被查询 (pull) | 被情境触发 (push) |
| 失效方式 | 信息错漏 | 情境错配、边界外使用、组合失灵 |
| 验证方式 | 与原文对齐 | **与真实决策的结果对齐** |
| 单位形态 | 节点 / 段落 / 摘要 | **闭包 / 契约 / 函数** |
| 处理未见情境 | 无关 | **必须处理** |

**一句话**: representation 是"关于世界的一份描述",contract 是"一份承诺 —— 当 X 情境发生,我会输出 Y 判断"。

## 这条原则如何贯穿项目

1. **命名**: KiU —— 名字本身即立场声明
2. **架构反转**: Graph 是 contract 的**证据层**,不是 contract 的生产者
3. **入库门槛**: The KiU Test 三问,不过关即拒收 (见 [Knowledge in Use (KiU)](../Knowledge%20in%20Use%20(KiU)%20ca57eeb637c04bd6a62e295fd6d089a0.md))
4. **单位形态**: skill = 契约闭包 + 使用轨迹,不是 markdown 文档
5. **验证方式**: 对真实决策的一致率,不是对原文的保真度
6. **拒绝清单**: Atlas / Forge / Prism 这些"隐喻名"全部放弃 —— 因为它们没有立场,只是好看

## 和两个前作的关系 (立场切清)

| 维度 | 与前作关系 |
| --- | --- |
| 从 Graphify **吸收** | 多模态摄取、tree-sitter、Leiden 聚类、边置信度标签、图作持久 source of truth、MCP 接口 |
| 从 Graphify **剥离** | "给 AI 助手做 corpus 地图"的定位 —— KiU 要产 skill,不只是产图 |
| 从 cangjie-skill **吸收** | RIA++ 六维模板、三重验证机制、Zettelkasten 链接、压力测试思路 |
| 从 cangjie-skill **剥离** | 单书一次性流水线、领域无关假设、skill 产物不含底层证据 |
| 从 Yeadon 版仓颉 **吸收** | "内在矛盾"作为一等维度、"信念形成故事"、认知边界声明 |
| **全新引入** | 策略路由、双 corpus、契约 schema、迭代 loop、external evaluation corpus、可验证 provenance chain |

## 口号

<aside>
🔥

**If it can't fire, it's not knowledge. It's notes.**

每个 PR、每次 skill 评审、每个新贡献者入门,都先念一遍这句话。

</aside>