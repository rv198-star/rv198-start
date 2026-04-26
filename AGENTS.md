# AGENTS


## Project Identity

Starting with `v0.7`, KiU's Chinese project name is `学以致用`.

This name is not a cosmetic translation. It reinforces the project goal: source
knowledge should become executable action capacity while preserving evidence,
boundaries, and user choice about whether to apply additional context layers.

Required rules:

- Keep `KiU` as the stable technical/project abbreviation.
- Use `学以致用` as the Chinese-facing project name from `v0.7` onward.
- Do not rename historical release evidence retroactively; older artifacts may remain
  under `Knowledge in Use` / `KiU` wording for provenance clarity.

## v0.8 语言迁移边界

从 v0.8 开始，新的主线项目文档应先使用 `学以致用` 架构语言解释
KiU，再讨论历史版本术语或外部参照项目术语。

Required rules:

- 不要为了改名而重写历史报告、release evidence、旧计划或 attribution 记录。
- 历史术语保留在 `docs/public/concept-language-glossary.md` 中，用于追溯。
- 新的公共文档应优先使用：读准原书、提炼判断、生成技能、分流流程、
  校准应用、验证行动价值。
- Graphify absorption、cangjie methodology absorption、RIA-TV++、C-class、
  world alignment 等历史术语，只能在明确标注为历史/内部术语，或 attribution
  必须要求时出现在新文档中。
- `技能不是摘要` 和 `学到最后要能用` 是两个优先公共表达；`用而不染`
  保留为校准应用的边界原则。除非能显著减少理解成本，否则不要继续引入
  新的品牌化术语。
- README 和 release note 应先使用新架构语言，而不是版本史语言。

## Methodology Toolbox

`AGENTS.md` defines how KiU calls methodology tools. Detailed methodology
descriptions live under `docs/methodologies/`.

Methodology categories:

- KiU-native methodology: used to explain how KiU works. Current method:
  `学以致用方法论`, expressed as `原书 -> 读准原书 -> 提炼判断 -> 生成技能 /
  分流流程 -> 校准应用 -> 验证行动价值`. See
  `docs/methodologies/kiu-methodology.md`.
- General thinking tools: reusable methods KiU calls for planning, diagnosis,
  and macro decisions. Current tools are `三层递归五步法`, `极限演绎与场景投影法`,
  and `系统效率碾压局部优势`. See
  `docs/methodologies/recursive-five-step-method.md` and
  `docs/methodologies/extreme-deduction-and-scenario-projection.md`, and
  `docs/methodologies/top-level-decision-philosophy.md`.

Required usage:

- Use `学以致用方法论` for public project narrative and product architecture.
- Use `三层递归五步法` for non-trivial planning: discover signals, define
  falsifiable problems, and resolve them into executable actions through
  `基 -> 标 -> 差 -> 策 -> 拆`.
- Use `极限演绎与场景投影法` when a problem looks like `A 也行, B 也行`:
  run L1 structure diagnosis first; only run L2 scenario projection when a
  concrete selection or service boundary is still needed.
- Use `系统效率碾压局部优势` only for macro direction decisions, and never to
  excuse weak evidence honesty, workflow-vs-agentic boundary drift, or ethical
  floor violations.
- Treat general thinking tools as portable methods, not KiU-owned product
  methodology. When used inside KiU, they must obey KiU project boundaries.

## World Alignment Isolation Boundary

KiU `v0.7` world alignment follows `isolation enhancement`, not `fusion rewrite`.
World alignment may add a separate contextual review, gate, pressure-test, or
usage-caveat layer, but it must not rewrite source-faithful skills into
world-blended artifacts.

This principle preserves compatibility with users who want an original-source-only
mode. A user must be able to request source-faithful KiU outputs without world
alignment being applied.

Required rules:

- Keep source-derived `SKILL.md`, anchors, rationale, and book claims source-faithful.
- Store world context, temporal caveats, pressure tests, and application gates in
  isolated artifacts such as `world_alignment/`, not as silent edits to the skill.
- World alignment may change application advice (`apply`, `partial_apply`,
  `apply_with_caveats`, `ask_more_context`, `refuse`), but not the source claim.
- Preserve an explicit original-source-only path for users who do not want real-world
  alignment applied.
- Do not use external world context as hidden source evidence or as a replacement
  for book/source anchors.
- Release evidence must score `source_fidelity_preserved` and
  `world_context_isolated` separately from practical usefulness.

Decision checks:

- Can a reviewer see which parts came from the source and which parts came from
  world alignment?
- Can the same skill be used in original-source-only mode without the world layer?
- Did world context merely gate or caveat application, or did it silently rewrite
  the author's/source's claim?
- Are we improving practical usefulness without weakening evidence honesty or the
  workflow-vs-agentic boundary?

## External Reference Boundary

KiU may use external projects such as `cangjie-skill` and `Graphify` as local reference material, benchmark baselines, and design inspiration, but not as silent inputs to the default production pipeline.

Required rules:

