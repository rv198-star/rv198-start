import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_validator.core import validate_bundle


PUBLISHED_INVESTING_REVISION = 5


class BundleValidationTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"
        self.engineering_bundle_path = ROOT / "bundles" / "engineering-postmortem-v0.1"

    def _load_yaml(self, path: Path) -> dict:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _write_yaml(self, path: Path, doc: dict) -> None:
        path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _canonical_graph_hash(self, graph_doc: dict) -> str:
        canonical_doc = dict(graph_doc)
        canonical_doc.pop("graph_hash", None)
        encoded = json.dumps(canonical_doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def _rewrite_bundle_graph_bindings(self, bundle_root: Path, graph_hash: str, graph_version: str) -> None:
        manifest = self._load_yaml(bundle_root / "manifest.yaml")
        manifest["graph"]["graph_hash"] = graph_hash
        manifest["graph"]["graph_version"] = graph_version
        self._write_yaml(bundle_root / "manifest.yaml", manifest)

        for skill_entry in manifest["skills"]:
            skill_dir = bundle_root / skill_entry["path"]
            anchors = self._load_yaml(skill_dir / "anchors.yaml")
            anchors["graph_hash"] = graph_hash
            anchors["graph_version"] = graph_version
            self._write_yaml(skill_dir / "anchors.yaml", anchors)

            revisions = self._load_yaml(skill_dir / "iterations" / "revisions.yaml")
            for entry in revisions.get("history", []):
                entry["graph_hash"] = graph_hash
            self._write_yaml(skill_dir / "iterations" / "revisions.yaml", revisions)

    def _replace_skill_text(
        self,
        bundle_root: Path,
        skill_id: str,
        old: str,
        new: str,
    ) -> None:
        skill_path = bundle_root / "skills" / skill_id / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        self.assertIn(old, content)
        skill_path.write_text(content.replace(old, new, 1), encoding="utf-8")

    def _rewrite_skill_sections(
        self,
        bundle_root: Path,
        skill_id: str,
        *,
        rationale: str,
        evidence_summary: str,
    ) -> None:
        skill_path = bundle_root / "skills" / skill_id / "SKILL.md"
        content = skill_path.read_text(encoding="utf-8")
        content, rationale_count = re.subn(
            r"## Rationale\n.*?\n## Evidence Summary\n",
            f"## Rationale\n{rationale}\n\n## Evidence Summary\n",
            content,
            flags=re.DOTALL,
        )
        self.assertEqual(rationale_count, 1)
        content, evidence_count = re.subn(
            r"## Evidence Summary\n.*?\n## Relations\n",
            f"## Evidence Summary\n{evidence_summary}\n\n## Relations\n",
            content,
            flags=re.DOTALL,
        )
        self.assertEqual(evidence_count, 1)
        skill_path.write_text(content, encoding="utf-8")

    def _collect_contract_symbols(self, bundle_root: Path) -> list[str]:
        symbols: set[str] = set()
        for skill_path in (bundle_root / "skills").glob("*/SKILL.md"):
            content = skill_path.read_text(encoding="utf-8")
            match = re.search(r"## Contract\s+```yaml\n(.*?)```", content, re.DOTALL)
            self.assertIsNotNone(match, skill_path)
            contract = yaml.safe_load(match.group(1)) or {}
            trigger = contract.get("trigger", {})
            boundary = contract.get("boundary", {})
            for key in ("patterns", "exclusions"):
                symbols.update(trigger.get(key, []))
            for key in ("fails_when", "do_not_fire_when"):
                symbols.update(boundary.get(key, []))
        return sorted(symbols)

    def _write_local_trigger_registry(self, bundle_root: Path) -> Path:
        trigger_entries = [
            {
                "symbol": symbol,
                "definition": f"{symbol} definition",
                "positive_examples": [f"{symbol} positive"],
                "negative_examples": [f"{symbol} negative"],
            }
            for symbol in self._collect_contract_symbols(bundle_root)
        ]
        registry_path = bundle_root / "triggers.yaml"
        self._write_yaml(registry_path, {"triggers": trigger_entries})

        automation_path = bundle_root / "automation.yaml"
        automation_doc = self._load_yaml(automation_path)
        automation_doc["trigger_registry"] = "triggers.yaml"
        self._write_yaml(automation_path, automation_doc)
        return registry_path

    def _rewrite_bundle_id(self, bundle_root: Path, bundle_id: str) -> None:
        manifest_path = bundle_root / "manifest.yaml"
        manifest = self._load_yaml(manifest_path)
        manifest["bundle_id"] = bundle_id
        self._write_yaml(manifest_path, manifest)

    def test_bundle_validates_without_errors(self) -> None:
        report = validate_bundle(self.bundle_path)

        self.assertEqual(report["errors"], [])
        self.assertIn("warnings", report)
        self.assertEqual(report["manifest"]["bundle_version"], "0.1.0")
        self.assertEqual(len(report["skills"]), 5)
        self.assertEqual(
            {skill["skill_id"] for skill in report["skills"]},
            {
                "circle-of-competence",
                "invert-the-problem",
                "margin-of-safety-sizing",
                "bias-self-audit",
                "opportunity-cost-of-the-next-best-idea",
            },
        )

    def test_engineering_bundle_validates_without_errors(self) -> None:
        report = validate_bundle(self.engineering_bundle_path)

        self.assertEqual(report["errors"], [])
        self.assertEqual(report["manifest"]["domain"], "engineering")
        self.assertEqual(
            {skill["skill_id"] for skill in report["skills"]},
            {"postmortem-blameless", "blast-radius-check"},
        )

    def test_engineering_bundle_supports_cross_bundle_validation(self) -> None:
        report = validate_bundle(
            self.engineering_bundle_path,
            merge_with=[self.bundle_path],
        )

        self.assertEqual(report["errors"], [])
        self.assertEqual(
            report["merged_graph"]["source_bundles"],
            ["engineering-postmortem-v0.1", "poor-charlies-almanack-v0.1"],
        )

    def test_bundle_has_shared_graph_trace_and_evaluation_assets(self) -> None:
        report = validate_bundle(self.bundle_path)

        self.assertGreaterEqual(report["graph"]["node_count"], 10)
        self.assertGreaterEqual(report["graph"]["edge_count"], 5)
        self.assertGreaterEqual(report["shared_assets"]["trace_count"], 12)
        self.assertEqual(report["shared_assets"]["evaluation_count"], 53)
        self.assertEqual(
            report["shared_assets"]["evaluation_breakdown"],
            {
                "real_decisions": 20,
                "synthetic_adversarial": 20,
                "out_of_distribution": 10,
            },
        )

    def test_one_skill_demonstrates_revision_plus_one_loop(self) -> None:
        report = validate_bundle(self.bundle_path)
        circle = next(
            skill
            for skill in report["skills"]
            if skill["skill_id"] == "circle-of-competence"
        )

        self.assertEqual(circle["status"], "published")
        self.assertEqual(circle["skill_revision"], PUBLISHED_INVESTING_REVISION)
        self.assertGreaterEqual(circle["revision_entry_count"], 2)
        self.assertTrue(circle["has_revision_loop"])

    def test_full_release_marks_all_five_skills_as_published(self) -> None:
        report = validate_bundle(self.bundle_path)

        self.assertEqual(len(report["skills"]), 5)
        for skill in report["skills"]:
            self.assertEqual(skill["status"], "published")
            self.assertGreaterEqual(skill["skill_revision"], 2)
            self.assertGreaterEqual(skill["usage_trace_count"], 3)
            self.assertTrue(skill["all_eval_subsets_pass"])
            self.assertEqual(
                skill["eval_case_counts"],
                {
                    "real_decisions": 20,
                    "synthetic_adversarial": 20,
                    "out_of_distribution": 10,
                },
            )

    def test_circle_of_competence_is_v04_reference_skill(self) -> None:
        report = validate_bundle(self.bundle_path)
        circle = next(
            skill
            for skill in report["skills"]
            if skill["skill_id"] == "circle-of-competence"
        )

        self.assertEqual(circle["skill_revision"], PUBLISHED_INVESTING_REVISION)
        self.assertEqual(circle["revision_entry_count"], PUBLISHED_INVESTING_REVISION)
        self.assertEqual(
            set(circle["relations"]["constrained_by"]),
            {"margin-of-safety-sizing"},
        )
        self.assertEqual(
            set(circle["relations"]["complements"]),
            {"invert-the-problem", "opportunity-cost-of-the-next-best-idea"},
        )

        skill_path = (
            self.bundle_path / "skills" / "circle-of-competence" / "SKILL.md"
        )
        skill_doc = skill_path.read_text(encoding="utf-8")
        self.assertIn("[^trace:canonical/dotcom-refusal.yaml]", skill_doc)
        self.assertIn("[^trace:canonical/google-omission.yaml]", skill_doc)
        self.assertIn("[^trace:canonical/crypto-rejection.yaml]", skill_doc)
        self.assertIn(f"Revision {PUBLISHED_INVESTING_REVISION}", skill_doc)

        eval_summary = self._load_yaml(
            self.bundle_path
            / "skills"
            / "circle-of-competence"
            / "eval"
            / "summary.yaml"
        )
        self.assertEqual(eval_summary["skill_revision"], PUBLISHED_INVESTING_REVISION)
        self.assertGreaterEqual(len(eval_summary["key_failure_modes"]), 2)

        revisions = self._load_yaml(
            self.bundle_path
            / "skills"
            / "circle-of-competence"
            / "iterations"
            / "revisions.yaml"
        )
        self.assertEqual(revisions["current_revision"], PUBLISHED_INVESTING_REVISION)
        self.assertEqual(len(revisions["history"]), PUBLISHED_INVESTING_REVISION)

    def test_all_published_investing_skills_are_v04_content_rewrites(self) -> None:
        expected_revisions = {
            "circle-of-competence": 5,
            "invert-the-problem": 5,
            "margin-of-safety-sizing": 5,
            "bias-self-audit": 5,
            "opportunity-cost-of-the-next-best-idea": 4,
        }
        expected_trace_refs = {
            "circle-of-competence": [
                "[^trace:canonical/dotcom-refusal.yaml]",
                "[^trace:canonical/google-omission.yaml]",
                "[^trace:canonical/crypto-rejection.yaml]",
            ],
            "invert-the-problem": [
                "[^trace:canonical/anti-ruin-checklist.yaml]",
                "[^trace:canonical/pilot-pre-mortem.yaml]",
                "[^trace:canonical/airline-bankruptcy-checklist.yaml]",
            ],
            "margin-of-safety-sizing": [
                "[^trace:canonical/sees-candies-discipline.yaml]",
                "[^trace:canonical/salomon-exposure-cap.yaml]",
                "[^trace:canonical/irreversible-bet-precheck.yaml]",
            ],
            "bias-self-audit": [
                "[^trace:canonical/us-air-regret.yaml]",
                "[^trace:canonical/incentive-caused-delusion-audit.yaml]",
                "[^trace:canonical/pilot-pre-mortem.yaml]",
            ],
            "opportunity-cost-of-the-next-best-idea": [
                "[^trace:canonical/costco-next-best-idea.yaml]",
                "[^trace:canonical/capital-switching-benchmark.yaml]",
                "[^trace:canonical/dexter-shoe-consideration.yaml]",
            ],
        }

        report = validate_bundle(self.bundle_path)

        for skill in report["skills"]:
            skill_id = skill["skill_id"]
            expected_revision = expected_revisions[skill_id]
            self.assertEqual(skill["skill_revision"], expected_revision, skill_id)

            skill_doc = (
                self.bundle_path / "skills" / skill_id / "SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertIn(f"Revision {expected_revision}", skill_doc, skill_id)
            for trace_ref in expected_trace_refs[skill_id]:
                self.assertIn(trace_ref, skill_doc, f"{skill_id}: missing {trace_ref}")

            eval_summary = self._load_yaml(
                self.bundle_path / "skills" / skill_id / "eval" / "summary.yaml"
            )
            self.assertEqual(eval_summary["skill_revision"], expected_revision, skill_id)
            self.assertGreaterEqual(len(eval_summary["key_failure_modes"]), 2, skill_id)

            revisions = self._load_yaml(
                self.bundle_path / "skills" / skill_id / "iterations" / "revisions.yaml"
            )
            self.assertEqual(revisions["current_revision"], expected_revision, skill_id)
            self.assertEqual(len(revisions["history"]), expected_revision, skill_id)

    def test_density_hard_gate_blocks_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)
            self._rewrite_skill_sections(
                tmp_bundle,
                "circle-of-competence",
                rationale="Thin text.",
                evidence_summary="No anchors here.",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    error.startswith(
                        "circle-of-competence: rationale_below_density_threshold"
                    )
                    for error in report["errors"]
                ),
                report["errors"],
            )
            self.assertTrue(
                any(
                    error.startswith(
                        "circle-of-competence: evidence_summary_missing_anchors"
                    )
                    for error in report["errors"]
                ),
                report["errors"],
            )

    def test_density_soft_gate_warns_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)
            self._rewrite_skill_sections(
                tmp_bundle,
                "circle-of-competence",
                rationale="Thin text.",
                evidence_summary="No anchors here.",
            )

            manifest_path = tmp_bundle / "manifest.yaml"
            manifest_doc = self._load_yaml(manifest_path)
            manifest_doc["domain"] = "default"
            self._write_yaml(manifest_path, manifest_doc)

            automation_path = tmp_bundle / "automation.yaml"
            automation_doc = self._load_yaml(automation_path)
            automation_doc["inherits"] = "default"
            self._write_yaml(automation_path, automation_doc)
            self._write_local_trigger_registry(tmp_bundle)

            report = validate_bundle(tmp_bundle)

            self.assertFalse(
                any(
                    error.startswith(
                        "circle-of-competence: rationale_below_density_threshold"
                    )
                    for error in report["errors"]
                ),
                report["errors"],
            )
            self.assertTrue(
                any(
                    warning.startswith(
                        "circle-of-competence: rationale_below_density_threshold"
                    )
                    for warning in report["warnings"]
                ),
                report["warnings"],
            )

    def test_empty_trigger_registry_emits_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            registry_path = tmp_bundle / "empty-triggers.yaml"
            self._write_yaml(registry_path, {"triggers": []})

            automation_path = tmp_bundle / "automation.yaml"
            automation_doc = self._load_yaml(automation_path)
            automation_doc["trigger_registry"] = "empty-triggers.yaml"
            self._write_yaml(automation_path, automation_doc)

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    warning == "bundle: trigger registry is empty; trigger validation coverage is weakened"
                    for warning in report["warnings"]
                ),
                report["warnings"],
            )

    def test_validator_rejects_missing_source_anchor_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            anchors_path = (
                tmp_bundle
                / "skills"
                / "circle-of-competence"
                / "anchors.yaml"
            )
            anchors_doc = yaml.safe_load(anchors_path.read_text(encoding="utf-8"))
            anchors_doc["source_anchor_sets"] = []
            anchors_path.write_text(
                yaml.safe_dump(anchors_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any("source/scenario anchor" in error for error in report["errors"])
            )

    def test_validator_rejects_graph_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            manifest_path = tmp_bundle / "manifest.yaml"
            manifest_doc = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            manifest_doc["graph"]["graph_hash"] = "sha256:deadbeef"
            manifest_path.write_text(
                yaml.safe_dump(manifest_doc, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any("graph_hash" in error for error in report["errors"])
            )

    def test_migrate_graph_v01_to_v02_cli_updates_bundle_and_keeps_valid(self) -> None:
        for bundle_path in (self.bundle_path, self.engineering_bundle_path):
            with self.subTest(bundle=bundle_path.name):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_bundle = Path(tmp_dir) / "bundle"
                    shutil.copytree(bundle_path, tmp_bundle)

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "migrate_graph_v01_to_v02.py"),
                            str(tmp_bundle),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                    manifest = self._load_yaml(tmp_bundle / "manifest.yaml")
                    graph_doc = json.loads(
                        (tmp_bundle / manifest["graph"]["path"]).read_text(encoding="utf-8")
                    )
                    self.assertEqual(manifest["graph"]["graph_version"], "kiu.graph/v0.2")
                    self.assertEqual(graph_doc["graph_version"], "kiu.graph/v0.2")
                    self.assertTrue(graph_doc["graph_hash"].startswith("sha256:"))
                    self.assertEqual(manifest["graph"]["graph_hash"], graph_doc["graph_hash"])
                    self.assertIn("source_file", graph_doc["nodes"][0])
                    self.assertIn("source_location", graph_doc["nodes"][0])
                    self.assertIn("extraction_kind", graph_doc["nodes"][0])
                    self.assertIn("confidence", graph_doc["edges"][0])

                    first_skill = manifest["skills"][0]["skill_id"]
                    anchors = self._load_yaml(
                        tmp_bundle / "skills" / first_skill / "anchors.yaml"
                    )
                    self.assertEqual(anchors["graph_version"], "kiu.graph/v0.2")
                    self.assertEqual(anchors["graph_hash"], graph_doc["graph_hash"])

                    revisions = self._load_yaml(
                        tmp_bundle / "skills" / first_skill / "iterations" / "revisions.yaml"
                    )
                    self.assertEqual(
                        revisions["history"][0]["graph_hash"],
                        graph_doc["graph_hash"],
                    )

                    report = validate_bundle(tmp_bundle)
                    self.assertEqual(report["errors"], [], report["errors"])

    def test_validator_rejects_v02_extracted_edge_without_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            migrated = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "migrate_graph_v01_to_v02.py"),
                    str(tmp_bundle),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)

            manifest = self._load_yaml(tmp_bundle / "manifest.yaml")
            graph_path = tmp_bundle / manifest["graph"]["path"]
            graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
            graph_doc["edges"][0]["source_file"] = None
            graph_doc["graph_hash"] = self._canonical_graph_hash(graph_doc)
            graph_path.write_text(
                json.dumps(graph_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self._rewrite_bundle_graph_bindings(
                tmp_bundle,
                graph_hash=graph_doc["graph_hash"],
                graph_version=graph_doc["graph_version"],
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any("EXTRACTED edge missing source_file" in error for error in report["errors"]),
                report["errors"],
            )

    def test_validator_warns_when_published_bundle_has_many_ambiguous_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            migrated = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "migrate_graph_v01_to_v02.py"),
                    str(tmp_bundle),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)

            manifest = self._load_yaml(tmp_bundle / "manifest.yaml")
            graph_path = tmp_bundle / manifest["graph"]["path"]
            graph_doc = json.loads(graph_path.read_text(encoding="utf-8"))
            for edge in graph_doc["edges"][:3]:
                edge["extraction_kind"] = "AMBIGUOUS"
                edge["confidence"] = 0.5
                edge["source_file"] = None
            graph_doc["graph_hash"] = self._canonical_graph_hash(graph_doc)
            graph_path.write_text(
                json.dumps(graph_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self._rewrite_bundle_graph_bindings(
                tmp_bundle,
                graph_hash=graph_doc["graph_hash"],
                graph_version=graph_doc["graph_version"],
            )

            report = validate_bundle(tmp_bundle)

            self.assertEqual(report["errors"], [])
            self.assertTrue(
                any("ambiguous_edge_ratio" in warning for warning in report["warnings"]),
                report["warnings"],
            )

    def test_validator_rejects_unknown_trigger_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            self._replace_skill_text(
                tmp_bundle,
                "circle-of-competence",
                "user_considering_specific_investment",
                "user_considering_unknown_meme_stock",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    "unknown_trigger_symbol user_considering_unknown_meme_stock"
                    in error
                    for error in report["errors"]
                )
            )

    def test_validator_warns_when_trigger_registry_definition_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            registry_path = self._write_local_trigger_registry(tmp_bundle)
            registry_doc = self._load_yaml(registry_path)
            registry_doc["triggers"][0]["definition"] = ""
            self._write_yaml(registry_path, registry_doc)

            report = validate_bundle(tmp_bundle)

            self.assertEqual(report["errors"], [])
            self.assertTrue(
                any(
                    "trigger_symbol_missing_definition" in warning
                    for warning in report["warnings"]
                )
            )

    def test_validator_rejects_published_without_revision_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            manifest_path = tmp_bundle / "manifest.yaml"
            manifest_doc = self._load_yaml(manifest_path)
            manifest_doc["skills"][0]["skill_revision"] = 1
            self._write_yaml(manifest_path, manifest_doc)

            self._replace_skill_text(
                tmp_bundle,
                "circle-of-competence",
                f"skill_revision: {PUBLISHED_INVESTING_REVISION}",
                "skill_revision: 1",
            )

            eval_path = (
                tmp_bundle / "skills" / "circle-of-competence" / "eval" / "summary.yaml"
            )
            eval_doc = self._load_yaml(eval_path)
            eval_doc["skill_revision"] = 1
            self._write_yaml(eval_path, eval_doc)

            revisions_path = (
                tmp_bundle
                / "skills"
                / "circle-of-competence"
                / "iterations"
                / "revisions.yaml"
            )
            revisions_doc = self._load_yaml(revisions_path)
            revisions_doc["current_revision"] = 1
            revisions_doc["history"] = revisions_doc["history"][:1]
            self._write_yaml(revisions_path, revisions_doc)

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    "published skills must have gone through at least one revision cycle"
                    in error
                    for error in report["errors"]
                )
            )

    def test_validator_rejects_published_with_insufficient_eval_case_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            eval_path = (
                tmp_bundle / "skills" / "circle-of-competence" / "eval" / "summary.yaml"
            )
            eval_doc = self._load_yaml(eval_path)
            eval_doc["subsets"]["real_decisions"]["cases"] = [
                "biotech-founder-quantum-etf",
                "semiconductor-engineer-chipmaker-bet",
                "consumer-brand-fan-luxury-stock",
                "founder-buyout-outside-circle",
            ]
            eval_doc["subsets"]["real_decisions"]["total"] = 4
            eval_doc["subsets"]["real_decisions"]["passed"] = 4
            eval_doc["subsets"]["synthetic_adversarial"]["cases"] = [
                "tsla-surface-familiarity",
                "ai-tourist-deepfake-expert",
                "doctor-crypto-miner-confidence",
                "private-equity-brochure-overconfidence",
            ]
            eval_doc["subsets"]["synthetic_adversarial"]["total"] = 4
            eval_doc["subsets"]["synthetic_adversarial"]["passed"] = 4
            eval_doc["subsets"]["out_of_distribution"]["cases"] = [
                "career-offer-choice",
                "house-buying-decision",
            ]
            eval_doc["subsets"]["out_of_distribution"]["total"] = 2
            eval_doc["subsets"]["out_of_distribution"]["passed"] = 2
            self._write_yaml(eval_path, eval_doc)

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    "published requires real_decisions>=20, got 4 (need 16 more)"
                    in error
                    for error in report["errors"]
                )
            )
            self.assertTrue(
                any(
                    "published requires synthetic_adversarial>=20, got 4 (need 16 more)"
                    in error
                    for error in report["errors"]
                )
            )
            self.assertTrue(
                any(
                    "published requires out_of_distribution>=10, got 2 (need 8 more)"
                    in error
                    for error in report["errors"]
                )
            )

    def test_subset_count_rejects_inflated_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            eval_path = (
                tmp_bundle / "skills" / "circle-of-competence" / "eval" / "summary.yaml"
            )
            eval_doc = self._load_yaml(eval_path)
            eval_doc["subsets"]["real_decisions"]["cases"] = [
                "biotech-founder-quantum-etf",
                "semiconductor-engineer-chipmaker-bet",
                "consumer-brand-fan-luxury-stock",
                "founder-buyout-outside-circle",
            ]
            eval_doc["subsets"]["real_decisions"]["total"] = 20
            self._write_yaml(eval_path, eval_doc)

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    "circle-of-competence: real_decisions total=20 does not match resolved_cases=4"
                    in error
                    for error in report["errors"]
                ),
                report["errors"],
            )

    def test_subset_count_accepts_glob_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            eval_path = (
                tmp_bundle / "skills" / "circle-of-competence" / "eval" / "summary.yaml"
            )
            eval_doc = self._load_yaml(eval_path)
            eval_doc["subsets"]["real_decisions"]["cases"] = [
                "../../../evaluation/real_decisions/*.yaml"
            ]
            eval_doc["subsets"]["real_decisions"]["total"] = 20
            self._write_yaml(eval_path, eval_doc)

            report = validate_bundle(tmp_bundle)

            self.assertFalse(
                any(
                    "circle-of-competence: real_decisions total=20 does not match resolved_cases=20"
                    in error
                    for error in report["errors"]
                ),
                report["errors"],
            )
            self.assertEqual(
                next(
                    skill["eval_case_counts"]["real_decisions"]
                    for skill in report["skills"]
                    if skill["skill_id"] == "circle-of-competence"
                ),
                20,
            )

    def test_subset_count_rejects_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            eval_path = (
                tmp_bundle / "skills" / "circle-of-competence" / "eval" / "summary.yaml"
            )
            eval_doc = self._load_yaml(eval_path)
            eval_doc["subsets"]["real_decisions"]["cases"] = [
                "../../../evaluation/real_decisions/does-not-exist-*.yaml"
            ]
            eval_doc["subsets"]["real_decisions"]["total"] = 0
            self._write_yaml(eval_path, eval_doc)

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    "circle-of-competence: real_decisions cases pattern matched 0 files"
                    in error
                    for error in report["errors"]
                ),
                report["errors"],
            )

    def test_validator_allows_under_evaluation_with_small_eval_case_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            manifest_path = tmp_bundle / "manifest.yaml"
            manifest_doc = self._load_yaml(manifest_path)
            manifest_doc["skills"][0]["status"] = "under_evaluation"
            manifest_doc["skills"][0]["skill_revision"] = 1
            self._write_yaml(manifest_path, manifest_doc)

            self._replace_skill_text(
                tmp_bundle,
                "circle-of-competence",
                "status: published",
                "status: under_evaluation",
            )
            self._replace_skill_text(
                tmp_bundle,
                "circle-of-competence",
                f"skill_revision: {PUBLISHED_INVESTING_REVISION}",
                "skill_revision: 1",
            )

            eval_path = (
                tmp_bundle / "skills" / "circle-of-competence" / "eval" / "summary.yaml"
            )
            eval_doc = self._load_yaml(eval_path)
            eval_doc["status"] = "under_evaluation"
            eval_doc["skill_revision"] = 1
            eval_doc["subsets"]["real_decisions"]["total"] = 4
            eval_doc["subsets"]["synthetic_adversarial"]["total"] = 4
            eval_doc["subsets"]["out_of_distribution"]["total"] = 2
            self._write_yaml(eval_path, eval_doc)

            revisions_path = (
                tmp_bundle
                / "skills"
                / "circle-of-competence"
                / "iterations"
                / "revisions.yaml"
            )
            revisions_doc = self._load_yaml(revisions_path)
            revisions_doc["current_revision"] = 1
            revisions_doc["history"] = revisions_doc["history"][:1]
            self._write_yaml(revisions_path, revisions_doc)

            report = validate_bundle(tmp_bundle)

            self.assertFalse(
                any("published requires" in error for error in report["errors"]),
                report["errors"],
            )

    def test_validator_rejects_unknown_relation_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            self._replace_skill_text(
                tmp_bundle,
                "circle-of-competence",
                "  - bias-self-audit",
                "  - unknown-skill",
            )

            report = validate_bundle(tmp_bundle)

            self.assertTrue(
                any(
                    "unknown relation target unknown-skill" in error
                    for error in report["errors"]
                )
            )

    def test_validator_allows_external_relation_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            self._replace_skill_text(
                tmp_bundle,
                "circle-of-competence",
                "  - bias-self-audit",
                "  - external:reference-bundle:bias-self-audit",
            )

            report = validate_bundle(tmp_bundle)

            self.assertEqual(report["errors"], [])

    def test_validator_resolves_external_relation_target_with_merge_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)

            self._replace_skill_text(
                primary_bundle,
                "circle-of-competence",
                "  - bias-self-audit",
                "  - external:reference-bundle:bias-self-audit",
            )
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            report = validate_bundle(primary_bundle, merge_with=[reference_bundle])

            self.assertEqual(report["errors"], [])

    def test_validator_accepts_legacy_external_relation_target_with_merge_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)

            self._replace_skill_text(
                primary_bundle,
                "circle-of-competence",
                "  - bias-self-audit",
                "  - external:reference-bundle/bias-self-audit",
            )
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            report = validate_bundle(primary_bundle, merge_with=[reference_bundle])

            self.assertEqual(report["errors"], [])

    def test_validator_rejects_unresolved_external_relation_target_when_merge_context_provided(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)

            self._replace_skill_text(
                primary_bundle,
                "circle-of-competence",
                "  - bias-self-audit",
                "  - external:reference-bundle:missing-skill",
            )
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            report = validate_bundle(primary_bundle, merge_with=[reference_bundle])

            self.assertTrue(
                any(
                    "unknown external relation target external:reference-bundle:missing-skill"
                    in error
                    for error in report["errors"]
                ),
                report["errors"],
            )

    def test_validator_accepts_legacy_autonomous_refiner_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_bundle = Path(tmp_dir) / "bundle"
            shutil.copytree(self.bundle_path, tmp_bundle)

            automation_path = tmp_bundle / "automation.yaml"
            automation_doc = self._load_yaml(automation_path)
            automation_doc["autonomous_refiner"] = automation_doc.pop("refinement_scheduler")
            self._write_yaml(automation_path, automation_doc)

            report = validate_bundle(tmp_bundle)

            self.assertEqual(report["errors"], [])

    def test_cli_reports_success_for_reference_bundle(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_bundle.py"),
                str(self.bundle_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VALID", result.stdout)

    def test_cli_reports_success_with_merge_with_reference_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)

            self._replace_skill_text(
                primary_bundle,
                "circle-of-competence",
                "  - bias-self-audit",
                "  - external:reference-bundle:bias-self-audit",
            )
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_bundle.py"),
                    str(primary_bundle),
                    "--merge-with",
                    str(reference_bundle),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VALID", result.stdout)

    def test_v03_foundation_includes_trigger_registry_assets(self) -> None:
        self.assertTrue((ROOT / "shared_profiles" / "investing" / "triggers.yaml").exists())
        self.assertTrue((ROOT / "schemas" / "trigger-registry.schema.yaml").exists())

    def test_v05_engineering_profile_assets_exist(self) -> None:
        self.assertTrue((ROOT / "shared_profiles" / "engineering" / "profile.yaml").exists())
        self.assertTrue((ROOT / "shared_profiles" / "engineering" / "triggers.yaml").exists())

    def test_v03_release_assets_exist(self) -> None:
        self.assertTrue((ROOT / ".github" / "workflows" / "ci.yml").exists())
        self.assertTrue((ROOT / "docs" / "kiu-skill-spec-v0.3.md").exists())
        self.assertTrue((ROOT / "docs" / "CONTRIBUTING.md").exists())
        self.assertTrue(
            (
                ROOT
                / "workflow_candidates"
                / "examples"
                / "dcf-basic-valuation"
                / "steps.yaml"
            ).exists()
        )
        self.assertTrue((ROOT / "schemas" / "workflow-candidate.schema.yaml").exists())

    def test_release_has_usage_guide_with_design_rationale(self) -> None:
        usage_guide = ROOT / "docs" / "usage-guide.md"
        self.assertTrue(usage_guide.exists())

        content = usage_guide.read_text(encoding="utf-8")
        self.assertIn("# KiU v0.1 Usage Guide", content)
        self.assertIn("## Quick Start", content)
        self.assertIn("## Repository Layout", content)
        self.assertIn("## How To Read A Skill", content)
        self.assertIn("## How To Extend The Bundle", content)
        self.assertIn("## Design Rationale", content)
        self.assertIn("## Workflow Script Artifact Example", content)


if __name__ == "__main__":
    unittest.main()
