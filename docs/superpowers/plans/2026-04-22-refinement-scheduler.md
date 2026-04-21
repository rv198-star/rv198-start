# Autonomous Skill Refiner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 2 unattended multi-round candidate refinement so KiU can produce near-finished skills by default without requiring human intervention.

**Architecture:** Keep Phase 1 deterministic seed generation intact, then layer an refinement scheduler on top that scores candidates against nearest-skill and bundle baselines, mutates the full candidate unit round by round, and records terminal decisions plus round reports. The new top-level CLI should call seed generation, refinement, validation, and reporting as one unattended pipeline.

**Tech Stack:** Python 3.12, `unittest`, YAML/JSON file outputs, existing `kiu_pipeline` and `kiu_validator` modules.

---

## File Map

- Create: `src/kiu_pipeline/baseline.py`
- Create: `src/kiu_pipeline/scoring.py`
- Create: `src/kiu_pipeline/mutate.py`
- Create: `src/kiu_pipeline/reports.py`
- Create: `src/kiu_pipeline/refiner.py`
- Create: `scripts/build_candidates.py`
- Modify: `src/kiu_pipeline/models.py`
- Modify: `src/kiu_pipeline/load.py`
- Modify: `src/kiu_pipeline/render.py`
- Modify: `src/kiu_pipeline/preflight.py`
- Modify: `src/kiu_pipeline/seed.py`
- Modify: `bundles/poor-charlies-almanack-v0.1/automation.yaml`
- Modify: `docs/kiu-v0.2-pipeline.md`
- Modify: `docs/usage-guide.md`
- Test: `tests/test_refiner.py`
- Test: `tests/test_pipeline.py`

### Task 1: Extend Profile And Candidate Metadata

**Files:**
- Modify: `bundles/poor-charlies-almanack-v0.1/automation.yaml`
- Modify: `src/kiu_pipeline/models.py`
- Modify: `src/kiu_pipeline/load.py`
- Modify: `src/kiu_pipeline/seed.py`
- Test: `tests/test_refiner.py`

- [ ] **Step 1: Write the failing test**

```python
def test_load_source_bundle_reads_refinement_scheduler_profile(self) -> None:
    bundle = load_source_bundle(self.bundle_path)
    refiner = bundle.profile["refinement_scheduler"]
    self.assertTrue(refiner["enabled_by_default"])
    self.assertEqual(refiner["max_rounds"], 5)

def test_seed_metadata_initializes_loop_fields(self) -> None:
    metadata = derive_candidate_metadata(
        candidate_id="circle-of-competence",
        seed_node_id="n_circle_principle",
        candidate_kind="general_agentic",
        graph_hash="sha256:test",
        bundle_id="demo",
        routing_profile={
            "candidate_kinds": {"general_agentic": {"workflow_certainty": "medium", "context_certainty": "high"}},
            "routing_rules": [{"when": {"workflow_certainty": "medium", "context_certainty": "high"}, "recommended_execution_mode": "llm_agentic", "disposition": "skill_candidate"}],
            "refinement_scheduler": {"enabled_by_default": True},
        },
    )
    self.assertEqual(metadata["loop_mode"], "refinement_scheduler")
    self.assertEqual(metadata["current_round"], 0)
    self.assertEqual(metadata["terminal_state"], "pending")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_refiner.RefinerConfigTests -v`
Expected: FAIL because `refinement_scheduler` config and loop metadata fields are missing.

- [ ] **Step 3: Write minimal implementation**

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

```python
return {
    "candidate_id": candidate_id,
    "source_bundle_id": bundle_id,
    "source_graph_hash": graph_hash,
    "seed": {...},
    "candidate_kind": candidate_kind,
    "workflow_certainty": workflow_certainty,
    "context_certainty": context_certainty,
    "recommended_execution_mode": execution_mode,
    "disposition": disposition,
    "gold_match_hint": gold_match_hint,
    "drafting_mode": drafting_mode,
    "loop_mode": "refinement_scheduler",
    "current_round": 0,
    "terminal_state": "pending",
    "human_gate": "skipped",
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_refiner.RefinerConfigTests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bundles/poor-charlies-almanack-v0.1/automation.yaml src/kiu_pipeline/models.py src/kiu_pipeline/load.py src/kiu_pipeline/seed.py tests/test_refiner.py
git commit -m "feat: add refinement scheduler config metadata"
```

