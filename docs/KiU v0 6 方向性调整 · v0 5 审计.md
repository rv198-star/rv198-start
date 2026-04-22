# KiU v0.6 方向性调整 · v0.5 审计 · W1 工单（开发团队交接版）

<aside>
📌

**本文档范围**：(1) 说明 v0.6 为什么从「foundation 收官」切到「生产管线自研」；(2) 沉淀 v0.5 的三条参照线审计结论；(3) 给出 4 周融合路径的整体骨架；(4) **只详细展开 W1 的工单**，W2–W4 等 W1 实测数据出来后再定稿。

**Owner**：`<待指定>`

**优先级**：P0（启动即最高优先级）

**预计 W1 工作量**：1 人 5 人日

</aside>

# Part 0 · 决策摘要

| 决策项 | 结论 |
| --- | --- |
| 战略路径 | **Path B · 自研生产管线**，不走 ecosystem 集成 |
| 项目定位 | **自用工具**，不做社区发布、不做推广 |
| 融合来源 | Graphify（图模型核心）+ cangjie-skill（蒸馏方法论核心），剥离外围 |
| 节奏 | **4 周 roadmap，按周 gate**。本文档只详细定稿 W1 |
| 前置红线 | Attribution 必须从 Day 1 写对，理由见 Part 1.5 |
| v0.6 目标版本 | 单本书（穷查理宝典）端到端跑通：原书 → graph.json（三态边）→ 15+ skills（带 Agentic/Workflow 分流）→ 三层审查报告 |

---

# Part 1 · v0.6 方向性调整背景

## 1.1 为什么从 v0.5 切到生产管线自研

v0.5 完成了 foundation 收官：多域 bundle + 跨 bundle 图合并 + Agentic/Workflow 边界 + 三层审查评分。但把 v0.5 放到三把尺子下量，**结构完整、能力不完整**：

- **Graphify 的精髓实现度 ~25%**：吃了图骨架和命名空间合并，没吃自动提取 / 出处三态 / always-on 集成。
- **cangjie-skill 的精髓实现度 ~45%**：Schema 层比 cangjie 更规整，但**生产管线层是 0 分**——KiU 当前的 skill 都是人工写的，`generate_candidates.py` 只从已结构化的 seed node 扩写，不是从原书抽取。
- **Agentic/Workflow 平衡 ~60%**：v0.5 最原创、最扎实的一条线，但需要更多 workflow 候选来证明规模化。

**最直接的差距证据**：同一本《穷查理宝典》，cangjie 已产 **12 个 skill**，KiU 只有 **5 个 published + 人工写**。schema 再工程化，生产不出量就没有规模效应。

## 1.2 路径 A 被否决 → 路径 B 的战略确认

v0.5 评审时我提过两条路径：

- 路径 A（ecosystem 集成）：KiU 做 cangjie/Graphify 的质检 + 路由层。**已被用户否决**——不想集成，想替代并超越。
- 路径 B（自研 pipeline）：吸收两者核心，自己做蒸馏。**本次确认走这条**。

## 1.3 为什么「拿来主义」在自用场景下合理

三个前提同时满足：

1. **法律上**：两个项目都是 MIT，允许 fork / 复用 / 商用，只需保留版权声明。
2. **定位上**：自用工具，不追求社区动量、传播、署名权。
3. **范围上**：只要核心，**不要外围**——Graphify 的 14 个 IDE 集成、25 种 tree-sitter 语言、MCP server、i18n、PyPI 打包全部砍掉；cangjie 的推广渠道、已生产的 6 个 skill pack 全部不拿。

在这三个前提下，拿来主义不再涉及社区信任问题，退化为**合规的代码复用 + 方法论借鉴**。

## 1.4 核心 vs 外围的明确切割

| 项目 | 要的核心 | 不要的外围 |
| --- | --- | --- |
| cangjie-skill | RIA-TV++ 6 阶段方法论 · 5 个 extractor 的 prompt 设计 · 三重验证规则（跨域 ≥ 2 / 预测力 / 独特性）· Zettelkasten 链接 · 压力测试（诱饵题）· 模板文件 | 6 个已生产的 skill pack 本体 · 作者推广渠道 · 公众号 / 小红书内容 |

## 1.5 前置红线：Attribution 必须 Day 1 做对

<aside>
⚠️

**即便自用，Attribution 必须从 W1 Day 1 做对。**

理由：任何时候想把这个 repo 从私有切到公开（哪怕只是发一篇 blog），attribution 必须在——**回头补极其困难**，且会留下时间戳证据不利。前置做 1 小时，后置补 1 周。

