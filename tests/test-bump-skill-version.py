#!/usr/bin/env python3
"""Offline regression test for the auto version-bump logic.

Exercises next_version()/apply() against temporary copies of SKILL.md,
README.md, and skill-card.md so it never hits the network or mutates the
real repository files.
"""
import importlib.util
import shutil
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "scripts" / "bump-skill-version.py"

spec = importlib.util.spec_from_file_location("bump_skill_version", SOURCE)
assert spec and spec.loader
bump_skill_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bump_skill_version)

# --- parse/format round-trip and validation -------------------------------
assert bump_skill_version.parse_version("2.0.5") == (2, 0, 5)
assert bump_skill_version.format_version((2, 0, 5)) == "2.0.5"
try:
    bump_skill_version.parse_version("2.0")
    raise AssertionError("expected a malformed version to be rejected")
except SystemExit:
    pass

# --- next_version() picks the max of local vs. live, then bumps patch ----
with mock.patch.object(bump_skill_version, "read_local_version", return_value="2.0.5"), \
     mock.patch.object(bump_skill_version, "read_live_versions", return_value=["2.0.4", "2.0.3"]):
    assert bump_skill_version.next_version() == "2.0.6"

# A prior run that silently published ahead of the checked-in version (the
# "pending-publication" bug) must still be detected and outrun.
with mock.patch.object(bump_skill_version, "read_local_version", return_value="2.0.3"), \
     mock.patch.object(bump_skill_version, "read_live_versions", return_value=["2.0.5"]):
    assert bump_skill_version.next_version() == "2.0.6"

# Registry unreachable / never-published skill: fall back to local only.
with mock.patch.object(bump_skill_version, "read_local_version", return_value="1.0.0"), \
     mock.patch.object(bump_skill_version, "read_live_versions", return_value=[]):
    assert bump_skill_version.next_version() == "1.0.1"

# --- apply() rewrites all three mirrored files ----------------------------
tmp_dir = Path(tempfile.mkdtemp())
try:
    skill_md = tmp_dir / "SKILL.md"
    readme_md = tmp_dir / "README.md"
    skill_card_md = tmp_dir / "skill-card.md"

    skill_md.write_text("---\nname: wcag-skill\nmetadata:\n  version: 2.0.5\n---\n")
    readme_md.write_text(
        "[![Version](https://img.shields.io/badge/version-2.0.5-blue)](x)\n"
    )
    skill_card_md.write_text(
        "## Skill Version\n\n2.0.5 (source: `SKILL.md` metadata; more text).\n"
    )

    with mock.patch.object(bump_skill_version, "SKILL_MD", skill_md), \
         mock.patch.object(bump_skill_version, "README_MD", readme_md), \
         mock.patch.object(bump_skill_version, "SKILL_CARD_MD", skill_card_md):
        bump_skill_version.apply("2.0.6")

    assert "version: 2.0.6" in skill_md.read_text()
    assert "badge/version-2.0.6-blue" in readme_md.read_text()
    assert skill_card_md.read_text().startswith("## Skill Version\n\n2.0.6 (source:")
finally:
    shutil.rmtree(tmp_dir)

print("Version bump regression test passed.")
