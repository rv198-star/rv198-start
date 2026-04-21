# Architecture · Five Layers

<aside>
📌

**架构原则**: 契约自上而下,证据自下而上。Graph 不生成 skill —— Graph 服务于 skill 契约。

</aside>

## 五层总览

```
┌──────────────────────────────────────────────────────────────┐
│ L1 · INPUT LAYER                                                   │
│                                                                    │
│   knowledge_corpus/    书籍、论文、录像录音 (传统"供给")          │
│   scenario_corpus/     真实决策记录、案例库 (新的"需求")         │
│   evaluation_corpus/   语料外真实决策 (验证铁底)                │
│   manifest.yaml        domain / audience / sources               │
└──────────────────────────┬───────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────┐
│ L2 · GRAPH LAYER                                                   │
│                                                                    │
│   knowledge.graph.json  ⇄  scenario.graph.json                  │
│             ╲                  ╱                                  │
│              activation_edges (场景 ↔ 知识)                        │
│                                                                    │
│   - tree-sitter + LLM semantic + whisper                           │
│   - EXTRACTED / INFERRED / AMBIGUOUS edge tagging                  │
│   - Leiden 聚类 (固定 seed) + God Nodes                             │
│   - 版本化、hash 化、可 diff                                        │
└──────────────────────────┬───────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────┐
│ L3 · STRATEGY ROUTER  (一等公民)                                   │
│                                                                    │
│   输入: domain + audience + graph_stats                           │
│   输出: Policy 对象 → 传给 L4/L5                                 │
│                                                                    │
│   Policy 决定 7 件事:                                              │
│     1. union_mode (full / disagreement / parallel / observation)   │
│     2. mandatory_metadata (era / scale / school / paradigm)        │
│     3. verification_weights                                        │
│     4. preserve_contradiction                                      │
│     5. ria_dimensions (R/I/A1/A2/E/B 启用与权重)                     │
│     6. extraction_targets                                          │
│     7. convergence_criterion                                       │
└──────────────────────────┬───────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────┐
│ L4 · KiU EXTRACTION  (抽“可触发契约”,不是抽“原则陈述”)              │
│                                                                    │
│   候选源: God Nodes + 社区中心 + activation 热点                    │
│   每个候选 → 绑定 ≥1 个 node_id                                   │
│   验证: 图查询实现,LLM 只做语义改写                                 │
│                                                                    │
│   产出格式: SKILL.md (use block + traces + rationale + anchors)   │
│   不满足 KiU Test 三问 → 拒绝                                       │
└──────────────────────────┬───────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────┐
│ L5 · REFINEMENT LOOP                                               │
│                                                                    │
│   a) 内部自检 (test-prompts.json)                                 │
│   b) external eval gate (硬性门槛)                                 │
│       real_decisions / synthetic_adversarial / OOD                │
│   c) live execution feedback (skill 被调用 → outcome 回流)         │
│                                                                    │
│   failure set → gap analysis → graph patch → re-extract             │
│   收敛判定: 按 Router 给的 convergence_criterion                    │
└──────────────────────────┬───────────────────────────────────────┘
                          ↓
┌───────────────────────────────────────────────────────────────┐
│ OUTPUT · Skill Pack                                                │
└───────────────────────────────────────────────────────────────┘
```

## 架构反转: 为什么 Graph 不生成 Skill

错误模式 (我们最初的方案):

```
corpus → graph → skill     (supply-push)
         ↑↑↑
      skill 继承了图的 representation 属性,变成"更好的笔记"
```

KiU 的模式:

```
skill contract 是目标契约
     ↓
定义需要什么样的证据
     ↓
graph 提供经过验证的证据           (demand-pull)
     ↓
契约被证据支撑 → skill 入库
```

就像类型系统不生成程序、类型系统保证程序正确性 —— **Graph 不生成 skill、Graph 保证 skill 的可溯性和契约成立性**。

## 关键模块职责

### L2 · Graph Layer

- **不是**: skill 来源
- **是**: provenance 的存放处、验证查询的执行引擎、矛盾检测的结构基础

### L3 · Strategy Router

- **不是**: 角落里的 config 文件
- **是**: 独立模块 · 有自己的 API 和测试 · 每条 pipeline 必经的决策层

### L4 · KiU Extraction

- **不是**: RAG 优化
- **是**: 契约符号的构造器 + 图查询的组持者
- **核心约束**: 不过 KiU Test 三问 → 不出现在最终 skill pack

### L5 · Refinement Loop

- **不是**: "多跑几轮就是 loop"
- **是**: 根据失败情况**反向打 graph patch**的结构化机制 · external eval corpus 作为硬性门槛

## Dogfood 阶段的简化 (v0.1)

<aside>
⚠️

v0.1 MVP 不要上来就把五层全部自动化。手工走一遍整个流程,验证契约 schema 和 KiU Test 有效后,再竞个自动化。详见 [Knowledge in Use (KiU)](../Knowledge%20in%20Use%20(KiU)%20ca57eeb637c04bd6a62e295fd6d089a0.md) 的 Roadmap。

</aside>