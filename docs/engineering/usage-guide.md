# KiU v0.1 Usage Guide

## Quick Start

KiU 目前包含两层内容：

- `v0.1`：graph-first、evidence-backed 的 reference bundle 与 validator
- `v0.2`：从已发布 graph snapshot 生成 candidate seeds，并默认执行 refinement scheduling
- `v0.3`：domain-profile 驱动的 validator / refinement scheduler / `llm-assisted` drafting
- `v0.4`：单 domain 生产线强化，加入 production quality gating、example fixtures、workflow-vs-agentic 路由约束，以及生成摘要诚实同步

当前仓库内置的参考语料仍然是 *Poor Charlie's Almanack*。

Install the repo into your current environment first:

```bash
python3 -m pip install -e .
```

Validate the bundle from the repo root:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_profile.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
```

If the validator reports `rationale_below_density_threshold` for a published investing skill, the skill text is below the domain's hard density floor and must be revised before release.

Expected result:

- the validator prints `VALID`
- the test suite reports all tests passing

Build a v0.2 refinement-scheduled candidate run:

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase2-smoke
```

Generate deterministic seed output only:

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

默认情况下，pipeline 不把测试产物写回仓库，而是写到固定本地目录：

- `/tmp/kiu-local-artifacts/generated/`
- `/tmp/kiu-local-artifacts/sources/<fixture-name>/bundle`

如果你需要改成另一处固定目录，设置 `KIU_LOCAL_OUTPUT_ROOT=/your/path` 即可。
只有在你明确希望写到仓库内路径时，才传 `--output-root generated` 之类的显式覆盖。

## v0.5.1 Cangjie Gap-Closure Benchmark

`v0.5.1` 起，KiU 用本地 reference pack 收口 `cangjie-skill` 对照线，但它们仍然只是
`benchmark/reference`，不会进入默认生产链。

对已发布 bundle 做 same-source 对照：

```bash
python3 scripts/benchmark_reference_pack.py \
  --kiu-bundle bundles/poor-charlies-almanack-v0.1 \
  --reference-pack /tmp/kiu-reference-poor-charlies-almanack-skill \
  --alignment-file benchmarks/alignments/poor-charlies-vs-cangjie.yaml \
  --comparison-scope same-source
```

对 raw-book pipeline 的 source bundle + generated run 做结构对照：

```bash
python3 scripts/benchmark_reference_pack.py \
  --kiu-bundle /tmp/kiu-local-artifacts/book-pipeline/sources/<source-id>/bundle \
  --run-root /tmp/kiu-local-artifacts/book-pipeline/generated/<bundle-id>/<run-id> \
  --reference-pack /tmp/kiu-reference-poor-charlies-almanack-skill
```

输出会同时写：

- `reference-benchmark.json`
- `reference-benchmark.md`

当前固定的对照维度：

- `output_count`
- `coverage`
- `actionability`
- `evidence_traceability`
- `workflow_vs_agentic_boundary`
- `real_usage_quality`

same-source 深评时，额外看：

- `concept_alignment`
- `kiu_review`
- `reference_review`
- `artifact_score_delta_100`

same-scenario usage 现在还会额外输出诊断字段：

- case-level `failure_analysis`
- pair-level `top_failure_modes`
- run-level `repair_targets`
- run-level `upstream owners`

这些字段用于把 usage 失败反推到 `contract / drafting / extraction / seed_verification / routing`
等责任层，而不是只看一个 usage 分数。

`v0.5.1` 的 release gate 不是“artifact 领先即可”，而是必须同时满足：

- `artifact_score_delta_100 > 0`
- same-scenario `average_usage_delta > 0.0`
- same-scenario `usage_winner = kiu`
- same-scenario `kiu_weighted_pass_rate >= reference_weighted_pass_rate`
- `workflow_vs_agentic_boundary` 保持稳定，不能靠误降 skill 来刷赢 benchmark

这个 gate 在 `2026-04-24` 被明确修订成“轻微但明确超越 reference”，原因是原先
单独要求 `weighted_pass_rate` 严格大于 reference，在双方都达到 `1.0` 时会变成
不可达条件。

如果 usage 只是打平、落后，或者虽然 pass rate 打平但综合赢家仍不是 `kiu`，即使
artifact 层领先，也不能宣称已经补齐 `cangjie-skill` 这条版本目标。

