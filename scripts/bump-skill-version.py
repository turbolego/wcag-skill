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

If the registry can't be queried (network error, non-404 HTTP error, or a
malformed response), this script fails loudly rather than silently falling
back to the local version alone: doing otherwise would let a stale version
be bumped and collide with one that already exists during a transient
ClawHub outage — the exact failure this script exists to prevent. A
confirmed 404 (the skill has genuinely never been published) is the only
case treated as "no versions yet".

Keeps every release-version mirror in sync, including the npm manifests.

Usage:
  scripts/bump-skill-version.py            # print the next version only
  scripts/bump-skill-version.py --write    # also update files on disk
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from skill_version import check_versions, parse_version, read_frontmatter_version, sync_versions

ROOT = Path(__file__).resolve().parent.parent
SKILL_SLUG = "wcag-skill"

Version = tuple[int, int, int]


def read_local_version() -> str:
    return read_frontmatter_version(ROOT / "SKILL.md")


def read_live_versions() -> list[str]:
    """Return every version ClawHub already has for this skill.

    Returns an empty list only when the registry gives a confirmed 404 (the
    skill has never been published). Any other failure — network errors,
    timeouts, non-404 HTTP errors, or a malformed response — is fatal: silently
    treating those as "no versions" would let a stale local version get
    bumped and collide with a version that already exists, which is exactly
    the failure this script exists to prevent.
    """
    url = f"https://clawhub.ai/api/v1/skills/{SKILL_SLUG}/versions"
    versions: list[str] = []
    cursors: set[str] = set()
    try:
        while True:
            with urlopen(url, timeout=60) as resp:
                data = json.load(resp)
            versions.extend(item["version"] for item in data["items"])
            cursor = data.get("nextCursor")
            if cursor is None:
                return versions
            if not isinstance(cursor, str) or not cursor or cursor in cursors:
                raise ValueError("Invalid or repeated registry pagination cursor")
            cursors.add(cursor)
            url = f"https://clawhub.ai/api/v1/skills/{SKILL_SLUG}/versions?{urlencode({'cursor': cursor})}"
    except HTTPError as exc:
        if exc.code == 404:
            if not versions:
                return []
            raise SystemExit("ClawHub pagination returned HTTP 404; refusing incomplete version history") from exc
        raise SystemExit(
            f"ClawHub registry query failed with HTTP {exc.code}; refusing to "
            "guess the published version list. Retry once the registry is "
            "reachable."
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise SystemExit(
            f"Could not reach ClawHub registry ({exc}); refusing to guess the "
            "published version list. Retry once the registry is reachable."
        ) from exc
    except ValueError as exc:
        raise SystemExit(
            f"ClawHub registry returned an unparseable response ({exc}); "
            "refusing to guess the published version list."
        ) from exc

    except (AttributeError, KeyError, TypeError) as exc:
        raise SystemExit(
            f"ClawHub registry response was missing expected fields ({exc}); "
            "refusing to guess the published version list."
        ) from exc


def format_version(version: Version) -> str:
    return ".".join(str(part) for part in version)


def next_version() -> str:
    candidates = [parse_version(read_local_version())]
    candidates += [parse_version(v) for v in read_live_versions()]
    major, minor, patch = max(candidates)
    return format_version((major, minor, patch + 1))


def apply(version: str) -> None:
    sync_versions(ROOT, version)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Write the bumped version to disk"
    )
    args = parser.parse_args()

    check_versions(ROOT)
    version = next_version()
    if args.write:
        apply(version)
    print(version)


if __name__ == "__main__":
    main()
