"""Shared release-version reader, synchronizer, and consistency gate."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILES = ("SKILL.md", "README.md", "skill-card.md", "package.json", "package-lock.json")
SEMVER = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
SKILL_PATTERN = rf"(?m)^(  version: )[\"']?({SEMVER})[\"']?[ \t]*$"
MIRROR_PATTERNS = {
    "README.md": rf"(badge/version-)({SEMVER})(-blue)",
    "skill-card.md": rf"(?m)^()({SEMVER})(?= \(source: `SKILL\.md`)",
}


def parse_version(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(SEMVER, value):
        raise SystemExit(f"Version {value!r} is not in MAJOR.MINOR.PATCH form")
    major, minor, patch = (int(part) for part in value.split("."))
    return major, minor, patch


def frontmatter(content: str) -> re.Match[str]:
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
    if not match:
        raise SystemExit("Could not find YAML frontmatter in SKILL.md")
    return match


def version_match(content: str, pattern: str, name: str) -> re.Match[str]:
    matches = list(re.finditer(pattern, content))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one release version in {name}, found {len(matches)}")
    return matches[0]


def read_frontmatter_version(skill_md: Path) -> str:
    block = frontmatter(skill_md.read_text()).group(1)
    metadata = re.search(r"(?m)^metadata:\s*\n((?:[ \t]+[^\n]*\n?)*)", block)
    if not metadata:
        raise SystemExit("Could not find metadata in SKILL.md frontmatter")
    return version_match(metadata.group(1), SKILL_PATTERN, "SKILL.md metadata.version").group(2)


def synchronized_contents(root: Path, version: str) -> dict[Path, str]:
    parse_version(version)
    changes: dict[Path, str] = {}
    skill = root / "SKILL.md"
    text = skill.read_text()
    read_frontmatter_version(skill)
    block = frontmatter(text)
    metadata = re.search(r"(?m)^metadata:\s*\n((?:[ \t]+[^\n]*\n?)*)", block.group(1))
    assert metadata is not None
    match = version_match(metadata.group(1), SKILL_PATTERN, "SKILL.md metadata.version")
    start = metadata.start(1) + match.start(2)
    end = metadata.start(1) + match.end(2)
    updated = block.group(1)[:start] + version + block.group(1)[end:]
    changes[skill] = text[:block.start(1)] + updated + text[block.end(1):]
    for name, pattern in MIRROR_PATTERNS.items():
        path = root / name
        text = path.read_text()
        match = version_match(text, pattern, name)
        changes[path] = text[:match.start(2)] + version + text[match.end(2):]
    for name in ("package.json", "package-lock.json"):
        path = root / name
        data = json.loads(path.read_text())
        if not isinstance(data.get("version"), str):
            raise SystemExit(f"Missing root version in {name}")
        data["version"] = version
        if name == "package-lock.json":
            package = data.get("packages", {}).get("")
            if not isinstance(package, dict) or not isinstance(package.get("version"), str):
                raise SystemExit("Missing packages[''].version in package-lock.json")
            package["version"] = version
        changes[path] = json.dumps(data, indent=2) + "\n"
    return changes


def sync_versions(root: Path, version: str) -> None:
    # Validate every mirror before writing any file.
    for path, content in synchronized_contents(root, version).items():
        path.write_text(content)


def check_versions(root: Path) -> str:
    version = read_frontmatter_version(root / "SKILL.md")
    mismatches = []
    for path, expected in synchronized_contents(root, version).items():
        actual = path.read_text()
        if path.suffix == ".json":
            matches = json.loads(actual) == json.loads(expected)
        else:
            matches = actual == expected
        if not matches:
            mismatches.append(path.name)
    if mismatches:
        raise SystemExit(
            f"Release version mismatch (expected {version}): {', '.join(mismatches)}. "
            "Run python3 scripts/read-version.py --sync."
        )
    return version