当前固定的内部评分卡：

- `KiU foundation retained`
- `Graphify core absorbed`
- `cangjie core absorbed`
- `cangjie methodology internal`
- `cangjie external blind preference`
- `cangjie methodology closure`

`cangjie core absorbed` 只表示 KiU 在 reference 项目的可见结构、extractor 覆盖、产出吞吐和
same-scenario usage 上吸收了多少；它不是“RIA-TV++ 生产方法论已被完整吃透”的证明。

`cangjie methodology internal` 表示内部方法论证据是否到位；`cangjie external blind preference` 表示外部匿名偏好证据是否到位；`cangjie methodology closure` 取二者共同满足后的闭合分。这样避免把“内部能力已实现”和“外部审计未完成”混成一个 55 分。该 gate 单独检查：

- same-scenario usage pressure 是否足够
- principle-depth review 是否存在且有效
- cross-chapter synthesis 是否存在且有效
- triple verification 是否存在且有效
- decoy pressure test 是否存在且有效
- blind preference review 是否存在且有效

如果 KiU 在 same-scenario usage 上赢了，但上述方法论证据缺失，benchmark 必须输出：

- `cangjie_methodology_gate.ready = false`
- `cangjie_methodology_gate.claim = same_scenario_usage_win_only`

这意味着该版本只能声称“在当前 same-source/same-scenario usage rubric 下小胜”，不能声称
“已经追平或吸收 cangjie 的 book-to-skill 生产方法论”。

最终产出物效果从现在起按三层收口，而不是只看 usage 分：

- `Layer 1: immediate usage effect`：触发、边界、拒绝、下一步行动和 same-scenario 使用表现。
- `Layer 2: knowledge depth effect`：深读质量、非显然原则、跨章节综合、三重验证和诱饵压力。
- `Layer 3: external blind preference effect`：外部匿名评审偏好，不能由 KiU 自评替代。

`final_artifact_effect` 是版本收口用的总 gate：

- 只有三层都达标时，才允许 `claim = two_layer_effect_proven`。
- 如果 Layer 1 和 Layer 2 达标但 Layer 3 缺失，输出 `claim = internal_depth_proven_external_blind_missing`。
- 如果 Layer 1 达标但 Layer 2 不达标，只能输出 `claim = usage_effect_only`。
- `usage_effect_only` 是有效的局部改进证据，但不能作为“最终产出物整体质量已收口”或“已追平 cangjie 深读能力”的证据。


### Blind Review Pack Workflow

`v0.6.5` adds an external blind-review handoff path. The public reviewer pack contains anonymous Option A/B artifacts and response templates. It must not include `option_roles` or producer labels. The private unblind key is generated locally and kept out of the repository.

1. Build a same-source benchmark JSON with `scripts/benchmark_reference_pack.py`.
2. Build a reviewer pack with `scripts/build_blind_review_pack.py --benchmark-report <benchmark.json> --output-dir <pack-dir> --review-id <id>`.
3. Send only `reviewer-pack.json` and `reviewer-response-template.json` to reviewers.
4. Merge returned responses with `scripts/merge_blind_review_response.py --response <filled-response.json> --private-key <private-unblind-key.json> --output <blind-evidence.json>`.
5. Re-run `scripts/benchmark_reference_pack.py --blind-preference-evidence <blind-evidence.json>` to unlock the external blind preference gate if the review passes.

这里的版本分工固定为：

- `v0.5.0`：foundation closure
- `v0.5.1`：已经结版的 `cangjie-skill` corrective gap-closure line
- `v0.6`：`Graphify` alignment 预留线
- `v0.7`：更后续的 `In Use world-alignment` 预留线

这四条要严格分开记账：

- `v0.5.1` 解决的是 same-source / same-scenario 对照线
- `v0.6` 解决的是 source / graph / provenance 吸收线
- `v0.7` 解决的是“真实使用压力下仍保持抽象泛化”的 world-alignment 线

因此，即使一个改动能提升现实可用性，只要它的主要问题是“skill 在真实世界里是否更像可直接部署的判断工具”，也不应提前被记到 `v0.6` 的 release claim 里。

`2026-04-24` 的 fresh same-source release verification 已经确认：

- `usage_winner = kiu`
- `average_usage_score_delta_100 = +1.0`
- `kiu_weighted_pass_rate = 1.0`
- `reference_weighted_pass_rate = 1.0`
- `failure_tag_counts = {}`