- Treat external projects as `reference` or `benchmark`, not as hidden upstream generators for KiU's default artifacts.
- KiU's default generation path must consume original source materials, not external final skill packs.
- When running A/B or blind comparison, use the same source book where possible, but keep KiU outputs and external benchmark outputs produced by separate pipelines.
- Do not paste or ingest external final `SKILL.md` outputs into KiU's default candidate-building flow.
- If a teacher/reference-assisted mode is introduced later, it must be explicitly named, isolated from the default mode, and evaluated separately.
- Attribution requirements in `NOTICE` and `docs/third-party-attribution.md` remain mandatory whenever external project ideas, prompts, or structures are reused.

## Workflow-vs-Agentic Boundary

KiU treats the boundary between `workflow_script` and `llm_agentic` as a first-class design principle, not as an after-the-fact UI or runtime convenience.

Required rules:

- Judge the boundary on two separate axes: `workflow certainty` and `context certainty`.
- `workflow certainty` asks whether the task can be executed as a stable, repeatable, bounded procedure with low judgment variance.
- `context certainty` asks whether the required situational inputs are explicit enough that the system does not need broad interpretive reconstruction before acting.
- When both workflow certainty and context certainty are high, route the item to `workflow_script_candidate`, preserve it under the configured workflow-candidate output path, and keep it out of `bundle/skills/`.
- When the task still depends on judgment-rich interpretation, boundary arbitration, or context assembly, keep it on the `llm_agentic` path and treat it as a skill candidate rather than forcing it into a script.
- Never silently promote deterministic workflow logic into a KiU skill just because the prose looks rich, and never silently collapse a judgment-heavy skill into a checklist just because it can be summarized.
- Benchmark and release review must score `workflow-vs-agentic boundary quality` explicitly; content richness alone is not enough.

Current minimum implementation contract:

- Profiles own the routing rule. The default release rule today is `high workflow certainty + high context certainty => workflow_script_candidate`.
- Routed workflow candidates must remain auditable through their `candidate.yaml`, `workflow.yaml`, and supporting evidence, even though they are excluded from published `bundle/skills/`.
- Changes to extraction, seed mining, drafting, or refinement must be checked against this boundary rule so that quality gains do not come from boundary drift.

## Verification Feedback Discipline

Long verification runs must be split into visible stages with progress feedback.
Do not stay silent until a full suite finishes when the run is likely to take more
than a few seconds. The user should be able to see which verification phase is
running, what has already passed, and what remains.

Required rules:

- Prefer staged verification: targeted tests first, affected subsystem tests next,
  full-suite discovery last.
- Report after each stage with the command scope and result count.
- When a full suite is necessary, announce it before starting and provide interim
  updates while it is running.
- If a command is still running, poll and summarize progress instead of waiting
  silently for the final output.
- Do not present a release or completion claim until the required stages have fresh
  passing evidence.
- If time is limited, say which verification tier has passed and which tier remains
  unrun instead of implying full coverage.

Recommended sequence for feature work:

1. New or changed behavior tests.
2. Affected module or subsystem test file.
3. Version-specific regression subset.
4. YAML/schema/documentation sanity checks.
5. Full repository test discovery only after the earlier stages pass.

## Version Goal Tiers

KiU separates short-term development goals from condition-dependent external
validation. This keeps development executable when reviewers, real users, live web
access, or domain experts are not currently available.

Required rules:

- Treat `developable goals` as the short-term release driver: architecture, source
  fidelity, installability, workflow-vs-agentic boundary quality, internal usage
  regression, proxy pressure tests, cross-sample stability, and evidence honesty.
- Treat `condition-dependent goals` as mid/late-stage validation: human blind
  review, real user preference, live-world factual verification, domain-expert
  review, and long-running production usage data. These goals are valuable, but
  they must not block short-term releases when the required external condition is
  unavailable.
- Treat `strategic vision` as a north star rather than a release gate: proving KiU
  is preferred in real-world use, building high-quality world modeling, and
  outperforming reference projects under external review.
- Do not upgrade claims from internal evidence to external validation. If a release
  only has internal regression, proxy usage, or same-book reference comparison, say
  so explicitly.
- Do not open a short-term version whose central acceptance criterion depends on
  unavailable external conditions. Move that work to future backlog until the
  condition exists.

Decision checks:

- Can this goal be executed and verified with resources available now?
- If not, is it clearly marked as condition-dependent rather than a blocker?
- Does the release claim match the strongest available evidence tier?
- Are we continuing to improve the system rather than waiting for ideal validation?

Boundary conditions:

- External validation remains important for mature claims, but it is not the daily
  development engine.
- Internal evidence may justify continued development and foundation releases; it
  may not justify claims of human preference, real-world truth, or external closure.

## Benchmark Policy

For `cangjie-skill` specifically:

- Prefer using books that `cangjie-skill` already processed as same-source benchmark corpora.
- Compare on output count, coverage, actionability, evidence traceability, workflow-vs-agentic boundary quality, and real usage quality.
- Prefer blind review when comparing KiU outputs with `cangjie-skill` outputs, but treat it as condition-dependent evidence rather than a short-term blocker when no reviewer is available.
