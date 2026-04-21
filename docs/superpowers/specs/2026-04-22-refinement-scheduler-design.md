# KiU Phase 2 Autonomous Skill Refiner Design

日期：2026-04-22

## 1. 背景

KiU v0.2 Phase 1 已经实现了 deterministic `graph -> candidate bundle` 生成链路。当前输出的问题不是结构不完整，而是“更像可审阅骨架，而不是接近完成品的 skill”。

用户对 Phase 2 的要求已经明确：

- 默认模式必须支持无人介入的多轮迭代
- 人类在环只能是可选增强模式，不能成为默认依赖
- 目标产物应尽可能接近完成品，而不是停留在草稿
- 不自动正式发布，但要提供一个让人觉得可控的审核介入点
- 如果没有足够净新增价值，自动流程要能合法停止并进入 `do_not_publish`

这意味着 Phase 2 不是做 UI，也不是先做审查工具，而是把现有 pipeline 升级为“自动多轮修订的 skill 生产器”。

## 2. 目标

Phase 2 的目标是新增一条默认自动化链路：

`seed -> thick draft -> eval -> revise -> re-eval -> stop`

其中：

- `seed` 复用 Phase 1 的 deterministic candidate bundle
- `thick draft` 产出接近完成品的完整 skill 单元
- `eval` 负责判断该候选是否比现有基线更值得加入 bundle
- `revise` 允许自动系统修改完整候选单元，而不是只改文案
- `stop` 的结果必须可解释，且必须落盘为审计记录

## 3. 非目标

Phase 2 明确不做以下事情：

- 自动将产物状态切换为 `published`
- 重新设计 graph extraction 或 graph build 流程
- 引入网页前端、review UI 或可视化产品界面
- 让人类成为默认流程中的必经步骤
- 做大规模 beam search 或开放式候选爆炸

## 4. 核心原则

### 4.1 默认自动，不默认人工

系统默认以 default unattended mode 运行，自动完成多轮迭代。人工只在以下场景作为可选 gate 出现：

- 终态为 `ready_for_review`
- 终态为 `do_not_publish`
- 调用方显式启用 `human_gate`

### 4.2 交付物优先于审查工具

Phase 2 的首要任务是把 skill 本身做得更像成品，而不是先做“怎么看差异”的工具。审查能力可以在 Phase 3 或后续补充，但不能抢在交付物质量之前。

### 4.3 深度优先于广度

`net_positive_value` 的主标准不是覆盖更多情境，而是提升 skill 的判断深度和性能。排序如下：

1. `performance_gain`
2. `compression_or_clarity_gain`
3. `coverage_gain`

### 4.4 性能提升必须同时相对局部与整体成立

任何候选 skill 的“净新增价值”都必须同时对两类基线成立：

- 最相近的 existing skill
- 整个现有 bundle 的总体水平

如果只比某一条 skill 好，但对整体没有净增益，不足以判定值得收录。

### 4.5 边界质量权重最高

`performance_gain` 不看单一通过率，而看加权质量分，其中：

- `boundary_quality` 权重最高
- `eval_aggregate` 次之
- `cross_subset_stability` 再次之

原因很明确：边界不稳的 skill 会带来误触发和错误自信，再高的总分也不可信。

## 5. 方案选择

本轮采用的实现路径是 `Autonomous Refiner`。

备选方案：

- `Autonomous Re-generator`
- `Hybrid Beam Search`

未选原因：

- `Autonomous Re-generator` 波动过大，难以保证审计轨迹连续
- `Hybrid Beam Search` 成本和复杂度过高，不适合作为 Phase 2 的第一版主线

选择 `Autonomous Refiner` 的原因：

- 与 Phase 1 的 deterministic seed 连续
- 能最快形成稳定的无人值守默认链路
- 更容易把每轮修订落成结构化 revision 记录

## 6. 运行形态

Phase 2 引入一个新的上层编排入口，推荐命名为：

- `scripts/build_candidates.py`

该脚本是推荐入口，默认执行 refinement scheduler。Phase 1 现有的：

- `scripts/generate_candidates.py`

保留为底层 deterministic seed generator，用于测试、回归和低层调试。

推荐入口默认行为：

1. 调用 deterministic seed generation
2. 进入 refinement scheduling loop
3. 产出最终 candidate bundle
4. 生成 round-by-round reports
5. 根据终态决定 `ready_for_review` / `do_not_publish` / `max_rounds_reached`

