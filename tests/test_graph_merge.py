import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_graph.merge import merge_bundle_graphs


class GraphMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle_path = ROOT / "bundles" / "poor-charlies-almanack-v0.1"

    def _load_yaml(self, path: Path) -> dict:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _write_yaml(self, path: Path, doc: dict) -> None:
        path.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def _rewrite_bundle_id(self, bundle_root: Path, bundle_id: str) -> None:
        manifest_path = bundle_root / "manifest.yaml"
        manifest = self._load_yaml(manifest_path)
        manifest["bundle_id"] = bundle_id
        self._write_yaml(manifest_path, manifest)

    def test_merge_bundle_graphs_hash_is_order_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            merged_ab = merge_bundle_graphs([primary_bundle, reference_bundle])
            merged_ba = merge_bundle_graphs([reference_bundle, primary_bundle])

            self.assertEqual(merged_ab["graph_hash"], merged_ba["graph_hash"])
            self.assertEqual(merged_ab, merged_ba)

    def test_merge_bundle_graphs_namespaces_entities_by_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            merged = merge_bundle_graphs([primary_bundle, reference_bundle])
            node_ids = {node["id"] for node in merged["nodes"]}

            self.assertIn(
                "poor-charlies-almanack-v0.1::n_circle_principle",
                node_ids,
            )
            self.assertIn("reference-bundle::n_circle_principle", node_ids)

            edge = next(
                edge
                for edge in merged["edges"]
                if edge["id"] == "reference-bundle::e_circle_dotcom_supports"
            )
            self.assertEqual(
                edge["from"],
                "reference-bundle::n_circle_principle",
            )
            self.assertEqual(
                edge["to"],
                "reference-bundle::n_dotcom_refusal_trace",
            )

            community = next(
                community
                for community in merged["communities"]
                if community["id"] == "reference-bundle::c_boundary_discipline"
            )
            self.assertIn(
                "reference-bundle::n_bias_principle",
                community["node_ids"],
            )

    def test_merge_graphs_cli_writes_output_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            output_path = tmp_root / "merged_graph.json"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "merge_graphs.py"),
                    str(primary_bundle),
                    str(reference_bundle),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            merged = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                merged["source_bundles"],
                ["poor-charlies-almanack-v0.1", "reference-bundle"],
            )
            self.assertTrue(merged["graph_hash"].startswith("sha256:"))

    def test_merge_bundle_graphs_preserves_v02_provenance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            primary_bundle = tmp_root / "primary"
            reference_bundle = tmp_root / "reference"
            shutil.copytree(self.bundle_path, primary_bundle)
            shutil.copytree(self.bundle_path, reference_bundle)
            self._rewrite_bundle_id(reference_bundle, "reference-bundle")

            for bundle_root in (primary_bundle, reference_bundle):
                migrated = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "migrate_graph_v01_to_v02.py"),
                        str(bundle_root),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)

            merged = merge_bundle_graphs([primary_bundle, reference_bundle])

            self.assertEqual(merged["graph_version"], "kiu.graph.merge/v0.2")
            first_node = merged["nodes"][0]
            first_edge = merged["edges"][0]
            self.assertIn("source_file", first_node)
            self.assertIn("source_location", first_node)
            self.assertIn("extraction_kind", first_node)
            self.assertIn("source_file", first_edge)
            self.assertIn("source_location", first_edge)
            self.assertIn("extraction_kind", first_edge)
            self.assertIn("confidence", first_edge)

    def test_merge_bundle_graphs_derives_cross_bundle_inferred_links(self) -> None:
        merged = merge_bundle_graphs(
            [
                ROOT / "bundles" / "poor-charlies-almanack-v0.1",
                ROOT / "bundles" / "engineering-postmortem-v0.1",
            ]
        )

        inferred_edges = [
            edge
            for edge in merged["edges"]
            if edge.get("cross_bundle")
            and edge.get("extraction_kind") in {"INFERRED", "AMBIGUOUS"}
        ]

        self.assertGreater(len(inferred_edges), 0)
        margin_to_blast = next(
            (
                edge
                for edge in inferred_edges
                if edge["from"] == "poor-charlies-almanack-v0.1::n_margin_principle"
                and edge["to"] == "engineering-postmortem-v0.1::n_blast_radius_principle"
            ),
            None,
        )
        self.assertIsNotNone(margin_to_blast)
        assert margin_to_blast is not None
        self.assertLess(float(margin_to_blast["confidence"]), 1.0)
        self.assertGreater(float(margin_to_blast["confidence"]), 0.0)
        self.assertTrue(margin_to_blast.get("support_refs"))
        self.assertIn("shared_concepts", margin_to_blast)


if __name__ == "__main__":
    unittest.main()
