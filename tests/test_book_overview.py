import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kiu_pipeline.book_overview import (
    build_book_overview_doc,
    render_book_overview_markdown,
    validate_book_overview_doc,
)
from kiu_pipeline.source_chunks import build_source_chunks_from_markdown


class BookOverviewTests(unittest.TestCase):
    def test_build_book_overview_doc_emits_context_contract(self) -> None:
        source_chunks_doc = build_source_chunks_from_markdown(
            input_path=ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md",
            bundle_id="demo-source-bundle",
            source_id="effective-requirements-analysis",
            max_chars=240,
        )

        overview_doc = build_book_overview_doc(source_chunks_doc)

        self.assertEqual(validate_book_overview_doc(overview_doc), [])
        self.assertEqual(overview_doc["schema_version"], "kiu.book-overview/v0.1")
        self.assertEqual(overview_doc["source_id"], "effective-requirements-analysis")
        self.assertGreaterEqual(overview_doc["chapter_count"], 3)
        self.assertGreaterEqual(overview_doc["section_count"], 3)
        self.assertTrue(overview_doc["chapter_map"])
        self.assertIn(
            "Problem-First Requirements Analysis",
            [entry["chapter"] for entry in overview_doc["chapter_map"]],
        )
        self.assertTrue(overview_doc["thesis_summary"])
        self.assertIn("requirements-analysis", overview_doc["domain_tags"])
        self.assertTrue(overview_doc["boundary_warnings"])

        overview_markdown = render_book_overview_markdown(overview_doc)
        self.assertIn("# BOOK_OVERVIEW", overview_markdown)
        self.assertIn("## Thesis Summary", overview_markdown)
        self.assertIn("## Boundary Warnings", overview_markdown)
        self.assertIn("## Domain Tags", overview_markdown)

    def test_run_book_pipeline_cli_emits_book_overview_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "artifacts"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_book_pipeline.py"),
                    "--input",
                    str(ROOT / "examples" / "sources" / "effective-requirements-analysis-source.md"),
                    "--bundle-id",
                    "demo-source-bundle",
                    "--source-id",
                    "effective-requirements-analysis",
                    "--run-id",
                    "book-overview-smoke",
                    "--output-root",
                    str(output_root),
                    "--max-chars",
                    "240",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)

            source_bundle_root = Path(payload["source_bundle_root"])
            book_overview_path = Path(payload["book_overview_path"])
            book_overview_json_path = Path(payload["book_overview_json_path"])

            self.assertEqual(book_overview_path, source_bundle_root / "BOOK_OVERVIEW.md")
            self.assertEqual(
                book_overview_json_path,
                source_bundle_root / "ingestion" / "book-overview-v0.1.json",
            )
            self.assertTrue(book_overview_path.exists())
            self.assertTrue(book_overview_json_path.exists())

            overview_doc = json.loads(book_overview_json_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_book_overview_doc(overview_doc), [])
            self.assertIn("requirements-analysis", overview_doc["domain_tags"])

            overview_markdown = book_overview_path.read_text(encoding="utf-8")
            self.assertIn("# BOOK_OVERVIEW", overview_markdown)
            self.assertIn("Problem-First Requirements Analysis", overview_markdown)
            self.assertIn("## Boundary Warnings", overview_markdown)


if __name__ == "__main__":
    unittest.main()