## 7. 自动迭代模型

### 7.1 输入

自动迭代的输入包括：

- source bundle
- graph snapshot
- automation profile
- Phase 1 输出的 candidate seeds
- nearest-skill mapping
- shared evaluation corpus

### 7.2 每轮允许修改的对象

每一轮自动修订允许修改完整候选单元：

- `SKILL.md`
- `anchors.yaml`
- `eval/summary.yaml`
- `iterations/revisions.yaml`
- `candidate.yaml`
- `Usage Summary` 中的 trace references

禁止只做“文案美容式修订”。如果一轮没有触及证据、边界、评测、绑定或 revision 记录中的至少一项实质内容，则该轮不计为有效修订。

### 7.3 每轮步骤

每轮自动迭代遵循固定顺序：

1. `Draft`
   - 基于上轮候选、基线比较、失败模式、anchor 支撑和 eval 报告生成修订提案
2. `Mutate`
   - 按修订提案修改完整候选单元
3. `Validate`
   - 运行 bundle 结构验证与 generated preflight
4. `Score`
   - 计算结构得分、质量得分和净增值
5. `Record`
   - 将本轮变化写入 round report 和 revision trail
6. `Decide`
   - 判断是否继续下一轮或终止

## 8. 评分体系

### 8.1 结构闸门

所有轮次都必须先通过结构闸门，否则该轮直接失败：

- candidate bundle 可被 validator 接受
- 双层锚定仍然成立
- `candidate.yaml` 完整
- `SKILL.md` 八个必需块齐全
- 引用 trace / source / eval 路径可解析

结构闸门失败的候选不得参与后续质量比较。

### 8.2 质量主分

定义：

`overall_quality = 0.45 * boundary_quality + 0.35 * eval_aggregate + 0.20 * cross_subset_stability`

三个子项含义：

- `boundary_quality`
  - 是否减少误触发
  - 是否更稳地拒绝不该触发的情境
  - 是否让 `fails_when` / `do_not_fire_when` 更具体、可执行
- `eval_aggregate`
  - shared evaluation corpus 上的总体表现
  - 加权汇总 `real_decisions` / `synthetic_adversarial` / `out_of_distribution`
- `cross_subset_stability`
  - 各 subset 之间是否更加均衡
  - 避免只在一类数据上变强、另一类明显变弱

### 8.3 基线比较

每个候选都要与两类基线比较：

- `nearest_skill_baseline`
- `bundle_baseline`

定义：

- `delta_vs_nearest = candidate_overall_quality - nearest_skill_overall_quality`
- `delta_vs_bundle = candidate_overall_quality - bundle_proxy_overall_quality`

其中 `bundle_proxy_overall_quality` 是当前 bundle 在相同评价口径下的总体代理分，而不是某一条 skill 的简单拷贝。

### 8.4 净新增价值

`net_positive_value` 的判定规则如下：

- 必须满足：
  - `delta_vs_nearest > 0`
  - `delta_vs_bundle > 0`
- 在两者都为正的前提下，定义：
  - `net_positive_value = min(delta_vs_nearest, delta_vs_bundle) + clarity_bonus + coverage_bonus`

其中：

- `clarity_bonus` 是较小加分项
- `coverage_bonus` 是更小加分项

这保证“局部改进”与“整体改进”都成立，同时仍允许清晰度和少量新增覆盖作为次级收益。

## 9. 停机规则

### 9.1 基本策略

停机规则采用“质量阈值优先，最大轮数兜底”。

建议默认配置：

- `min_rounds: 2`
- `max_rounds: 5`
- `patience: 2`

### 9.2 终态

系统存在三种合法终态：

- `ready_for_review`
- `do_not_publish`
- `max_rounds_reached`

### 9.3 ready_for_review

满足以下条件时停止并进入 `ready_for_review`：

- 结构闸门通过
- `overall_quality >= target_overall_quality`
- `boundary_quality >= target_boundary_quality`
- `delta_vs_nearest >= min_positive_delta`
- `delta_vs_bundle >= min_positive_delta`
- 最近一轮已无显著新增收益，继续迭代预期价值很低

该状态的含义是：

- 候选已尽可能接近完成品
- 系统不自动发布
- 但此时已经值得交给人类做最终把关

### 9.4 do_not_publish

满足以下任一条件时进入 `do_not_publish`：