因此，`v0.5.1` 已经作为 corrective release 结版；后续实现主线转入 `v0.6` / `v0.7`，但它们的 release claim 仍需分别记账。

`2026-04-25` 的逆向定位结论是：`v0.5.1` 的领先主要来自 KiU 在边界、证据、下一步行动语言和
同场景触发上的工程优势；旧 rubric 对深读质量、非显然原则、跨章节综合、诱饵压力测试和盲评
偏弱。因此 `v0.5.1` 的结版性质保持为 corrective gap-closure，而不是 cangjie methodology closure。

为了避免多轮 AI 开发只依赖聊天和局部 plan，仓库内还维护一个 canonical backlog 面：

- `backlog/board.yaml`
- `python3 scripts/show_backlog.py --version v0.6.0`

版本级 backlog 只负责记录状态、阻塞、验收标准和证据链接；它不替代 spec、plan、benchmark、release report。

## Behavior-Aware Review Gate

当前 `three-layer-review.json` 不再只给分，也会给行为化发布判断：

```bash
python3 scripts/review_generated_run.py \
  --run-root /tmp/kiu-local-artifacts/generated/<bundle-id>/<run-id> \
  --source-bundle bundles/poor-charlies-almanack-v0.1
```

CLI 输出现在会包含：

- `release_gate_overall_ready`
- `release_gate_reasons`

写入到 `reports/three-layer-review.json` 的结构则额外包含：

- `usage_outputs.failure_tag_counts`
- `usage_outputs.usage_gate_ready`
- `release_gate.source_bundle_ready`
- `release_gate.generated_bundle_ready`
- `release_gate.usage_gate_ready`
- `release_gate.overall_ready`

这意味着一个 run 即使 artifact 分数还可以，只要 usage 层暴露出明显的
`boundary_leak`、`next_step_blunt` 或 usage score 低于门槛，release gate 也会拦截。

## v0.4 Design Notes

`v0.4.x` 的定位不是“KiU 全部假设已经验证完成”，而是把单 domain 的生产线先做扎实。当前设计重点有四条：

- `workflow` 和 `agentic` 的边界先由 profile 显式声明，而不是让 runtime 临场猜。
- `SKILL.md` 是厚视图，不是真源；`eval/summary.yaml` 与 `iterations/revisions.yaml` 才是结构化真源。
- `production_quality` 只能证明“生成产物达到当前生产线门槛”，不等于“真实 runtime 消费闭环已经证明”。
- 人工修订与 loop 驱动修订必须分开记账，不能把手工改稿伪装成 autonomous refinement。

在 `automation.yaml` 里，profile 继承字段现在接受：

- `inherits_from`
- `inherits`（兼容旧字段）

推荐新 bundle 使用 `inherits_from`，旧 bundle 保持 `inherits` 也能继续解析。

## What This Repo Contains

- one published bundle: `bundles/poor-charlies-almanack-v0.1/`
- five published P0 skills
- one published graph snapshot bound by `graph_hash`
- shared canonical traces
- shared evaluation corpus with:
  - `20` `real_decisions`
  - `20` `synthetic_adversarial`
  - `10` `out_of_distribution`
- validator code and acceptance tests
- one v0.2/v0.3 candidate pipeline with deterministic seed generation, refinement scheduling, `llm-assisted` rationale drafting, and generated-bundle preflight

## Repository Layout

```text
.
├── bundles/
│   └── poor-charlies-almanack-v0.1/
│       ├── manifest.yaml
│       ├── graph/graph.json
│       ├── skills/<skill-id>/
│       ├── traces/
│       ├── evaluation/
│       └── sources/
├── docs/
├── schemas/
├── scripts/
├── src/
└── tests/
```

Key directories:

- `bundles/poor-charlies-almanack-v0.1/manifest.yaml`
  - bundle identity, graph binding, skill index, and shared-asset roots
- `bundles/poor-charlies-almanack-v0.1/graph/graph.json`
  - the published graph snapshot used as the bundle's graph source of truth
- `bundles/poor-charlies-almanack-v0.1/skills/`
  - thick skill views for humans and reviewers
- `bundles/poor-charlies-almanack-v0.1/traces/`
  - canonical usage traces shared across skills
- `bundles/poor-charlies-almanack-v0.1/evaluation/`
  - shared evaluation pool split into real, adversarial, and OOD subsets
