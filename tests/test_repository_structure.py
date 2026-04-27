import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [part.decode("utf-8") for part in result.stdout.split(b"\0") if part]


class RepositoryStructureTests(unittest.TestCase):
    def test_tracked_root_directories_are_intentional(self) -> None:
        allowed = {
            ".github",
            "_archive",
            "backlog",
            "benchmarks",
            "bundles",
            "docs",
            "evidence",
            "examples",
            "installable-skills",
            "review-pack",
            "schemas",
            "scripts",
            "shared_profiles",
            "skills",
            "src",
            "tests",
        }
        tracked_dirs = {
            path.split("/", 1)[0]
            for path in _tracked_paths()
            if "/" in path
        }

        self.assertEqual(tracked_dirs, allowed)

    def test_legacy_and_local_output_directories_are_not_tracked(self) -> None:
        forbidden_prefixes = (
            "reports/",
            "notion-export/",
            "workflow_candidates/",
            "generated/",
            "dist/",
            "build/",
            "tmp/",
            ".worktrees/",
            ".references/",
        )
        tracked = _tracked_paths()

        offenders = [
            path
            for path in tracked
            if path.startswith(forbidden_prefixes) or "/__pycache__/" in path or path.endswith(".egg-info/SOURCES.txt")
        ]
        self.assertEqual(offenders, [])

    def test_local_build_outputs_are_gitignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        for pattern in ("dist/", "build/", "src/*.egg-info/"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, gitignore)

    def test_archive_has_explicit_boundary_index(self) -> None:
        archive_readme = ROOT / "_archive" / "README.md"

        self.assertTrue(archive_readme.exists())
        content = archive_readme.read_text(encoding="utf-8")
        self.assertIn("not a current entry point", content)
        self.assertIn("not used by the default generation pipeline", content)

    def test_example_fixtures_point_to_current_source_materials(self) -> None:
        fixture_paths = sorted((ROOT / "examples" / "fixtures").glob("*.yaml"))
        self.assertGreaterEqual(len(fixture_paths), 2)

        for fixture_path in fixture_paths:
            text = fixture_path.read_text(encoding="utf-8")
            self.assertNotIn("examples/sources/", text)
            for line in text.splitlines():
                if line.startswith("source_markdown:"):
                    source_path = ROOT / line.split(":", 1)[1].strip()
                    self.assertTrue(source_path.exists(), f"missing source for {fixture_path}: {source_path}")

    def test_current_review_pack_manifest_matches_visible_books(self) -> None:
        manifest_path = ROOT / "review-pack" / "current" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        books_root = ROOT / "review-pack" / "current" / "books"
        visible_books = {path.name for path in books_root.iterdir() if path.is_dir()}
        manifest_books = {book["id"] for book in manifest["books"]}

        self.assertEqual(visible_books, manifest_books)

        for book in manifest["books"]:
            book_root = books_root / book["id"]
            self.assertTrue((book_root / "source-card.md").exists(), book["id"])
            self.assertTrue((book_root / "scorecard.md").exists(), book["id"])
            self.assertTrue((book_root / "sources").exists(), book["id"])
            self.assertTrue((book_root / "generated-skills").exists(), book["id"])

    def test_current_review_pack_skills_use_value_gain_pressure_chain(self) -> None:
        skill_paths = sorted((ROOT / "review-pack" / "current" / "books").glob("*/generated-skills/*/SKILL.md"))
        self.assertEqual(len(skill_paths), 21)

        forbidden_external_method_names = (
            "模块价值增益法",
            "thinking-value-gain",
            "Premature Exit Check",
        )
        required_markers = (
            "value_gain_decision",
            "value_gain_evidence",
            "value_gain_risk_boundary",
            "value_gain_next_handoff",
            "Downstream Use Check",
            "Minimum Pressure Pass",
        )
        for skill_path in skill_paths:
            content = skill_path.read_text(encoding="utf-8")
            with self.subTest(skill=skill_path.relative_to(ROOT).as_posix()):
                for marker in required_markers:
                    self.assertIn(marker, content)
                for forbidden in forbidden_external_method_names:
                    self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
