# Version Roadmap Realignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the repo's version narrative so `v0.5.1`, `v0.6`, and `v0.7` stop carrying mixed goals and future work is routed to the correct release line, while keeping `v0.5.1` as the active unfinished mainline.

**Architecture:** Treat this as a docs-and-governance correction rather than a product rewrite. Preserve the existing `v0.5.1` evidence archive without treating it as final sign-off, keep `v0.6` scoped to later `Graphify` absorption, and define `v0.7` as a later separate `In Use world-alignment` major line. Historical documents stay archived, but current-facing entry points must use the new wording.

**Tech Stack:** Markdown docs, current benchmark reports, existing release narrative in `README.md`, `docs/usage-guide.md`, and the current planning/report archive.

---

### Task 1: Freeze Stable Version Wording

**Files:**
- Create: `docs/2026-04-24-version-roadmap-v051-v06-v07.md`
- Modify: `README.md`
- Modify: `docs/usage-guide.md`

- [ ] Add a new roadmap document that defines:
  - `v0.5.1 = cangjie gap closure`
  - `v0.6 = Graphify alignment`
  - `v0.7 = In Use world-alignment`
- [ ] Update `README.md` so the current release framing includes the new `v0.7` line and links to the roadmap document.
- [ ] Update `docs/usage-guide.md` so the version split is explicit and current operators do not mistake `v0.6` for the world-alignment release.

**Acceptance:**

- current-facing docs use one consistent three-line version story
- no current-facing doc describes `v0.6` as simultaneously owning `Graphify` and world-alignment

### Task 2: Archive The `cangjie-skill` Shortfalls Review

**Files:**
- Create: `reports/2026-04-24-cangjie-shortfalls-and-overperformance-strategy.md`
- Modify: `reports/2026-04-23-v0.5-vs-cangjie-conclusion.md`

- [ ] Add a new report that separates:
  - what the local `cangjie-skill` reference pack still does better
  - where the pack is structurally weaker than KiU
  - how KiU should stay ahead without stronger source-layer support
- [ ] Update the existing `v0.5 vs cangjie` conclusion so the "unfinished part" is no longer left as vague `v0.6+`, but explicitly points to `v0.6` for `Graphify` work and `v0.7` for world-alignment work.

**Acceptance:**

- the repo contains one auditable shortfalls review rather than only oral conclusions
- future `cangjie` comparison work can point to a stable written judgment

### Task 3: Mark Historical `v0.6` Plans As Scope-Limited

**Files:**
- Modify: `docs/2026-04-23-v0.6-规划意见与工单计划.md`
- Modify: `docs/KiU v0 6 方向性调整 · v0 5 审计.md`

- [ ] Add short status notes to the historical `v0.6` planning documents stating that, as of `2026-04-24`, `In Use world-alignment` has been moved out of `v0.6` and reserved for `v0.7`.
- [ ] Keep the original historical content intact; only add scope-clarification notes rather than rewriting the archived plan body.

**Acceptance:**

- readers can still inspect the archived `v0.6` planning context
- the archive no longer misleads future work into mixing `v0.6` and `v0.7`

### Task 4: Verify Repo Entry-Point Docs Still Pass

**Files:**
- Test: `tests/test_validator.py`

- [ ] Run `python3 -m unittest tests.test_validator` and confirm the docs-related release checks still pass after the wording changes.
- [ ] If the validator exposes a doc expectation mismatch, adjust the affected current-facing docs and rerun the test until green.

**Acceptance:**

- doc narrative changes do not break the repo's existing release/documentation gate

### Release Order

- [ ] Complete Task 1 before Task 2 so every new report uses the fixed version wording.
- [ ] Complete Task 2 before Task 3 so historical-scope notes can point to the new written review.
- [ ] Use Task 4 as the exit gate for this narrative realignment patch.
