#!/usr/bin/env python3
"""Print the SKILL.md frontmatter version — the source of truth for ClawHub sync.

Unlike bump-skill-version.py (which computes the *next* version), this just
reports the version the repo currently declares. The publish-web workflow uses
it as the target it forces ClawHub to match, instead of auto-bumping off the
checked-in version (which is what let the repo drift ahead of a stuck ClawHub
release).

Usage:  scripts/read-version.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_frontmatter_version(skill_md: Path) -> str:
    content = skill_md.read_text()
    fm = re.match(r"(?s)^\s*---\n(.*?)\n---\n", content)
    if not fm:
        raise SystemExit("Could not find YAML frontmatter in SKILL.md")
    match = re.search(r"(?m)^\s*version:\s*['\"]?([^'\"\s]+)", fm.group(1))
    if not match:
        raise SystemExit("Could not find metadata.version in SKILL.md frontmatter")
    return match.group(1)


def main() -> None:
    print(read_frontmatter_version(ROOT / "SKILL.md"))


if __name__ == "__main__":
    main()
