# KiU · Knowledge in Use · 学以致用

[![CI](https://github.com/rv198-star/KiU/actions/workflows/ci.yml/badge.svg)](https://github.com/rv198-star/KiU/actions/workflows/ci.yml)

KiU 是 `Knowledge in Use` 的缩写，中文名是 `学以致用`。

它的目标不是把书压缩成摘要，而是把原书知识转化为可触发、有边界、能拒绝误用、能指导复盘的行动技能，让学习最终变成可执行的行动力。

它可以和 RAG、知识库问答、摘要器、摘录库、翻译器放在同一个知识使用语境里比较，但定位不同：RAG 更偏向“检索并生成答案”，KiU 更关注“把原书思想转化为可触发、有边界、能拒绝误用、能指导复盘的行动技能”。

两个核心表达：

- `技能不是摘要`：技能必须产生行动力，而不是压缩版章节总结。
- `学到最后要能用`：学习的终点不是“知道”，而是能改善具体判断、选择、行动、拒绝和复盘。

## 架构

```text
原书 -> 读准原书 -> 提炼判断 -> 生成技能 / 分流流程 -> 校准应用 -> 验证行动价值
```

| 步骤 | 含义 |
| --- | --- |
| 读准原书 | 保留原书段落、观点、结构、锚点和来源。 |
| 提炼判断 | 从原书中提炼可迁移的判断，而不是把书压缩成笔记。 |
| 生成技能 | 只发布能帮助用户判断、取舍、行动、拒绝或复盘的技能。 |
| 分流流程 | 确定性流程保留为流程工件，不膨胀成技能。 |
| 校准应用 | 按需加入现实语境、当前事实核验、风险提示，但不改写原书技能。 |
| 验证行动价值 | 验证产物是否在明确证据等级下产生行动价值。 |

## 从这里开始

- [项目架构叙事](docs/public/project-architecture-narrative.md)
- [方法论工具箱](docs/methodologies/README.md)
- [当前评审包](review-pack/current/README.md)
- [证据索引](evidence/README.md)
- [概念语言对照表](docs/public/concept-language-glossary.md)
- [用户侧评分指南](docs/public/user-facing-evaluation-guide.md)
- [使用指南](docs/engineering/usage-guide.md)
- [Backlog 看板](backlog/board.yaml)
- [KiU 技能规范 v0.6](docs/engineering/skill-specs/kiu-skill-spec-v0.6.md)
- [参考 bundle](bundles/poor-charlies-almanack-v0.1/manifest.yaml)
- [工程参考 bundle](bundles/engineering-postmortem-v0.1/manifest.yaml)

## 当前证据边界

v0.8.2 是当前阶段性结案基线。仓库保留最新版可审查产物：
`review-pack/current` 包含 5 本书、21 个已发布 SKILLS，均由 v0.8.2 价值驱动压力链重新生成，且包含 `value_gain_*`、`Downstream Use Check`、`Minimum Pressure Pass` 标记。

当前项目已经有较强的内部生成、路由、结构评估和使用者视角 proxy 证据。但外部盲评、真实用户验证、领域专家验证仍是独立证据等级，不能从内部评分中自动推导出来。

本地安装：

```bash
python3 -m pip install -e .
```

本地验证：

```bash
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_profile.py bundles/poor-charlies-almanack-v0.1
python3 scripts/show_backlog.py --version v0.6.0
python3 -m unittest tests/test_validator.py
```

如果验证返回类似错误：
`circle-of-competence: rationale_below_density_threshold (...)`,
说明已发布技能文本低于领域配置的硬密度门槛，发布前必须修订。

构建带 refinement 调度的候选 bundle：

```bash
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase2-smoke
```

从来源 bundle、生成 bundle 和使用输出三层审查生成结果：

```bash
python3 scripts/review_generated_run.py \
  --run-root /tmp/kiu-local-artifacts/generated/poor-charlies-almanack-v0.1/phase2-smoke \
  --source-bundle bundles/poor-charlies-almanack-v0.1
```

默认情况下，pipeline 输出写到仓库外的 `/tmp/kiu-local-artifacts/generated/`。
可以设置 `KIU_LOCAL_OUTPUT_ROOT=/your/path` 覆盖默认位置；如果确实想写到其他目录，例如 `generated/`，可以传入 `--output-root`。

只生成确定性 seed bundle：

```bash
python3 scripts/generate_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id local-v0_2 \
  --drafting-mode deterministic
```

用 mock provider 跑一次 `llm-assisted` 起草：

```bash
KIU_LLM_PROVIDER=mock \
KIU_LLM_MOCK_RESPONSE="Replace me with a dense rationale.[^anchor:demo] [^trace:canonical/demo.yaml]" \
python3 scripts/build_candidates.py \
  --source-bundle bundles/poor-charlies-almanack-v0.1 \
  --run-id phase3-llm \
  --drafting-mode llm-assisted \
  --llm-budget-tokens 4000
```