具体要求见 W1 工单 **KIU-608**。

</aside>

## 1.6 自用定位下的时间重估

原估算（发布级 / 社区级 Path B）：**6–8 周**。

自用定位剥离以下后：

- 面向用户的 README / docs / i18n · PyPI 发布 / 安装脚本 · IDE 集成 / MCP · 完整单测覆盖率 · 方法论命名原创性与差异化话术 · Community positioning

**净开发量 ≈ 3–4 周，1 人**。

---

# Part 2 · v0.5 审计结论（沉淀版）

## 2.1 三条参照线的精髓实现度对比

| 参照线 | 精髓度 | 吃透了什么 | 没吃透什么 | Graphify | **25%** | graph.json 持久化 · 跨 bundle 合并 · namespacing · canonical hash | EXTRACTED/INFERRED/AMBIGUOUS 三态 · Leiden 聚类 · 两段式提取 · always-on 集成 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cangjie-skill | **45%** | Contract 四件套（比 cangjie 更严格）· 跨 bundle relations（external: 命名空间）· KiU Test 三栅 | Adler 整书理解 · 5 extractor · 三重验证筛选 · end-to-end 书→skill pipeline | Agentic/Workflow 平衡 | **60%** | routing_rules 两维路由 · workflow_candidates 物理隔离 · [review.py](http://review.py) 评分纳入 workflow_boundary_factor | workflow_certainty 仍靠人工 hint · 实际 workflow 候选只有 1 个 · 规模化效益未证 |

## 2.2 v0.5 必须承认的三个事实

1. **v0.5 吃透了 schema 没吃透 pipeline**。结构完整，生产管线缺席。
2. **KiU 当前真正的原创贡献是 Agentic/Workflow 边界**，不是跨 bundle 图（后者是 Graphify-style，v0.5 只是命名空间实现）。
3. **穷查理同题对比 5 vs 12** 是不回避的生产力差距指标。

## 2.3 v0.5 保留 / 必须兼容的能力

v0.6 融合过程中，以下 v0.5 能力必须保留且不退化：

- 跨 bundle 图合并（`src/kiu_graph/merge.py`）→ v0.6 扩展到三态边兼容
- Agentic/Workflow 路由（`routing_rules` + `workflow_candidates/`）→ **v0.6 关键：把路由接到新 pipeline 的三重验证之后，作为筛选→分流一体化**
- 三层审查评分（`src/kiu_pipeline/review.py`）→ v0.6 作为 pipeline 终点
- 生产质量门（`artifact_quality: 0.78 / production_quality: 0.82`）→ v0.6 保留投资 domain profile 的硬门槛

---

# Part 3 · v0.6 整体 4 周路径（骨架，W2–W4 不定稿）

<aside>
🗺️

**本节只作为方向锚**。W2–W4 的详细工单等 W1 实测产出之后再定——因为 v0.4/v0.5 都出现过「原计划与实际交付 50% 偏移」，一次性排 4 周工单效率低。

</aside>

## 3.1 Merge Matrix（从哪个项目拿什么）

| 周次 | 目标 | 从 Graphify 拿 | 从 cangjie 拿 | 与 v0.5 融合点 |
| --- | --- | --- | --- | --- |
| W2 | 提取管线前半 | 两段式（deterministic → LLM）架构 | Adler 整书理解 · 5 extractor prompt（改写） | 新 `src/kiu_extract/`；复用 v0.5 LLM provider 抽象 |
| W4 | 端到端 + 独创融合 | — | — | **Agentic/Workflow 路由接在三重验证之后**；三层审查作 pipeline 终点；穷查理端到端对标 cangjie 12 → KiU 目标 15+ |

## 3.2 每周 gate 决策点

每周结束必须回答三个问题，满足才进入下一周：

1. 本周核心交付是否跑通？（有实测产物）
2. v0.5 既有能力是否回归？（测试套件通过）
3. 下一周的输入是否已就位？

## 3.3 v0.6 最终交付目标（W4 结束）

单本《穷查理宝典》喂进去 → 输出：

- `graph.json`（带 EXTRACTED/INFERRED/AMBIGUOUS 三态边 + 每条边 source_location）
- `GRAPH_REPORT.md`（god nodes + 社区 + surprising connections）
- **15+ KiU skills**（带 Agentic/Workflow 分流）
- `workflow_candidates/`（至少 2-3 个）
- `reports/three-layer-review.json`（带分数）

对标基线：cangjie 的 `poor-charlies-almanack-skill` 12 skills。

---

# Part 4 · W1 具体工单（详细版）

## W1 目标陈述

> **把 KiU 的图模型从 v0.5 的「手工策划节点 + 简单关系」升级为 Graphify-style 的「带出处坐标 + 三态可信度标记 + Leiden 聚类」模型，并产出第一份 GRAPH_[REPORT.md](http://REPORT.md)。**
> 

**不是 W1 要做的**（留给 W2+）：实际从原书文本中用 LLM 抽取节点/边。W1 只做 schema 升级 + 聚类 + 报告；数据仍从 v0.5 已有 graph.json 迁移。

## W1 工单清单

| ID | 标题 | P | 人日 | 依赖 | KIU-601 | graph.json schema v0.2 设计 | P0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KIU-602 | 验证器适配新 schema | P0 | 0.5 | 601 | KIU-603 | v0.5 两个 bundle graph 回填迁移 | P0 |
| KIU-604 | Leiden 聚类模块 | P0 | 1.0 | 601 | KIU-605 | GRAPH_[REPORT.md](http://REPORT.md) 生成器 | P0 |
| KIU-606 | CLI 命令 `build_graph_report.py` | P1 | 0.25 | 605 | KIU-607 | 穷查理 bundle W1 产出 audit | P0 |
| KIU-608 | Attribution 前置（LICENSES + NOTICE） | P0 | 0.5 | —（第一个做） | **合计** | **4.75 人日** |  |

---

### KIU-601 · graph.json schema v0.2 设计

**背景**：v0.5 的 graph.json 节点/边没有出处坐标，边没有可信度，不能区分「原文抽取」vs「LLM 推断」。这是 Graphify 最核心的增强。

**具体改动**：

- 新增字段（nodes）：
    - `source_file: str`（如 `sources/poor-charlies-core.md`）
    - `source_location: { line_start: int, line_end: int } | null`
    - `extraction_kind: "EXTRACTED" | "INFERRED" | "AMBIGUOUS"`
- 新增字段（edges）：
    - `source_file: str | null`
    - `source_location: {...} | null`
    - `extraction_kind: "EXTRACTED" | "INFERRED" | "AMBIGUOUS"`
    - `confidence: float`（`[0.0, 1.0]`，EXTRACTED 默认 1.0，INFERRED 要求 < 0.95，AMBIGUOUS < 0.7）
- Bump `graph_version` 从 `kiu.graph/v0.1` 到 `kiu.graph/v0.2`
- 合并图的 `kiu.graph.merge/v0.1` 也要 bump 到 `v0.2` 兼容三态

**交付物**：`docs/kiu-skill-spec-v0.6.md`（新建）中的 graph schema 章节 + JSON Schema 文件 `schemas/graph-v0.2.json`

**验收标准**：Schema 文档可评审；JSON Schema 对现有投资/工程 bundle 的 graph.json（回填后）validate 通过。

---

### KIU-602 · 验证器适配新 schema

**具体改动**：

- `src/kiu_validator/core.py` 中新增对 v0.2 graph 的校验：
    - `extraction_kind` 必须在 enum 内
    - `confidence` 必须在 `[0.0, 1.0]`
    - `extraction_kind == "EXTRACTED"` 时 `source_file` 必填
    - 发布态 bundle 中 `extraction_kind == "AMBIGUOUS"` 的边数量 / 总边数 > 20% 触发 warning
- 保留对 v0.1 graph 的向后兼容读取（迁移过程中需要）

**验收标准**：59+ 个现有单测通过；新增 8-10 个针对 v0.2 schema 的校验用例全部通过。

---

### KIU-603 · v0.5 两个 bundle graph 回填迁移

**背景**：投资和工程两个 bundle 的 graph.json 是 v0.1 schema，需要回填新字段才能跑通 W1 的 GRAPH_REPORT 生成。

**具体改动**：

- 新增脚本 `scripts/migrate_graph_v01_to_v02.py`
- 回填策略：
    - 所有现有节点/边默认标 `extraction_kind: "EXTRACTED"`, `confidence: 1.0`（因为它们都是手工策划的，都算「原文找到的」）
    - `source_file` 回填为 bundle 内对应 [SKILL.md](http://SKILL.md) 或 source 文件路径（按 skill_id 映射）
    - `source_location` 可 null（无精确行号）
- 在两个 bundle 各跑一次，commit 结果

**验收标准**：迁移后两个 bundle graph.json 通过 v0.2 validator；graph_hash 重算并更新到 manifest.yaml。

---

### KIU-604 · Leiden 聚类模块

**具体改动**：

- 新增依赖：`leidenalg` + `igraph`（推荐组合）或 `networkx` + `python-louvain`（后备）
- 新增模块 `src/kiu_graph/clustering.py`：
    - `run_leiden(graph_doc) -> list[Community]`
    - Community 结构：`{id, node_ids, modularity_score, top_node_id}`
    - 参数：`resolution=1.0`（默认）；小图（<20 节点）自动降到 `0.7` 避免过拟合
- 集成到合并图：merged graph 的 communities 也跑一遍 Leiden 重算

**验收标准**：投资 bundle 单独跑出 3-5 个 community；合并图跑出 5-8 个（跨域社区可识别）；输出稳定（同输入多次跑 community 划分相同）。

---

### KIU-605 · GRAPH_[REPORT.md](http://REPORT.md) 生成器

**具体改动**：

- 新增模块 `src/kiu_graph/report.py`：
    - `generate_graph_report(graph_doc) -> str`（markdown）
- 报告内容（对齐 Graphify 的 GRAPH_[REPORT.md](http://REPORT.md)）：
    1. **God Nodes**：度数排名 top 5 节点 + 简短描述
    2. **Communities**：每个社区的节点清单 + 中心节点 + 建议命名（LLM 可选，W1 先用规则命名）
    3. **Surprising Connections**：跨社区的 INFERRED 边 top 3
    4. **Suggested Questions**：基于 god nodes 自动生成 3-5 个 probing 问题（规则模板即可）
- 模板放 `templates/graph-report.md.jinja2`

**验收标准**：穷查理 bundle 的 GRAPH_[REPORT.md](http://REPORT.md) 人工阅读 ≤ 5 分钟能理解 bundle 结构；字数 800-1500；god nodes 与预期（比如 bias-self-audit, circle-of-competence）一致。

---

### KIU-606 · CLI 命令 `build_graph_report.py`

**具体改动**：

- 新增脚本 `scripts/build_graph_report.py`
- 参数：`--bundle <path>` 或 `--merged <path1> <path2> ...`；`--output <path>`（默认 `GRAPH_REPORT.md` 放 bundle 根）
- 输出同时更新 `manifest.yaml` 中的 `graph_report.path` 字段

**验收标准**：命令可单独运行；产出的 md 与 KIU-605 调用输出一致。

---

### KIU-607 · 穷查理 bundle W1 产出 audit

**背景**：这是 W1 的 gate——决定是否启动 W2。

**具体步骤**：

1. 穷查理投资 bundle 跑完 KIU-603 迁移 + KIU-604 聚类 + KIU-605 报告生成
2. 人工阅读 `GRAPH_REPORT.md` 并记录：
    - God nodes 是否符合直觉？
    - Communities 划分是否合理？
    - Surprising connections 是否有信息量？
3. 合并投资 + 工程 bundle，重跑 report，检查跨域社区
4. 写一份简短 audit 报告 `reports/w1-audit.md`（200-400 字即可）

**验收标准**：

- ✅ GRAPH_[REPORT.md](http://REPORT.md) 生成成功且人工判断可用
- ✅ v0.5 的 CI + 所有既有测试通过（回归零退化）
- ✅ audit 报告明确 go / no-go to W2

---

### KIU-608 · Attribution 前置

**W1 Day 1 必须第一个做完的工单**。

**具体改动**：

- 新建目录 `LICENSES/`
    - `LICENSES/graphify-MIT.txt`（从 safishamsi/graphify 的 LICENSE 整文件拷贝）
    - `LICENSES/cangjie-skill-MIT.txt`（从 kangarooking/cangjie-skill 的 LICENSE 整文件拷贝）
- 新建 `NOTICE.md` 根目录：
    
    ```
    # NOTICE
    
    KiU incorporates concepts and patterns from the following MIT-licensed projects:
    
    - safishamsi/graphify (MIT) — graph.json data model (EXTRACTED/INFERRED/AMBIGUOUS edge provenance,
      source_location), two-pass extraction architecture (deterministic → LLM), Leiden community
      detection usage pattern, GRAPH_REPORT.md output format. See LICENSES/graphify-MIT.txt.
    
    - kangarooking/cangjie-skill (MIT) — RIA-TV++ distillation methodology (Adler book
      comprehension, parallel 5-extractor, triple verification gate, Zettelkasten linking, adversarial
      stress test), SKILL.md / INDEX.md / BOOK_OVERVIEW.md template structure. See
      LICENSES/cangjie-skill-MIT.txt.
    
    KiU's original contributions (not derived from the above) include the Agentic/Workflow routing
     boundary, the three-layer review scoring (source bundle + generated bundle + usage outputs),
     the cross-bundle graph merge with namespaced IDs, and the Contract schema (trigger / intake /
     judgment_schema / boundary) as the published skill contract.
    ```
    
- `README.md` 增加「Acknowledgments」章节指向 `NOTICE.md`
- 任何**直接参考了**特定 Graphify / cangjie 文件写出来的 KiU 文件（W2+ 开始陆续出现），在文件头添加注释：
    
    ```
    # Portions of this file's design are derived from <project>/<path> (MIT).
    # See LICENSES/<project>-MIT.txt and NOTICE.md.
    ```
    

**验收标准**：

- ✅ 两个 LICENSE 原文存在且与上游一致
- ✅ [NOTICE.md](http://NOTICE.md) 存在且描述准确
- ✅ README 有 Acknowledgments 链接

---

## W1 验收 gate（KIU-607 完成时评估）

必过项：

- [ ]  KIU-608 attribution 三件齐全
- [ ]  两个 bundle graph 成功迁移到 v0.2 schema 并通过 validator
- [ ]  Leiden 聚类在穷查理 bundle 跑出合理社区
- [ ]  GRAPH_[REPORT.md](http://REPORT.md) 人工阅读可用
- [ ]  跨 bundle 合并图跑出跨域社区
- [ ]  v0.5 所有既有测试通过，零回归

满足全部 → 进入 W2 工单编写；任一失败 → 停下写补救方案，W2 延迟。

---

# Part 5 · 已识别的 W1 风险与开放问题

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| `leidenalg` / `igraph` 在某些 OS 下编译较麻烦 | W1 启动受阻 | 准备 `python-louvain` 作为 fallback（质量略降但能跑） |
| 小图（穷查理 bundle 当前 graph 节点估计 20-30 个）Leiden 可能过度分裂 | 社区无意义 | KIU-604 里加 resolution 自适应逻辑（<20 节点用 0.7） |
| v0.1 → v0.2 迁移后 graph_hash 变化，验证器可能误报 | 误伤 CI | KIU-603 迁移时同步更新 manifest.yaml 的 graph_hash，单次提交 |
| 三态边在 W1 全部回填为 EXTRACTED（因为都是人工手搓的）意味着三态能力在 W1 其实没被真正使用 | 看起来像「schema 加了但没用」 | **这是故意的**——W1 只升级 schema 容器，真正使用三态要等 W2 LLM 抽取上线后；W1 的价值在于为 W2 做好输出端准备 |

## 开放问题（留到 W2 决定）

1. LLM 抽取边时，`confidence` 如何量化？两种方案：
    
    (a) LLM 自报 confidence → 易虚高；
    
    (b) 基于 prompt 工程让 LLM 标「在原文第几行看到 / 根据什么推断」→ 可审计但慢。
    
    **建议 W2 试 (b)。**
    
2. cangjie 的 5 个 extractor prompt 是中文书 + 中文 LLM 语境调出来的，本地化到 KiU 的 setup 要多少 prompt 重调时间？
    
    **W2 预留 1 人日做 prompt 本地化。**
    
3. 整书理解（Adler）这一步在 KiU 要不要产出 `BOOK_OVERVIEW.md` 这种独立文件？还是直接作为 LLM 抽取的 context 喂进去？
    
    **倾向于独立文件**（可审计），但 W2 再定。
    

---

# Part 6 · 关键文件位置

- **本文档**：v0.6 方向性决定 + W1 工单（本页）
- **v0.5 评审聊天历史**：当前 thread
- **v0.5 · v0.4 开发团队交接版**：[KiU Skills · v0.3 评审报告 + v0.4 开发工单（开发团队交接版）](https://www.notion.so/KiU-Skills-v0-3-v0-4-1adb0c97056c43d6bafba041cbc1a86a?pvs=21)（前置参考，v0.4 → v0.5 的上下文）
- **内部 v0.4 路线**：[v0.3 评估 · v0.3.1 热修 · v0.4 路线规划](https://www.notion.so/v0-3-v0-3-1-v0-4-1ef15fbce15647ceb514c3c6e9940e14?pvs=21)
- **v0.3 Dev Brief**：[https://www.notion.so/236](https://www.notion.so/236)
- **KiU Hub**：[Knowledge in Use (KiU)](https://www.notion.so/Knowledge-in-Use-KiU-ca57eeb637c04bd6a62e295fd6d089a0?pvs=21)

---

<aside>
🚦

**W1 准备启动条件**：(1) Owner 指定完成；(2) 本文档 Part 4 工单评审通过；(3) KIU-608 attribution 优先开做，不阻塞其他工单但必须第一个合并。

</aside>