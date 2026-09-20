#!/usr/bin/env python3
"""Auto-increment the wcag-skill version ahead of a ClawHub publish.

Both publish workflows (publish-web.yml and publish-to-clawhub.yml) run this
before publishing so nobody has to remember to hand-bump SKILL.md. It compares
the version recorded in SKILL.md against every version ClawHub already has on
record for this skill, takes the highest of the two, and bumps the patch
component by one. That guarantees the next publish never collides with a
version that already exists — including one published by a previous run that
looked like it failed (see the "pending-publication" status bug documented in
publish-to-clawhub.yml) — without anyone manually editing version numbers.

Keeps SKILL.md's metadata.version, README.md's version badge, and
skill-card.md's version note in sync.

Usage:
  scripts/bump-skill-version.py            # print the next version only
  scripts/bump-skill-version.py --write    # also update files on disk
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = ROOT / "SKILL.md"
README_MD = ROOT / "README.md"
SKILL_CARD_MD = ROOT / "skill-card.md"
SKILL_SLUG = "wcag-skill"

Version = tuple[int, int, int]


def read_local_version() -> str:
    """Extract metadata.version from SKILL.md frontmatter."""
    content = SKILL_MD.read_text()
    match = re.search(r"^\s*version:\s*['\"]?([^'\"\s]+)", content, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find metadata.version in SKILL.md")
    return match.group(1)


def read_live_versions() -> list[str]:
    """Return every version ClawHub already has for this skill.

    Returns an empty list if the skill has never been published or the
    registry can't be reached, so a first-ever publish still works offline.
    """
    url = f"https://clawhub.ai/api/v1/skills/{SKILL_SLUG}/versions"
    try:
        with urlopen(url, timeout=15) as resp:
            data = json.load(resp)
        return [item["version"] for item in data.get("items", [])]
    except (URLError, HTTPError, ValueError, KeyError):
        return []


def parse_version(value: str) -> Version:
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise SystemExit(f"Version {value!r} is not in MAJOR.MINOR.PATCH form")
    major, minor, patch = (int(part) for part in parts)
    return (major, minor, patch)


def format_version(version: Version) -> str:
    return ".".join(str(part) for part in version)


def next_version() -> str:
    candidates = [parse_version(read_local_version())]
    candidates += [parse_version(v) for v in read_live_versions()]
    major, minor, patch = max(candidates)
    return format_version((major, minor, patch + 1))


def apply(version: str) -> None:
    """Rewrite the version in every file that mirrors it, or fail loudly."""
    replacements = (
        (SKILL_MD, r"(?m)^(\s*version:\s*)['\"]?[^'\"\s]+", rf"\g<1>{version}"),
        (README_MD, r"(badge/version-)[^-]+(-blue)", rf"\g<1>{version}\g<2>"),
        (
            SKILL_CARD_MD,
            r"(?m)^\d+\.\d+\.\d+(?= \(source: `SKILL\.md`)",
            version,
        ),
    )
    for path, pattern, replacement in replacements:
        text = path.read_text()
        new_text, count = re.subn(pattern, replacement, text, count=1)
        if count == 0:
            raise SystemExit(f"Failed to update version in {path}")
        path.write_text(new_text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Write the bumped version to disk"
    )
    args = parser.parse_args()

    version = next_version()
    if args.write:
        apply(version)
    print(version)


if __name__ == "__main__":
    main()
