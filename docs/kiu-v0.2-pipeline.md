# KiU v0.2 Candidate Pipeline

## 目标

KiU v0.2 不做 graph 构建，不做自动发布，也不做 runtime dispatcher。  
这一版解决两件连续的事：

1. 把已经发布的 graph snapshot 稳定地转成 candidate seeds
2. 默认以无人介入多轮迭代把这些 seeds 推向接近完成品的 candidate bundle

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

### 4. refinement scheduler 是默认上层入口

当前实现包含两层：

- `scripts/generate_candidates.py`
  - 底层 deterministic seed generator
- `scripts/build_candidates.py`
  - 默认推荐入口
  - 先生成 seeds，再执行 multi-round refinement scheduling

推荐入口默认是无人介入的 default unattended mode。人工 gate 只作为可选补充存在，不是默认依赖。

## 目录结构

一次 pipeline 运行默认输出到：

```text
/tmp/kiu-local-artifacts/generated/<source-bundle-id>/<run-id>/
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
    ├── metrics.json
    ├── production-quality.json
    ├── scorecard.json
    ├── final-decision.json
    └── rounds/
        └── <candidate-id>-round-01.json
```

source fixture 脚手架默认写到：

- `/tmp/kiu-local-artifacts/sources/<fixture-name>/bundle`

如果你希望改到另一处固定本地目录，设置 `KIU_LOCAL_OUTPUT_ROOT=/your/path`。
只有在需要显式覆盖时，才传 `--output-root /your/path`。

## automation.yaml

每个 source bundle 自带一个 `automation.yaml`，负责声明：

- 允许作为 seed 的 graph node 类型
- `max_candidates`
- `candidate_kinds`
- `routing_rules`
- `seed_overrides`
- `refinement_scheduler`
  - `min_rounds / max_rounds / patience`
  - `targets`
  - `weights`
  - `bonuses`
  - `mutable_surfaces`

在 `poor-charlies-almanack-v0.1` 里，五个 principle 节点都映射到五个 gold skills，用来做第一轮 dogfood。

## 使用方式

在仓库根目录运行：

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase2-smoke
```

如果你只想看 deterministic seed，不跑 refinement：

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

生成后验证：

```bash
python3 scripts/validate_bundle.py /tmp/kiu-local-artifacts/generated/poor-charlies-almanack-v0.1/local-v0_2/bundle
python3 -m unittest tests/test_pipeline.py
```

## 当前范围

已经实现：

- source bundle 加载
- graph 归一化
- candidate seed 挖掘
- workflow/context 双轴路由
- deterministic candidate bundle 渲染
- multi-round refinement scheduling
- nearest-skill / bundle baseline scoring
- terminal-state decision
- generated bundle preflight
- metrics / scorecard / final decision / round reports

本版故意不做：

- graph 抽取
- 自动发布
- dispatcher / runtime 执行
- 多分支 beam search
- 真正的 LLM-assisted content drafting

## 终态语义

自动 refinement 目前有三种合法终态：

- `ready_for_review`
  - 已达到质量阈值，接近完成品，但不自动发布
- `do_not_publish`
  - 没有足够净新增价值，自动流程停止并保留审计记录
- `max_rounds_reached`
  - 到达轮数上限但仍未收敛

这些终态会写入：

- `bundle/skills/<skill-id>/candidate.yaml`
- `reports/final-decision.json`
- `reports/scorecard.json`

## 下一步建议

v0.2 后续可以继续补三块：

1. `llm-assisted` drafting
   - 用于在 refinement scheduler 中丰富 rationale、evidence summary 和 revision notes
2. better net-positive-value measurement
   - 让 bundle-level 基线更细，不止用当前的质量代理分
3. loop-aware revision patching
   - 把 eval 失败模式更系统地反写到 revision log 和 graph patch 建议中