### Task 2: Add Baseline And Scoring Engine

**Files:**
- Create: `src/kiu_pipeline/baseline.py`
- Create: `src/kiu_pipeline/scoring.py`
- Test: `tests/test_refiner.py`

- [ ] **Step 1: Write the failing test**

```python
def test_score_candidate_uses_weighted_quality_and_positive_deltas(self) -> None:
    baseline = {
        "nearest_skill_id": "circle-of-competence",
        "nearest_skill_overall_quality": 0.72,
        "bundle_proxy_overall_quality": 0.70,
    }
    score = score_candidate(
        boundary_quality=0.90,
        eval_aggregate=0.80,
        cross_subset_stability=0.75,
        baseline=baseline,
        bonuses={"clarity": 0.03, "coverage": 0.01},
        weights={"boundary_quality": 0.45, "eval_aggregate": 0.35, "cross_subset_stability": 0.20},
    )
    self.assertAlmostEqual(score["overall_quality"], 0.835)
    self.assertGreater(score["delta_vs_nearest"], 0)
    self.assertGreater(score["delta_vs_bundle"], 0)
    self.assertGreater(score["net_positive_value"], 0)
```

```python
def test_decide_terminal_state_returns_do_not_publish_without_positive_value(self) -> None:
    decision = decide_terminal_state(
        round_index=2,
        config={"min_rounds": 2, "max_rounds": 5, "patience": 2, "targets": {"overall_quality": 0.82, "boundary_quality": 0.85, "min_positive_delta": 0.03}},
        scorecard={"overall_quality": 0.81, "boundary_quality": 0.86, "delta_vs_nearest": -0.01, "delta_vs_bundle": 0.02, "net_positive_value": -0.01},
        history=[{"overall_quality": 0.79}, {"overall_quality": 0.81}],
        structural_valid=True,
    )
    self.assertEqual(decision["terminal_state"], "do_not_publish")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_refiner.RefinerScoringTests -v`
Expected: FAIL because scoring and decision modules do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def score_candidate(*, boundary_quality, eval_aggregate, cross_subset_stability, baseline, bonuses, weights):
    overall_quality = (
        weights["boundary_quality"] * boundary_quality
        + weights["eval_aggregate"] * eval_aggregate
        + weights["cross_subset_stability"] * cross_subset_stability
    )
    delta_vs_nearest = overall_quality - baseline["nearest_skill_overall_quality"]
    delta_vs_bundle = overall_quality - baseline["bundle_proxy_overall_quality"]
    net_positive_value = min(delta_vs_nearest, delta_vs_bundle)
    if delta_vs_nearest > 0 and delta_vs_bundle > 0:
        net_positive_value += bonuses["clarity"] + bonuses["coverage"]
    return {...}
