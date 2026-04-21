# Knowledge in Use (KiU)

<aside>
🔥

**Core Principle · Knowledge in Use**

*If it can't fire, it's not knowledge. It's notes.*

</aside>

**KiU** 是一个把语料变成**可执行 skill** 的流水线 —— 不是摘要、不是知识图谱、不是检索索引。每一条 skill 都携带机器可读的契约、真实的使用轨迹,并且必须通过对**语料外真实决策**的评测。

## 为什么需要 KiU

现有路线都在同一个点失败:

| 路线 | 产出 | 问题 |
| --- | --- | --- |
| RAG / 知识图谱 | 结构化描述 | 描述世界,不会触发 |
| 读书笔记 | 压缩摘要 | 被动,不会被情境调用 |
| cangjie-skill (RIA-TV++) | 单书蒸馏技能 | 一次性流水,无 loop,无外部评测 |
| Graphify | 语料知识图 | 表征层,不是执行层 |
| **KiU** | **带契约 + 轨迹的可执行 skill** | **在新情境下真正触发,用现实检验** |

## The KiU Test · 三问

每一条候选 skill 必须全部通过才能入库:

1. **Trigger Test** —— 能否机器可读地说明「什么情境下触发」?
2. **Fire Test** —— 给一个符合 trigger 的新情境,能否输出**具体判断**?
3. **Boundary Test** —— 给一个**故意错配**的情境,它会不会主动拒绝触发?

任何一问失败 → `rejected/`,附拒绝理由。

## 架构一览

五层。契约自上而下,证据自下而上。

1. **L1 · Input** — 双 corpus(知识 + 场景)+ 评测 corpus
2. **L2 · Graph** — Graphify 驱动,双图通过 activation edges 连接
3. **L3 · Strategy Router** — 领域敏感的策略层(一等公民)
4. **L4 · KiU Extraction** — 契约优先,图锚定
5. **L5 · Refinement Loop** — 内部自检 + 外部评测闸门 + 活使用反馈

## 工作区导航

### 📖 核心文档

- [Philosophy · Knowledge in Use](Knowledge%20in%20Use%20(KiU)/Philosophy%20%C2%B7%20Knowledge%20in%20Use%20be39d335800e46a68d755e28deaf021d.md) —— 核心哲学、终极指标、对比矩阵
- [Architecture · Five Layers](Knowledge%20in%20Use%20(KiU)/Architecture%20%C2%B7%20Five%20Layers%2080a6f893ec274503b4ba6e6112ce88d5.md) —— L1→L5 分层设计与数据流
- [Skill Contract Schema · `use` block](Knowledge%20in%20Use%20(KiU)/Skill%20Contract%20Schema%20%C2%B7%20use%20block%205364dbd0439442e8b4319c55fcbede16.md) —— 机器可读契约的完整 schema
- [The KiU Test · 三问与外部评测](Knowledge%20in%20Use%20(KiU)/The%20KiU%20Test%20%C2%B7%20%E4%B8%89%E9%97%AE%E4%B8%8E%E5%A4%96%E9%83%A8%E8%AF%84%E6%B5%8B%2042e1662a734a4e93ac1d7a7b727171ce.md) —— 闸门规则与评测方法学
- [Roadmap · MVP & Beyond](Knowledge%20in%20Use%20(KiU)/Roadmap%20%C2%B7%20MVP%20&%20Beyond%20c58423484cbe479e8b5d4f9474390033.md) —— v0.1→v0.5 路线图与当前扣针

### 🗄️ 数据库

- [](Knowledge%20in%20Use%20(KiU)/Domain%20Profiles%2029be6db183ff441083bb09cd784c5685.md) —— 领域策略配置 (已种: default / investing / engineering)
- [](Knowledge%20in%20Use%20(KiU)/Skills%20Registry%206f794433a93546668d6708e167d93cb8.md) —— skill 总库与 pipeline 看板 (已种 5 个 P0 候选)
- [](Knowledge%20in%20Use%20(KiU)/Usage%20Traces%20830f937243404f7ab3d0ebd9e06c7482.md) —— 每条 skill 的使用轨迹 (目标 ≥3/skill)
- [](Knowledge%20in%20Use%20(KiU)/Evaluation%20Cases%205a4b3c0a36e24cb3bc9fe0083b6e6ede.md) —— KiU Test 与外部评测的用例库

### 🎯 下一步 (v0.1 MVP)

1. 在 [](Knowledge%20in%20Use%20(KiU)/Skills%20Registry%206f794433a93546668d6708e167d93cb8.md) 的 **v0.1 MVP** 视图中,逐条为 5 个 P0 skill 写出 `use` block (照 Contract Schema 格式)
2. 每条 skill 至少挂 ≥3 条 [](Knowledge%20in%20Use%20(KiU)/Usage%20Traces%20830f937243404f7ab3d0ebd9e06c7482.md) (优先 historical)
3. 在 [](Knowledge%20in%20Use%20(KiU)/Evaluation%20Cases%205a4b3c0a36e24cb3bc9fe0083b6e6ede.md) 建立 50 条用例: 20 real_decision + 20 synthetic_adversarial + 10 out_of_distribution
4. 逐条跑 KiU Test 三问,更新 Stage
5. 盲评对比 cangjie-skill 的 poor-charlies-almanack-skill (12 条)

## 状态

**当前阶段**:哲学骨架完成,MVP 已界定。  

**首个 dogfood corpus**:《穷查理宝典》(直接对标 cangjie-skill 的 12-skill 版本,便于 A/B)。  

**创建者**:@深蓝

[Philosophy · Knowledge in Use](Knowledge%20in%20Use%20(KiU)/Philosophy%20%C2%B7%20Knowledge%20in%20Use%20be39d335800e46a68d755e28deaf021d.md)

[Architecture · Five Layers](Knowledge%20in%20Use%20(KiU)/Architecture%20%C2%B7%20Five%20Layers%2080a6f893ec274503b4ba6e6112ce88d5.md)

[Skill Contract Schema · `use` block](Knowledge%20in%20Use%20(KiU)/Skill%20Contract%20Schema%20%C2%B7%20use%20block%205364dbd0439442e8b4319c55fcbede16.md)

[The KiU Test · 三问与外部评测](Knowledge%20in%20Use%20(KiU)/The%20KiU%20Test%20%C2%B7%20%E4%B8%89%E9%97%AE%E4%B8%8E%E5%A4%96%E9%83%A8%E8%AF%84%E6%B5%8B%2042e1662a734a4e93ac1d7a7b727171ce.md)

[Roadmap · MVP & Beyond](Knowledge%20in%20Use%20(KiU)/Roadmap%20%C2%B7%20MVP%20&%20Beyond%20c58423484cbe479e8b5d4f9474390033.md)

[Domain Profiles](Knowledge%20in%20Use%20(KiU)/Domain%20Profiles%2029be6db183ff441083bb09cd784c5685.csv)

[Skills Registry](Knowledge%20in%20Use%20(KiU)/Skills%20Registry%206f794433a93546668d6708e167d93cb8.csv)

[Usage Traces](Knowledge%20in%20Use%20(KiU)/Usage%20Traces%20830f937243404f7ab3d0ebd9e06c7482.csv)

[Evaluation Cases](Knowledge%20in%20Use%20(KiU)/Evaluation%20Cases%205a4b3c0a36e24cb3bc9fe0083b6e6ede.csv)