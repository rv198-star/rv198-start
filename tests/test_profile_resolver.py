import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import warnings

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.load import load_source_bundle
from kiu_pipeline.profile_resolver import resolve_profile


class ProfileResolverTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"

    def test_resolve_profile_loads_default_and_domain_overrides(self) -> None:
        profile = resolve_profile(self.bundle_path)

        self.assertEqual(profile["domain"], "investing")
        self.assertEqual(profile["resolved_from"], ["default", "investing", "bundle"])
        self.assertEqual(profile["refinement_scheduler"]["weights"]["boundary_quality"], 0.45)
        self.assertEqual(profile["refinement_scheduler"]["targets"]["production_quality"], 0.82)
        self.assertEqual(profile["published_min_eval_cases"]["real_decisions"], 20)
        self.assertEqual(profile["rationale_density"]["min_anchor_refs"], 2)

    def test_load_source_bundle_exposes_resolved_profile(self) -> None:
        bundle = load_source_bundle(self.bundle_path)

        self.assertEqual(bundle.domain, "investing")
        self.assertEqual(bundle.profile["domain"], "investing")
        self.assertIn("published_min_eval_cases", bundle.profile)
        self.assertEqual(bundle.profile["refinement_scheduler"]["targets"]["overall_quality"], 0.82)

    def test_resolve_profile_returns_isolated_copy_from_cache(self) -> None:
        first = resolve_profile(self.bundle_path)
        first["refinement_scheduler"]["max_rounds"] = 99

        second = resolve_profile(self.bundle_path)

        self.assertEqual(second["refinement_scheduler"]["max_rounds"], 5)

    def test_legacy_refiner_key_emits_deprecation_warning_and_normalizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir) / "bundle"
            tmp_root.mkdir(parents=True)
            manifest = {
                "bundle_id": "demo",
                "bundle_version": "0.1.0",
                "domain": "investing",
                "graph": {
                    "path": "graph/graph.json",
                    "graph_version": "kiu.graph/v0.1",
                    "graph_hash": "sha256:test",
                },
                "skills": [],
            }
            (tmp_root / "manifest.yaml").write_text(
                yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            (tmp_root / "automation.yaml").write_text(
                yaml.safe_dump(
                    {
                        "inherits": "investing",
                        "autonomous_refiner": {"max_rounds": 9},
                    },
                    sort_keys=False,
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            (tmp_root / "graph").mkdir()
            (tmp_root / "graph" / "graph.json").write_text(
                json.dumps(
                    {
                        "graph_version": "kiu.graph/v0.1",
                        "graph_hash": "sha256:test",
                        "nodes": [],
                        "edges": [],
                        "communities": [],
                    }
                ),
                encoding="utf-8",
            )

            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                profile = resolve_profile(tmp_root)

            self.assertEqual(profile["refinement_scheduler"]["max_rounds"], 9)
            self.assertNotIn("autonomous_refiner", profile)
            self.assertTrue(
                any("autonomous_refiner is deprecated" in str(item.message) for item in captured)
            )

    def test_show_profile_cli_prints_resolved_profile(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "show_profile.py"),
                str(self.bundle_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        profile = yaml.safe_load(result.stdout)
        self.assertEqual(profile["domain"], "investing")
        self.assertIn("refinement_scheduler", profile)

    def test_missing_domain_profile_fails_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir) / "bundle"
            tmp_root.mkdir(parents=True)
            manifest = {
                "bundle_id": "demo",
                "bundle_version": "0.1.0",
                "domain": "unknown-domain",
                "graph": {
                    "path": "graph/graph.json",
                    "graph_version": "kiu.graph/v0.1",
                    "graph_hash": "sha256:test",
                },
                "skills": [],
            }
            (tmp_root / "manifest.yaml").write_text(
                yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            (tmp_root / "automation.yaml").write_text(
                yaml.safe_dump({"inherits": "unknown-domain"}, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            (tmp_root / "graph").mkdir()
            (tmp_root / "graph" / "graph.json").write_text(
                json.dumps({"graph_version": "kiu.graph/v0.1", "graph_hash": "sha256:test", "nodes": [], "edges": [], "communities": []}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(FileNotFoundError, "unknown-domain"):
                resolve_profile(tmp_root)


if __name__ == "__main__":
    unittest.main()
