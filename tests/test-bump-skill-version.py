#!/usr/bin/env python3
"""Offline regression test for the auto version-bump logic.

Exercises next_version()/apply() against temporary copies of SKILL.md,
README.md, and skill-card.md so it never hits the network or mutates the
real repository files.
"""
import importlib.util
import shutil
import tempfile
import sys
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "scripts" / "bump-skill-version.py"
sys.path.insert(0, str(ROOT / "scripts"))
import skill_version

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

# Registry confirms the skill was never published (404): treat as no
# versions yet, so a first-ever publish still works.
with mock.patch.object(bump_skill_version, "read_local_version", return_value="1.0.0"), \
     mock.patch.object(bump_skill_version, "read_live_versions", return_value=[]):
    assert bump_skill_version.next_version() == "1.0.1"

# --- read_live_versions() error handling -----------------------------------
import io
import json as json_module
from urllib.error import HTTPError, URLError


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen_ok(_url, timeout=None):
    payload = json_module.dumps({"items": [{"version": "2.0.4"}]}).encode()
    return _FakeResponse(payload)


def _fake_urlopen_404(_url, timeout=None):
    raise HTTPError(_url, 404, "Not Found", {}, None)


def _fake_urlopen_500(_url, timeout=None):
    raise HTTPError(_url, 500, "Server Error", {}, None)


def _fake_urlopen_unreachable(_url, timeout=None):
    raise URLError("connection refused")


def _fake_urlopen_malformed(_url, timeout=None):
    return _FakeResponse(b"not json")


def _fake_urlopen_missing_field(_url, timeout=None):
    return _FakeResponse(json_module.dumps({"nope": []}).encode())


with mock.patch.object(bump_skill_version, "urlopen", _fake_urlopen_ok):
    assert bump_skill_version.read_live_versions() == ["2.0.4"]

# A confirmed 404 (skill never published) is the only failure treated as "no
# versions yet".
with mock.patch.object(bump_skill_version, "urlopen", _fake_urlopen_404):
    assert bump_skill_version.read_live_versions() == []

# Every other failure mode must fail loudly instead of silently returning [],
# since that would let a stale local version collide with an existing one.
for fake in (
    _fake_urlopen_500,
    _fake_urlopen_unreachable,
    _fake_urlopen_malformed,
    _fake_urlopen_missing_field,
):
    with mock.patch.object(bump_skill_version, "urlopen", fake):
        try:
            bump_skill_version.read_live_versions()
            raise AssertionError(f"expected {fake.__name__} to raise SystemExit")
        except SystemExit:
            pass

# --- apply() rewrites every release mirror, not dependency versions --------
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
    (tmp_dir / "package.json").write_text(json_module.dumps({
        "version": "2.0.5", "devDependencies": {"example": "1.2.3"},
    }))
    (tmp_dir / "package-lock.json").write_text(json_module.dumps({
        "version": "2.0.5",
        "packages": {"": {"version": "2.0.5"}, "node_modules/example": {"version": "1.2.3"}},
    }))

    with mock.patch.object(bump_skill_version, "ROOT", tmp_dir):
        bump_skill_version.apply("2.0.6")

    assert "version: 2.0.6" in skill_md.read_text()
    assert "badge/version-2.0.6-blue" in readme_md.read_text()
    assert skill_card_md.read_text().startswith("## Skill Version\n\n2.0.6 (source:")
    assert skill_version.check_versions(tmp_dir) == "2.0.6"
    package = json_module.loads((tmp_dir / "package.json").read_text())
    lock = json_module.loads((tmp_dir / "package-lock.json").read_text())
    assert package["version"] == lock["version"] == lock["packages"][""]["version"] == "2.0.6"
    assert package["devDependencies"]["example"] == "1.2.3"
    assert lock["packages"]["node_modules/example"]["version"] == "1.2.3"

    baseline = {name: (tmp_dir / name).read_text() for name in skill_version.VERSION_FILES}
    for name in skill_version.VERSION_FILES:
        path = tmp_dir / name
        path.write_text(baseline[name].replace("2.0.6", "2.0.7"))
        try:
            skill_version.check_versions(tmp_dir)
            raise AssertionError(f"Missed drift in {name}")
        except SystemExit as error:
            assert "mismatch" in str(error)
        path.write_text(baseline[name])

    # A missing mirror must fail before any other file is written.
    readme_md.write_text("No badge\n")
    before = skill_md.read_text()
    try:
        skill_version.sync_versions(tmp_dir, "2.0.8")
        raise AssertionError("Missing version badge was accepted")
    except SystemExit:
        pass
    assert skill_md.read_text() == before

    # metadata.version, not another YAML key or a body example, is canonical.
    skill_md.write_text("---\nversion: 9.9.9\nmetadata:\n  version: '2.0.6'\n---\nversion: 8.8.8\n")
    assert skill_version.read_frontmatter_version(skill_md) == "2.0.6"
    readme_md.write_text(baseline["README.md"])
    assert skill_version.check_versions(tmp_dir) == "2.0.6"
    skill_version.sync_versions(tmp_dir, "2.0.8")
    assert "  version: '2.0.8'" in skill_md.read_text()
    assert "version: 9.9.9" in skill_md.read_text()
    assert "version: 8.8.8" in skill_md.read_text()
finally:
    shutil.rmtree(tmp_dir)

# Registry pages may contain a higher version after the first page.
pages = [
    {"items": [{"version": "2.0.4"}], "nextCursor": "next page"},
    {"items": [{"version": "2.1.0"}], "nextCursor": None},
]
with mock.patch.object(bump_skill_version, "urlopen",
                       side_effect=[_FakeResponse(json_module.dumps(page).encode()) for page in pages]) as fetch:
    assert bump_skill_version.read_live_versions() == ["2.0.4", "2.1.0"]
    assert "cursor=next+page" in fetch.call_args_list[1].args[0]

with mock.patch.object(bump_skill_version, "urlopen", side_effect=[
    _FakeResponse(json_module.dumps(pages[0]).encode()),
    _FakeResponse(json_module.dumps(pages[0]).encode()),
]):
    try:
        bump_skill_version.read_live_versions()
        raise AssertionError("Repeated cursor was accepted")
    except SystemExit:
        pass

print("Version bump regression test passed.")