- 至少经历 `min_rounds` 后仍没有足够 `net_positive_value`
- 连续 `patience` 轮没有实质改进
- 质量分没有持续上升趋势
- 结构虽然合格，但相对基线没有足够正收益

该状态不是失败，而是自动系统的合法判断结果。系统必须保留完整审计信息，并允许后续人工选择：

- 终止
- 继续定向修订
- 以人工模式再跑一轮或多轮

### 9.5 max_rounds_reached

达到 `max_rounds` 且未满足 `ready_for_review` 或 `do_not_publish` 条件时进入该状态。此状态用于暴露“系统一直在改，但始终没有收敛”的情况。

## 10. 交付物

最终输出仍落在：

- `generated/<bundle-id>/<run-id>/`

在现有结构基础上新增以下产物：

- `reports/rounds/round-01.json`
- `reports/rounds/round-02.json`
- `reports/final-decision.json`
- `reports/scorecard.json`

并扩展 `candidate.yaml`，至少增加：

- `loop_mode`
- `current_round`
- `terminal_state`
- `overall_quality`
- `boundary_quality`
- `eval_aggregate`
- `cross_subset_stability`
- `delta_vs_nearest`
- `delta_vs_bundle`
- `net_positive_value`
- `human_gate`

其中：

- `human_gate` 默认值为 `skipped`
- 在人工介入模式下可变为 `pending` / `approved` / `rejected`

## 11. automation profile 扩展

Phase 2 需要在每个 bundle 的 `automation.yaml` 中新增 refinement-scheduler loop 配置。建议结构：

```yaml
refinement_scheduler:
  enabled_by_default: true
  min_rounds: 2
  max_rounds: 5
  patience: 2
  targets:
    overall_quality: 0.82
    boundary_quality: 0.85
    min_positive_delta: 0.03
  weights:
    boundary_quality: 0.45
    eval_aggregate: 0.35
    cross_subset_stability: 0.20
  bonuses:
    clarity: 0.03
    coverage: 0.01
  mutable_surfaces:
    - skill_markdown
    - anchors
    - eval_summary
    - revisions
    - trace_references
```

本设计要求这些阈值和权重进入配置，而不是硬编码在实现里。

## 12. 模块拆分

为避免把 Phase 2 全部塞进一个脚本，建议新增以下模块：

- `src/kiu_pipeline/refiner.py`
  - 控制多轮编排
- `src/kiu_pipeline/scoring.py`
  - 计算质量分和净新增价值
- `src/kiu_pipeline/mutate.py`
  - 执行候选单元修改
- `src/kiu_pipeline/baseline.py`
  - 计算 nearest skill 与 bundle baseline
- `src/kiu_pipeline/reports.py`
  - 输出 round reports 与 final decision

Phase 1 现有模块继续保留，避免把 seed generation 和 multi-round refinement 强耦合进同一层。

## 13. 测试策略

Phase 2 必须至少覆盖以下测试：

1. 自动模式默认可无人介入执行
2. 候选在达到质量阈值时能以 `ready_for_review` 停机
3. 候选在净新增价值不足时能以 `do_not_publish` 停机
4. 达到 `max_rounds` 时能正确暴露未收敛状态
5. 每轮确实允许修改完整候选单元，而不是只改 `SKILL.md`
6. 结构闸门失败时不得继续质量比较
7. `candidate.yaml` 正确记录 terminal state 和分数字段
8. revision trail 与 round reports 一致

## 14. 实施顺序

建议按以下顺序落地：

1. 扩展 `automation.yaml` 和 `candidate.yaml` schema
2. 新增 scoring / baseline / reports 模块
3. 实现 single-candidate refinement scheduler
4. 用测试驱动接入 CLI
5. 扩展为 bundle 级批量运行
6. 补 optional `human_gate`

这样可以先跑通“一个候选自动多轮迭代”的主链，再扩到完整 bundle。

## 15. 结论

Phase 2 的本质不是“生成更多 skill”，而是让 KiU 默认具备一种无人介入、可多轮修订、以净新增价值为停机依据的 skill 生产机制。

这个机制的终点不是自动发布，而是：

- 自动尽量逼近完成品
- 自动识别不值得收录的候选
- 在需要时给人一个明确、可控、可追踪的介入点

这与 KiU 的目标一致：不是把知识简单扩写成目录，而是把知识变成经得起边界和评测考验的可用 skill。