- `schemas/`
  - public interface definitions for the bundle manifest, anchors, eval summaries, revisions, relation enum, and KiU Test
- `examples/legacy/workflow-candidates/`
  - schema-first examples for workflow script artifacts
- `scripts/generate_candidates.py`
  - v0.2 deterministic seed generator
- `scripts/build_candidates.py`
  - v0.2/v0.3 default unattended builder
- `scripts/show_profile.py`
  - prints the resolved domain profile for one bundle
- `/tmp/kiu-local-artifacts/generated/`
  - default local v0.2/v0.4 output root; intentionally outside the repo
- `generated/`
  - optional repo-local override path; ignored if you choose to use it explicitly

## How To Read A Skill

Open any skill directory under `bundles/poor-charlies-almanack-v0.1/skills/<skill-id>/`.

Read files in this order:

1. `SKILL.md`
   - the human-facing thick spec
   - starts with `Identity` and `Contract`
   - ends with usage, evaluation, and revision summaries
2. `anchors.yaml`
   - proves double anchoring
   - binds the skill to graph objects and to resolvable source/scenario evidence
3. `eval/summary.yaml`
   - records KiU Test status and the current subset-level evaluation result
4. `iterations/revisions.yaml`
   - records what changed from one revision to the next and why

For a published skill, verify these minimum conditions:

- `status: published`
- `skill_revision` matches the manifest
- at least one graph anchor set exists
- at least one source or scenario anchor set exists
- at least three usage trace references appear in `Usage Summary`
- all three evaluation subsets report `status: pass`

## How To Validate The Bundle

Run the validator:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
```

The validator checks:

- manifest completeness
- graph hash consistency
- required skill files
- required `SKILL.md` sections
- allowed relation enum usage
- trigger registry coverage
- double anchoring rules
- domain-profile published minimum eval counts
- eval summary consistency
- revision-log consistency
- published-skill constraints:
  - at least 3 usage traces
  - all evaluation subsets pass
  - domain minimum eval counts
  - at least one revision cycle

For generated bundles, run the pipeline preflight through the test suite:

```bash
python3 -m unittest tests/test_pipeline.py
```

That check covers:

- generated candidate bundle rendering
- rendered `Evaluation Summary` / `Revision Summary` honesty against YAML truth docs
- `candidate.yaml` presence
- metrics report emission
- rejection of `workflow_script_candidate` inside `bundle/skills/`
- unattended build terminal state emission

## How To Extend The Bundle

To add or revise a skill in this release shape:

1. Duplicate an existing skill directory as a starting point.
2. Write or update `SKILL.md` so all 8 required sections remain present.
3. Add `anchors.yaml` entries that include both:
   - graph anchors
   - source or scenario anchors
4. Update `eval/summary.yaml` with current KiU Test and subset results.
5. Append a new entry to `iterations/revisions.yaml`.
6. If the skill's rationale, boundary, anchors, or evaluation conclusion changes, bump `skill_revision`.
7. If the published graph snapshot changes, update:
   - `graph/graph.json`
   - `manifest.yaml`
   - any affected `anchors.yaml`
   - any affected `revisions.yaml`
8. Re-run validation and tests.

## Publishing Workflow

The current repo already includes the reference public release shape. For future releases, use this order:

1. update bundle content
2. validate locally
3. run acceptance tests
4. commit
5. publish or push

Recommended commands:

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 -m unittest tests/test_validator.py
git status --short
git add .
git commit -m "Describe the release change"
```

## How To Use The v0.2 Pipeline

v0.2 consumes an existing source bundle and its `automation.yaml`.

Run:

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase2-smoke
```

If you only want the deterministic seed bundle:

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

默认输出位置：

- source scaffolding: `/tmp/kiu-local-artifacts/sources/<fixture-name>/bundle`
- generated runs: `/tmp/kiu-local-artifacts/generated/`

覆盖方式：

- 环境变量：`KIU_LOCAL_OUTPUT_ROOT=/your/path`
- 单次命令：`--output-root /your/path`

If you want the current `llm-assisted` surface, use:

```bash
KIU_LLM_PROVIDER=mock \
KIU_LLM_MOCK_RESPONSE="Dense rationale text with anchor refs.[^anchor:demo] [^trace:canonical/demo.yaml]" \
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase3-llm \
  --drafting-mode llm-assisted \
  --llm-budget-tokens 4000
