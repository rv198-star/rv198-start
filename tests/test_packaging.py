import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingMetadataTests(unittest.TestCase):
    def test_pyproject_declares_pyyaml_dependency(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = pyproject["project"].get("dependencies", [])

        self.assertTrue(
            any(dep.lower().startswith("pyyaml") for dep in dependencies),
            "pyproject.toml must declare PyYAML so a clean install can run validator and pipeline commands.",
        )

    def test_pyproject_version_is_not_behind_latest_changelog_release(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        version = pyproject["project"]["version"]
        releases = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, flags=re.MULTILINE)

        self.assertTrue(releases, "CHANGELOG.md must contain at least one released version section.")
        latest_release = releases[0]
        self.assertGreaterEqual(
            tuple(int(part) for part in version.split(".")),
            tuple(int(part) for part in latest_release.split(".")),
            "pyproject.toml version must not lag behind the latest released version recorded in CHANGELOG.md.",
        )

    def test_changelog_records_v042_release(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIsNotNone(
            re.search(r"^## \[0\.4\.2\] - ", changelog, flags=re.MULTILINE),
            "CHANGELOG.md must record the v0.4.2 release section.",
        )

    def test_notice_and_third_party_attribution_document_v06_references(self) -> None:
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        attribution = (ROOT / "docs" / "third-party-attribution.md").read_text(encoding="utf-8")

        self.assertIn("Graphify", notice)
        self.assertIn("cangjie-skill", notice)
        self.assertIn("No third-party source files are vendored", notice)

        self.assertIn("Graphify", attribution)
        self.assertIn("cangjie-skill", attribution)
        self.assertIn("core ideas only", attribution)
        self.assertIn("not the surrounding tooling surface", attribution)
        self.assertIn("provenance-rich graph schema", attribution)
        self.assertIn("RIA-TV++", attribution)

    def test_v06_schema_and_example_assets_exist(self) -> None:
        self.assertTrue((ROOT / "docs" / "kiu-skill-spec-v0.6.md").exists())
        self.assertTrue((ROOT / "schemas" / "source-chunks-v0.1.json").exists())
        self.assertTrue((ROOT / "schemas" / "graph-v0.2.json").exists())
        self.assertTrue((ROOT / "schemas" / "extraction-results-v0.1.json").exists())
        examples_readme = ROOT / "examples" / "README.md"
        self.assertTrue(examples_readme.exists())

        content = examples_readme.read_text(encoding="utf-8")
        self.assertIn("有效需求分析（第2版）", content)
        self.assertIn("财务报表分析_Markdown版", content)
        self.assertIn("source/extraction", content)
        self.assertIn("not mixed into a single skill bundle", content)


if __name__ == "__main__":
    unittest.main()
