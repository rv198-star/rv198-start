#!/usr/bin/env python3
import argparse
import json
import re
import shutil
from pathlib import Path


def _slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + len("\n---\n"):].lstrip()
    return text.lstrip()


def _write_skill(review_pack: Path, output: Path, book: dict, skill_dir: Path) -> dict:
    source_id = book["id"]
    skill_id = skill_dir.name
    install_name = f"kiu-{_slug(source_id)}-{_slug(skill_id)}"
    target_dir = output / install_name
    target_ref_dir = target_dir / "references"
    target_ref_dir.mkdir(parents=True, exist_ok=True)

    source_skill_md = skill_dir / "SKILL.md"
    if not source_skill_md.exists():
        raise FileNotFoundError(source_skill_md)

    body = _strip_frontmatter(source_skill_md.read_text(encoding="utf-8"))
    description = f"Use this KiU-generated action skill from {book['title']} when the task matches `{skill_id}`."
    target_skill = "\n".join(
        [
            "---",
            f"name: {install_name}",
            f"description: {description}",
            "---",
            "",
            body,
        ]
    )
    (target_dir / "SKILL.md").write_text(target_skill, encoding="utf-8")

    provenance = "\n".join(
        [
            "# Provenance",
            "",
            "- Project: KiU / Knowledge in Use / 学以致用",
            f"- Source book id: `{source_id}`",
            f"- Source book title: `{book['title']}`",
            f"- Original skill id: `{skill_id}`",
            f"- Install name: `{install_name}`",
            f"- Run id: `{book['run_id']}`",
            f"- Pipeline mode: `{book['pipeline_mode']}`",
            f"- Review pack: `{review_pack.as_posix()}`",
            "",
            "This installable skill is generated from the current KiU review pack. Internal scores do not prove external blind review, real-user validation, or domain-expert validation.",
        ]
    )
    (target_ref_dir / "provenance.md").write_text(provenance, encoding="utf-8")

    return {
        "install_name": install_name,
        "source_book_id": source_id,
        "source_book_title": book["title"],
        "original_skill_id": skill_id,
        "path": f"{install_name}/SKILL.md",
        "provenance": f"{install_name}/references/provenance.md",
    }


def export_installable_skills(review_pack: Path, output: Path, clean: bool) -> dict:
    manifest_path = review_pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    skills = []
    seen = set()
    for book in manifest["books"]:
        skill_root = review_pack / "books" / book["id"] / "generated-skills"
        for skill_dir in sorted(path for path in skill_root.iterdir() if path.is_dir()):
            entry = _write_skill(review_pack=review_pack, output=output, book=book, skill_dir=skill_dir)
            if entry["install_name"] in seen:
                raise ValueError(f"duplicate install name: {entry['install_name']}")
            seen.add(entry["install_name"])
            skills.append(entry)

    install_manifest = {
        "schema_version": "kiu.installable-skills/v0.1",
        "project": "KiU / Knowledge in Use / 学以致用",
        "source_review_pack": review_pack.as_posix(),
        "skill_count": len(skills),
        "skills": skills,
    }
    (output / "manifest.json").write_text(
        json.dumps(install_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return install_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-pack", default="review-pack/current")
    parser.add_argument("--output", default="installable-skills")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    result = export_installable_skills(
        review_pack=Path(args.review_pack),
        output=Path(args.output),
        clean=args.clean,
    )
    print(json.dumps({"skill_count": result["skill_count"], "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