```

```python
def decide_terminal_state(*, round_index, config, scorecard, history, structural_valid):
    if not structural_valid:
        return {"terminal_state": "do_not_publish", "continue_loop": False, "reason": "structural_gate_failed"}
    if round_index >= config["min_rounds"] and scorecard["net_positive_value"] <= 0:
        return {"terminal_state": "do_not_publish", "continue_loop": False, "reason": "no_net_positive_value"}
    if (
        scorecard["overall_quality"] >= config["targets"]["overall_quality"]
        and scorecard["boundary_quality"] >= config["targets"]["boundary_quality"]
        and scorecard["delta_vs_nearest"] >= config["targets"]["min_positive_delta"]
        and scorecard["delta_vs_bundle"] >= config["targets"]["min_positive_delta"]
    ):
        return {"terminal_state": "ready_for_review", "continue_loop": False, "reason": "targets_met"}
    if round_index >= config["max_rounds"]:
        return {"terminal_state": "max_rounds_reached", "continue_loop": False, "reason": "max_rounds_reached"}
    return {"terminal_state": "pending", "continue_loop": True, "reason": "continue"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_refiner.RefinerScoringTests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kiu_pipeline/baseline.py src/kiu_pipeline/scoring.py tests/test_refiner.py
git commit -m "feat: add refinement scheduler scoring"
```

### Task 3: Add Candidate Mutation And Reports

**Files:**
- Create: `src/kiu_pipeline/mutate.py`
- Create: `src/kiu_pipeline/reports.py`
- Modify: `src/kiu_pipeline/render.py`
- Modify: `src/kiu_pipeline/preflight.py`
- Test: `tests/test_refiner.py`

- [ ] **Step 1: Write the failing test**

```python
def test_mutate_candidate_updates_full_candidate_unit(self) -> None:
    mutated = mutate_candidate(
        candidate=self.loaded_candidate,
        round_index=1,
        mutation_plan={
            "boundary_strength_delta": 0.10,
            "eval_gain_delta": 0.05,
            "stability_delta": 0.04,
            "append_trace_ref": "traces/canonical/pilot-pre-mortem.yaml",
            "revision_note": "Tightened trigger boundary and added stress trace.",
        },
    )
    self.assertEqual(mutated["candidate"]["current_round"], 1)
    self.assertIn("pilot-pre-mortem.yaml", mutated["skill_markdown"])
    self.assertEqual(mutated["eval_summary"]["status"], "under_evaluation")
    self.assertEqual(mutated["revisions"]["current_revision"], 2)
```

```python
def test_write_round_reports_emits_scorecard_and_final_decision(self) -> None:
    write_round_report(self.run_root, 1, {"overall_quality": 0.84, "terminal_state": "pending"})
    write_final_decision(self.run_root, {"terminal_state": "ready_for_review"})
    self.assertTrue((self.run_root / "reports" / "rounds" / "round-01.json").exists())
    self.assertTrue((self.run_root / "reports" / "final-decision.json").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_refiner.RefinerMutationTests -v`
Expected: FAIL because mutate and report helpers do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def mutate_candidate(*, candidate, round_index, mutation_plan):
    candidate_doc = deepcopy(candidate["candidate"])
    candidate_doc["current_round"] = round_index
    candidate_doc["boundary_quality"] = min(1.0, candidate_doc.get("boundary_quality", 0.70) + mutation_plan["boundary_strength_delta"])
    ...
    return {
        "skill_markdown": updated_skill_markdown,
        "anchors": candidate["anchors"],
        "eval_summary": updated_eval_summary,
        "revisions": updated_revisions,
        "candidate": candidate_doc,
    }
```

```python
def write_round_report(run_root, round_index, doc):
    path = Path(run_root) / "reports" / "rounds"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"round-{round_index:02d}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_refiner.RefinerMutationTests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kiu_pipeline/mutate.py src/kiu_pipeline/reports.py src/kiu_pipeline/render.py src/kiu_pipeline/preflight.py tests/test_refiner.py
git commit -m "feat: add candidate mutation and round reports"
```

### Task 4: Implement Single-Candidate Autonomous Refiner

**Files:**
- Create: `src/kiu_pipeline/refiner.py`
- Modify: `src/kiu_pipeline/render.py`
- Test: `tests/test_refiner.py`

- [ ] **Step 1: Write the failing test**

```python
def test_refine_candidate_reaches_ready_for_review_when_targets_are_met(self) -> None:
    result = refine_candidate(
        candidate=self.loaded_candidate,
        source_bundle=self.bundle,
        nearest_skill_id="circle-of-competence",
        run_root=self.run_root,
    )
    self.assertEqual(result["candidate"]["terminal_state"], "ready_for_review")
    self.assertGreaterEqual(result["candidate"]["overall_quality"], 0.82)
    self.assertTrue((self.run_root / "reports" / "final-decision.json").exists())
```

```python
def test_refine_candidate_returns_do_not_publish_when_no_positive_value(self) -> None:
    result = refine_candidate(
        candidate=self.low_value_candidate,
        source_bundle=self.bundle,
        nearest_skill_id="circle-of-competence",
        run_root=self.run_root,
    )
    self.assertEqual(result["candidate"]["terminal_state"], "do_not_publish")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_refiner.RefinerLoopTests -v`
Expected: FAIL because refiner module does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def refine_candidate(*, candidate, source_bundle, nearest_skill_id, run_root):
    config = source_bundle.profile["refinement_scheduler"]
    history = []
    current = candidate
    for round_index in range(1, config["max_rounds"] + 1):
        mutation_plan = plan_round_mutation(current=current, round_index=round_index)
        current = mutate_candidate(candidate=current, round_index=round_index, mutation_plan=mutation_plan)
        structural_valid = True
        baseline = build_candidate_baseline(source_bundle=source_bundle, nearest_skill_id=nearest_skill_id)
        scorecard = score_candidate(...)
        history.append(scorecard)
        decision = decide_terminal_state(...)
        current["candidate"].update(scorecard)
        current["candidate"]["terminal_state"] = decision["terminal_state"]
        write_round_report(run_root, round_index, {...})
        if not decision["continue_loop"]:
            write_final_decision(run_root, decision | {"candidate_id": current["candidate"]["candidate_id"]})
            return current
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_refiner.RefinerLoopTests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/kiu_pipeline/refiner.py src/kiu_pipeline/render.py tests/test_refiner.py
git commit -m "feat: add refinement scheduling loop"
```

### Task 5: Add End-To-End CLI And Bundle-Level Batch Execution

**Files:**
- Create: `scripts/build_candidates.py`
- Modify: `src/kiu_pipeline/render.py`
- Modify: `src/kiu_pipeline/preflight.py`
- Modify: `tests/test_pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_candidates_cli_runs_refinement_scheduler_and_emits_terminal_state(self) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_candidates.py"),
            "--source-bundle",
            str(self.bundle_path),
            "--output-root",
            str(output_root),
            "--run-id",
            "phase2-e2e",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    candidate_doc = yaml.safe_load((bundle_root / "skills" / "circle-of-competence" / "candidate.yaml").read_text(encoding="utf-8"))
    self.assertIn(candidate_doc["terminal_state"], {"ready_for_review", "do_not_publish", "max_rounds_reached"})
    self.assertTrue((run_root / "reports" / "final-decision.json").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_pipeline.CandidatePipelineTests.test_build_candidates_cli_runs_refinement_scheduler_and_emits_terminal_state -v`
Expected: FAIL because `build_candidates.py` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def main() -> int:
    args = parse_args()
    source_bundle = load_source_bundle(args.source_bundle, profile_override=args.profile)
    graph = normalize_graph(source_bundle.graph_doc)
    seeds = mine_candidate_seeds(source_bundle, graph, drafting_mode=args.drafting_mode)
    run_root = render_generated_run(..., prepare_only=True)
    candidates = load_generated_candidates(run_root / "bundle")
    refined = refine_bundle_candidates(candidates=candidates, source_bundle=source_bundle, run_root=run_root)
    materialize_refined_candidates(run_root / "bundle", refined)
    report = validate_generated_bundle(run_root / "bundle")
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_pipeline.CandidatePipelineTests.test_build_candidates_cli_runs_refinement_scheduler_and_emits_terminal_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_candidates.py src/kiu_pipeline/render.py src/kiu_pipeline/preflight.py tests/test_pipeline.py
git commit -m "feat: add unattended build candidates cli"
```

### Task 6: Update Documentation And Run Full Verification

**Files:**
- Modify: `docs/kiu-v0.2-pipeline.md`
- Modify: `docs/usage-guide.md`
- Test: `tests/test_refiner.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_validator.py`

- [ ] **Step 1: Update docs**

```markdown
## Phase 2 Autonomous Refiner

Default build mode now runs multi-round refinement scheduling after deterministic seed generation.

Terminal states:
- `ready_for_review`
- `do_not_publish`
- `max_rounds_reached`
```

- [ ] **Step 2: Run targeted tests**

Run: `python3 -m unittest tests/test_refiner.py`
Expected: all tests PASS

- [ ] **Step 3: Run pipeline tests**

Run: `python3 -m unittest tests/test_pipeline.py`
Expected: all tests PASS

- [ ] **Step 4: Run validator tests**

Run: `python3 -m unittest tests/test_validator.py`
Expected: all tests PASS

- [ ] **Step 5: Run CLI smoke**

Run: `python3 scripts/build_candidates.py --source-bundle bundles/poor-charlies-almanack-v0.1 --output-root generated --run-id phase2-smoke`
Expected: exit 0 and emit `reports/final-decision.json`

- [ ] **Step 6: Commit**

```bash
git add docs/kiu-v0.2-pipeline.md docs/usage-guide.md
git commit -m "docs: document refinement scheduler"
```
