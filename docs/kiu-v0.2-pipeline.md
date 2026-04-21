# KiU v0.2 Candidate Pipeline

## 目标

KiU v0.2 不做 graph 构建，不做自动发布，也不做 runtime dispatcher。  
这一版只解决一件事：

> 把已经发布的 graph snapshot 稳定地转成一批可审阅、可追踪、可继续 loop 的 skill candidates。

当前 dogfood 目标是 `bundles/poor-charlies-almanack-v0.1`。

## 设计思路

### 1. 先做 graph-to-candidate，而不是 graph-to-publish

v0.2 明确把“候选生成”和“正式发布”切开。

- graph snapshot 负责提供结构化证据底座
- candidate pipeline 负责提出 draft
- human review + eval loop 才决定是否进入 published

这样可以避免一条自动化链路把 graph 直接伪装成可发布 skill。

### 2. 核心原则是 workflow 确定性 × context 确定性

这条原则不是文档说明，而是结构化元数据：

- `workflow_certainty`
- `context_certainty`
- `recommended_execution_mode`
- `disposition`

含义：

- `workflow_certainty` 高：步骤清晰、判断逻辑接近脚本化
- `context_certainty` 高：输入上下文稳定、模糊度低

边界原则：

- `high/high` 不进入正式 KiU skill candidate
- 这类对象被降级为 `workflow_script_candidate`
- 它们仍然保留在 `workflow_candidates/` 中，便于审计和后续复查

这就是“Workflow 脚本”和 “LLM agentic skill” 的分界线。

### 3. v0.2 仍然坚持证据优先

自动生成的 candidate 不是轻量壳子，而是保留：

- `SKILL.md`
- `anchors.yaml`
- `eval/summary.yaml`
- `iterations/revisions.yaml`
- `candidate.yaml`

其中 `candidate.yaml` 是 v0.2 新增的机器侧记录，负责保存路由与执行建议。

### 4. deterministic 优先，llm-assisted 只保留接口

当前实现首先保证 deterministic 可重复运行：

- 同一 source bundle
- 同一 automation profile
- 同一 run id

会生成同形态输出。

`llm-assisted` 先作为 drafting mode 元数据入口保留，但不把成功路径建立在 LLM 调用之上。

## 目录结构

一次 pipeline 运行输出到：

```text
generated/<source-bundle-id>/<run-id>/
├── bundle/
│   ├── manifest.yaml
│   ├── graph/
│   ├── traces/
│   ├── evaluation/
│   ├── sources/
│   └── skills/<skill-id>/
│       ├── SKILL.md
│       ├── anchors.yaml
│       ├── candidate.yaml
│       ├── eval/summary.yaml
│       └── iterations/revisions.yaml
├── workflow_candidates/<candidate-id>/
│   ├── candidate.yaml
│   └── README.md
└── reports/
    └── metrics.json
```

## automation.yaml

每个 source bundle 自带一个 `automation.yaml`，负责声明：

- 允许作为 seed 的 graph node 类型
- `max_candidates`
- `candidate_kinds`
- `routing_rules`
- `seed_overrides`

在 `poor-charlies-almanack-v0.1` 里，五个 principle 节点都映射到五个 gold skills，用来做第一轮 dogfood。

## 使用方式

在仓库根目录运行：

```bash
/Volumes/Data/miniconda3/bin/python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --output-root generated \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

生成后验证：

```bash
/Volumes/Data/miniconda3/bin/python3 scripts/validate_bundle.py generated/poor-charlies-almanack-v0.1/local-v0_2/bundle
/Volumes/Data/miniconda3/bin/python3 -m unittest tests/test_pipeline.py
```

## 当前范围

已经实现：

- source bundle 加载
- graph 归一化
- candidate seed 挖掘
- workflow/context 双轴路由
- deterministic candidate bundle 渲染
- generated bundle preflight
- metrics 报告

本版故意不做：

- graph 抽取
- 自动发布
- dispatcher / runtime 执行
- 自动修订闭环

## 下一步建议

v0.2 后续可以继续补三块：

1. `llm-assisted` drafting
   - 用于丰富 rationale、evidence summary、candidate diff，而不是替代 deterministic 结构
2. candidate diff / review UI
   - 更清楚地展示 generated candidate 与 gold/reference skill 的差异
3. loop-aware revision patching
   - 把 eval 失败模式更系统地反写到 revision log 和 graph patch 建议中