```

Today the shipped LLM drafting surface is intentionally narrow:

- `Rationale` can be drafted by the provider layer
- validator precheck decides whether the draft is accepted
- rejected drafts are preserved in `reports/rounds/*.json`
- `Identity`, `Contract`, `Relations`, and anchors remain non-LLM-owned

## Workflow Script Artifact Example

KiU v0.3 also ships a schema-first workflow artifact example at:

- `examples/legacy/workflow-candidates/dcf-basic-valuation/steps.yaml`

This is the current reference shape for `workflow_script_candidate` delivery:

- YAML DSL only
- no execution engine implied
- intended for structure validation and review first

Read generated output in this order:

1. `/tmp/kiu-local-artifacts/generated/<bundle-id>/<run-id>/reports/metrics.json`
2. `/tmp/kiu-local-artifacts/generated/<bundle-id>/<run-id>/reports/scorecard.json`
3. `/tmp/kiu-local-artifacts/generated/<bundle-id>/<run-id>/reports/final-decision.json`
4. `/tmp/kiu-local-artifacts/generated/<bundle-id>/<run-id>/bundle/manifest.yaml`
5. one generated `bundle/skills/<skill-id>/`
6. if present, `workflow_candidates/<candidate-id>/candidate.yaml`

The most important v0.2 metadata is in `candidate.yaml`:

- `workflow_certainty`
- `context_certainty`
- `recommended_execution_mode`
- `disposition`
- `current_round`
- `terminal_state`
- `overall_quality`
- `net_positive_value`

Interpretation:

- `skill_candidate` means the seed remains in KiU candidate space
- `workflow_script_candidate` means the seed should be treated as deterministic workflow logic, not as a formal KiU skill candidate
- `ready_for_review` means the refinement-scheduler loop reached its quality threshold
- `do_not_publish` means the refinement-scheduler loop found insufficient 净新增价值
- `max_rounds_reached` means the loop hit its round cap before converging

## Design Rationale

### 1. Graph-first, not graph-only

The graph snapshot is the bundle's formal evidence substrate, but not the final product. KiU does not ship a graph browser and call it done. It ships skills that can be reviewed, revised, and validated against that graph.

### 2. Thick skills instead of thin contracts

`SKILL.md` is intentionally thicker than a dispatch-only config file. The contract has to stay machine-tractable, but reviewers also need rationale, evidence summary, usage summary, evaluation summary, and revision history in one place.

### 3. Double anchoring is non-negotiable

Graph anchors alone are too abstract. Source anchors alone are too local and do not guarantee structural consistency. Requiring both makes each published skill simultaneously:

- structurally attached to the released graph snapshot
- textually attached to concrete evidence

### 4. Shared traces and evaluation pools reduce duplication

Traces and eval cases live at the bundle level because they are canonical assets, not per-skill copies. A single case can support multiple skills, and future bundle revisions can expand the pool without scattering duplicate files.

### 5. Revision logs are first-class

KiU is designed for looped refinement rather than one-shot distillation. `iterations/revisions.yaml` is therefore part of the core spec, not an afterthought. A published skill without a visible revision trail is hard to trust.

### 6. v0.1 is spec-first on purpose

This release does not try to solve extraction automation, runtime dispatch, or MCP integration. It establishes:

- the release unit
- the mandatory files
- the public schemas
- the validator behavior
- the content shape of a complete reference bundle

That keeps the first release falsifiable and small enough to review.

### 7. v0.2 adds candidate generation, not automatic publication

The pipeline exists to reduce drafting overhead while preserving evidence discipline. It is intentionally constrained:

- graph snapshot is still the upstream truth
- generated output is still only `under_evaluation` or `ready_for_review`
- `high/high` workflow-context certainty is routed away from KiU skill publication
- refinement scheduling is the default
- human review remains an optional gate before publication

## Recommended Reading Order

If someone is new to the project, this order works well:

1. `docs/engineering/skill-specs/kiu-skill-spec-v0.1.md`
2. `docs/engineering/usage-guide.md`
3. `docs/engineering/kiu-v0.2-pipeline.md`
4. `bundles/poor-charlies-almanack-v0.1/manifest.yaml`
5. one published skill directory
6. `src/kiu_validator/core.py`
7. `tests/test_validator.py`
