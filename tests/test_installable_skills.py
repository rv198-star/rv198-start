import re
import shutil
import subprocess
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        raise AssertionError("missing YAML frontmatter")
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


class InstallableSkillsTests(unittest.TestCase):
    def test_kiu_project_skill_is_installable(self) -> None:
        skill_dir = ROOT / "skills" / "kiu"
        skill_md = skill_dir / "SKILL.md"

        self.assertTrue(skill_md.exists())
        frontmatter = _frontmatter(skill_md.read_text(encoding="utf-8"))
        self.assertEqual(frontmatter["name"], "kiu")
        self.assertIn("Knowledge in Use", frontmatter["description"])

        for reference in (
            "project-boundaries.md",
            "generation-workflow.md",
            "distribution-workflow.md",
        ):
            self.assertTrue((skill_dir / "references" / reference).exists(), reference)

    def test_exporter_writes_installable_generated_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "installable-skills"
            subprocess.run(
                [
                    "python3",
                    "scripts/export_installable_skills.py",
                    "--review-pack",
                    "review-pack/current",
                    "--output",
                    str(output),
                    "--clean",
                ],
                cwd=ROOT,
                check=True,
            )

            manifest_path = output / "manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "kiu.installable-skills/v0.1")
            self.assertEqual(manifest["skill_count"], 21)

            names = [skill["install_name"] for skill in manifest["skills"]]
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(all(name.startswith("kiu-") for name in names))

            for skill in manifest["skills"]:
                skill_dir = output / skill["install_name"]
                skill_md = skill_dir / "SKILL.md"
                provenance = skill_dir / "references" / "provenance.md"
                self.assertTrue(skill_md.exists(), skill["install_name"])
                self.assertTrue(provenance.exists(), skill["install_name"])
                frontmatter = _frontmatter(skill_md.read_text(encoding="utf-8"))
                self.assertEqual(frontmatter["name"], skill["install_name"])
                self.assertIn("description", frontmatter)

    def test_committed_installable_skills_are_valid(self) -> None:
        manifest_path = ROOT / "installable-skills" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["skill_count"], 21)

        names = [skill["install_name"] for skill in manifest["skills"]]
        self.assertEqual(len(names), len(set(names)))

        for skill in manifest["skills"]:
            skill_md = ROOT / "installable-skills" / skill["path"]
            text = skill_md.read_text(encoding="utf-8")
            frontmatter = _frontmatter(text)
            self.assertEqual(frontmatter["name"], skill["install_name"])
            for marker in (
                "value_gain_decision",
                "value_gain_evidence",
                "value_gain_risk_boundary",
                "value_gain_next_handoff",
                "Downstream Use Check",
                "Minimum Pressure Pass",
            ):
                self.assertIn(marker, text)

    def test_local_install_smoke_discovers_project_and_generated_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skills_home = Path(tmp) / "skills"
            skills_home.mkdir(parents=True)

            shutil.copytree(ROOT / "skills" / "kiu", skills_home / "kiu")
            manifest = json.loads((ROOT / "installable-skills" / "manifest.json").read_text(encoding="utf-8"))
            for skill in manifest["skills"]:
                shutil.copytree(ROOT / "installable-skills" / skill["install_name"], skills_home / skill["install_name"])

            discovered = sorted(path.parent.name for path in skills_home.glob("*/SKILL.md"))
            self.assertEqual(len(discovered), 22)
            self.assertIn("kiu", discovered)
            self.assertEqual(len(discovered), len(set(discovered)))


if __name__ == "__main__":
    unittest.main()
