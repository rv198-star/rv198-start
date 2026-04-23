# Multi-Document L3 Assessment

Date: `2026-04-23`

Scope:
- `examples/sources/effective-requirements-analysis-source.md`
- `examples/sources/financial-statement-analysis-source.md`

Method:
- each document was run independently through `run_book_pipeline.py`
- each run was scored through `three-layer-review.json`
- the main score uses the existing `overall_score_100`
- extended observations do not override the main score; they explain whether the run is actually shippable

Run roots:
- effective requirements: `/tmp/kiu-local-artifacts/multi-doc-l3/generated/effective-requirements-analysis-source-v0.6/multi-doc-effective-20260423`
- financial statement analysis: `/tmp/kiu-local-artifacts/multi-doc-l3/generated/financial-statement-analysis-source-v0.6/multi-doc-financial-20260423`

## Main Scorecard

| Document | Overall | Source | Generated | Usage | Release Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| effective-requirements-analysis | `93.5` | `97.5` | `96.4` | `85.8` | `blocked` |
| financial-statement-analysis | `95.0` | `97.5` | `96.4` | `90.8` | `blocked` |
| aggregate average | `94.2` | `97.5` | `96.4` | `88.3` | `0/2 pass` |

## Extended Observations

### effective-requirements-analysis

- Structure legality: `pass`
  - source bundle `0 errors / 0 warnings`
  - generated bundle `0 errors / 0 warnings`
- Evidence traceability: `strong`
  - provenance graph complete
  - tri-state density ratio `1.0`
  - tri-state effectiveness overall ratio `0.75`
- Contract clarity: `strong`
  - production artifact `contract_specificity=1.0`
- Boundary discipline: `good`
  - workflow boundary preserved
  - no native `boundary_leak` in three-layer usage review
- Next-step quality: `weak`
  - usage gate blocked on `next_step_quality_weak`
  - dominant failure tag: `next_step_blunt`
- Usage effectiveness: `85.8`
  - one usage sample, no critical failure
- Workflow-vs-Agentic boundary: `stable`
  - `1 skill / 2 workflow`
  - verification gate present, workflow verification ready ratio `1.0`
- Graph effectiveness: `good`
  - `15 nodes / 19 edges / 3 communities`
  - `GRAPH_REPORT.md` present
- Release discipline: `contradictory`
  - `production-quality.release_ready=true`
  - `release_gate.overall_ready=false`

### financial-statement-analysis

- Structure legality: `pass`
  - source bundle `0 errors / 0 warnings`
  - generated bundle `0 errors / 0 warnings`
- Evidence traceability: `strong`
  - provenance graph complete
  - tri-state density ratio `1.0`
  - tri-state effectiveness overall ratio `0.75`
- Contract clarity: `strong`
  - production artifact `contract_specificity=1.0`
- Boundary discipline: `good`
  - workflow boundary preserved
  - no native `boundary_leak` in three-layer usage review
- Next-step quality: `weak`
  - usage gate blocked on `next_step_quality_weak`
  - dominant failure tag: `next_step_blunt` x `2`
- Usage effectiveness: `90.8`
  - two usage samples, no critical failure
- Workflow-vs-Agentic boundary: `stable`
  - `2 skill / 1 workflow`
  - verification gate present, workflow verification ready ratio `1.0`
- Graph effectiveness: `good`
  - `12 nodes / 15 edges / 3 communities`
  - `GRAPH_REPORT.md` present
- Release discipline: `contradictory`
  - `production-quality.release_ready=true`
  - `release_gate.overall_ready=false`

## Aggregate Judgment

Main score result:
- average `94.2`
- median `94.2`
- worst sample `93.5`

Interpretation:
- the system is now structurally stable across two independent documents
- the source and generated layers are consistently strong
- the bottleneck is no longer extraction completeness or schema integrity
- the bottleneck has concentrated into one behavior layer: `next_step_quality`

Cross-document stability:
- source layer is stable: both runs `97.5`
- generated layer is stable: both runs `96.4`
- usage layer varies but is consistently the weakest layer: `85.8` vs `90.8`
- release gate pass rate is `0/2`

Systemic failure pattern:
- dominant failure tag across documents: `next_step_blunt` x `3`
- dominant release-gate reasons:
  - `usage_gate_not_ready` x `2`
  - `next_step_quality_weak` x `2`

## Key Findings

1. `L3` 的机制是有效的。
   - 它没有把高 artifact 分数误判成可发布结果。
   - 两个样本都被 usage gate 拦下，且原因一致。

2. 当前版本的主问题不是“不会生成 skill”，而是“生成后的 next action 还不够硬”。
   - 这解释了为什么整体分高，但行为 gate 仍然失败。

3. `production_quality.release_ready` 与 `behavior-aware release_gate` 存在口径分裂。
   - 工程上这是一个真实问题，不是展示问题。
   - 现在的 `production_quality` 更像 artifact release ready，而不是 true release ready。

4. Workflow/Agentic 边界在这轮没有退化。
   - 两个样本都保持了 workflow boundary preserved。
   - 当前问题与 boundary drift 无关。

## Prioritized Problems

P0:
- strengthen generated `next_action` so it is scenario-specific rather than generic review language

P0:
- align `production_quality.release_ready` with `three-layer review.release_gate.overall_ready`

P1:
- raise `usage_readiness` from the current `0.675` plateau by improving representative cases and action-shape realism

P1:
- add richer native usage review samples per run so `usage_outputs` is not decided by only `1-2` smoke cases

## Recommended Next Work Items

- `KIU-L3-701`
  - tighten generated next-action synthesis in candidate drafting/materialization
- `KIU-L3-702`
  - make production quality report expose `artifact_ready` vs `behavior_ready` explicitly
- `KIU-L3-703`
  - expand native usage smoke generation beyond `review_source_evidence`-style generic next actions
- `KIU-L3-704`
  - add multi-document regression gate using this assessment format as a fixed audit step
