# W2 Benchmark Summary

Date: `2026-04-23`

Status: `historical_baseline_superseded_by_v0.5.1_r14`

Superseding evidence:
- corrective scorecard: [`reports/2026-04-23-v0.5.1-gap-closure-scorecard.md`](./2026-04-23-v0.5.1-gap-closure-scorecard.md)
- corrective conclusion: [`reports/2026-04-23-v0.5-vs-cangjie-conclusion.md`](./2026-04-23-v0.5-vs-cangjie-conclusion.md)

The content below remains accurate as the original W2 checkpoint, but its
same-scenario weakness has now been closed by the later `v0.5.1` corrective run
`v051-gap-closure-r14`.

Primary run:
- source bundle: `/tmp/kiu-local-artifacts/w2-poor-charlies/sources/poor-charlies-almanack-book/bundle`
- generated run: `/tmp/kiu-local-artifacts/w2-poor-charlies/generated/poor-charlies-almanack-book-source-v0.6/w2-gate-pc-final`
- reference benchmark: `/tmp/kiu-local-artifacts/w2-poor-charlies/generated/poor-charlies-almanack-book-source-v0.6/w2-gate-pc-final/reports/reference-benchmark.json`

Supporting repo artifacts:
- merged graph report: `reports/w1-merged-graph-report.md`
- W1 audit baseline: `reports/w1-audit.md`

## Question 1

Did candidate quality rise?

Answer: `yes`

Evidence:
- accepted candidates: `5`
- rejected candidates: `0`
- generated bundle score: `96.4`
- usage output score: `95.8`
- overall three-layer score: `94.8`
- concept-aligned artifact score delta vs reference: `+20.0`
- minimum production quality: `0.9449`

Interpretation:
- the final run recovered all five P0 investment principles as `skill_candidate`, with no rejected candidate left in the verification summary.
- accepted outputs are not just structurally present; the generated bundle stayed at `excellent` production quality and the three-layer review rose to `94.8`.
- this closes the earlier recall gap from the intermediate W2 runs.

## Question 2

Did workflow count rise without boundary drift?

Answer: `yes, after hardening the boundary by refusing false workflow promotion`

Evidence:
- current run workflow candidates: `0`
- current run generated skills: `5`
- benchmark boundary preserved: `true`
- workflow verification ready ratio: `1.0`
- prior pre-hardening run `w2-gate-pc-02` produced `2` workflow candidates, both from judgment-heavy investment principles

Interpretation:
- the useful outcome here was not “more workflows”, but “no workflow drift”.
- W2 added a harder routing rule: a single checklist cue plus one evidence chunk no longer promotes a `principle_signal` into `workflow_script_candidate`.
- this is aligned with `AGENTS.md`: `bias-self-audit` and `invert-the-problem` now stay on the `llm_agentic` path instead of collapsing into scripts.

## Question 3

Did the merged graph become more informative?

Answer: `yes`

Evidence:
- merged graph edge count rose from `18` to `25`
- `reports/w1-merged-graph-report.md` now contains cross-bundle `INFERRED` and `AMBIGUOUS` connections
- `Surprising Connections` now surfaces bounded inferred links with `support_refs`, for example:
  - `Bias self audit -> Blast radius check`
  - `Reversibility gate -> Bias self audit`
  - `Bias self audit -> Blameless postmortem`

Interpretation:
- the merged graph is no longer only a side-by-side listing of two bundles.
- cross-bundle navigation is now evidence-backed and bounded by low-confidence inferred links instead of unmarked synthesis.
- this materially improves graph usefulness for follow-up review and cross-domain question generation.

## Same-Scenario Review

Reference benchmark summary:
- matched concept pairs: `2`
- same-scenario cases: `6`
- KiU average usage score: `69.4`
- reference average usage score: `72.5`
- average delta: `-3.2`
- KiU weighted pass rate: `0.6667`
- reference weighted pass rate: `0.6667`

Interpretation:
- generated artifacts are structurally stronger than the local reference pack, but usage behavior is still slightly behind.
- the current gap is not boundary drift; it is trigger and next-action sharpness inside the generated skill contract.

## W2 Exit Judgment

Decision: `GO`, with explicit carry-over gaps

What is now proven:
- raw-book pipeline can emit `BOOK_OVERVIEW`, extraction result, graph, verification summary, generated bundle, usage review, and reference benchmark in one auditable path.
- benchmarking a generated run no longer loses concept alignment just because the source bundle itself has `0` published skills.
- workflow-vs-agentic boundary hardening improved real output quality instead of gaming throughput.
- the final `Poor Charlie` run now lands at `5 skill / 0 workflow drift`, which is the right side of the `AGENTS.md` boundary for this corpus.

What remains open:
- improve same-scenario usage quality so KiU is not merely artifact-strong but also behavior-strong.
- raise `Graphify core absorbed` beyond `87.5` by improving tri-state effectiveness and extractor coverage.

## L3 Follow-Up

Post-W2, the benchmark stack now emits structured usage failure attribution:

- `Top failure modes`
- `Repair targets`
- `Upstream owners`

The three-layer review stack also now emits a behavior-aware `release_gate`, so later runs can be blocked for usage-level weakness even when structural validation and artifact quality still look acceptable.
