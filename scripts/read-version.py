#!/usr/bin/env python3
"""Read, check, or synchronize release versions from SKILL.md metadata."""
import argparse

from skill_version import ROOT, check_versions, read_frontmatter_version, sync_versions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Fail if any release version differs")
    mode.add_argument("--sync", action="store_true", help="Copy SKILL.md's version to all mirrors")
    args = parser.parse_args()
    version = read_frontmatter_version(ROOT / "SKILL.md")
    if args.sync:
        sync_versions(ROOT, version)
    if args.check or args.sync:
        check_versions(ROOT)
    print(version)


if __name__ == "__main__":
    main()
