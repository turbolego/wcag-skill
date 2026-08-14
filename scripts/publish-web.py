#!/usr/bin/env python3
"""Publish wcag-skill to ClawHub via multipart upload API.

This bypasses the CLI ticket-upload path which is blocked by a server-side
clock-domain bug (issue #3397 / PR #3400). The multipart web-upload path
stores files directly and skips the buggy per-file ticket verification.

Required: CLAWHUB_TOKEN environment variable (a clh_... API token).
"""
import argparse, fnmatch, hashlib, json, os, re, sys, uuid
from pathlib import Path
from urllib.request import Request, urlopen

SKILL_DIR = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parent.parent))
SKILL_SLUG = "wcag-skill"


def get_token() -> str:
    """Read ClawHub API token from environment."""
    token = os.environ.get("CLAWHUB_TOKEN")
    if not token:
        print("❌ CLAWHUB_TOKEN not set in environment", file=sys.stderr)
        sys.exit(1)
    return token


def load_ignore_patterns(root: Path) -> list[str]:
    """Read the simple path patterns used by .clawhubignore."""
    ignore_file = root / ".clawhubignore"
    if not ignore_file.exists():
        return []
    return [
        line.strip()
        for line in ignore_file.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def is_ignored(rel: str, patterns: list[str]) -> bool:
    """Match a path against file, directory, and shell-style ignore patterns."""
    for pattern in patterns:
        normalized = pattern.rstrip("/")
        if rel == normalized or rel.startswith(f"{normalized}/"):
            return True
        if fnmatch.fnmatch(rel, pattern):
            return True
    return False


def collect_files(root: Path) -> list[tuple[str, bytes]]:
    """Walk skill directory, apply .clawhubignore, return [(relpath, bytes)]."""
    files: list[tuple[str, bytes]] = []
    ignored_patterns = load_ignore_patterns(root)
    for dirpath, dirnames, filenames in os.walk(str(root)):
        current = Path(dirpath)
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d != "node_modules"
            and not is_ignored(str((current / d).relative_to(root)), ignored_patterns)
        ]
        for fn in sorted(filenames):
            if fn.startswith(".") and fn != ".clawhubignore":
                continue
            abs_path = current / fn
            rel = str(abs_path.relative_to(root))
            if is_ignored(rel, ignored_patterns):
                continue
            data = abs_path.read_bytes()
            files.append((rel, data))
    return files


def read_version(skill_dir: Path) -> str:
    """Extract version from SKILL.md frontmatter."""
    content = (skill_dir / "SKILL.md").read_text()
    for line in content.split("\n"):
        match = re.match(r"^\s*version:\s*['\"]?([^'\"\s]+)", line)
        if match:
            return match.group(1)
    return "unknown"


def build_multipart(
    payload: dict, files: list[tuple[str, bytes]], boundary: str
) -> bytes:
    """Build a multipart/form-data body for the ClawHub API."""
    body = bytearray()

    def add(s: str | bytes) -> None:
        body.extend(s.encode() if isinstance(s, str) else s)

    # Payload field
    add(f"--{boundary}\r\n")
    add('Content-Disposition: form-data; name="payload"\r\n')
    add("Content-Type: application/json\r\n\r\n")
    add(json.dumps(payload, separators=(",", ":")))
    add("\r\n")

    # File fields
    for path, data in files:
        add(f"--{boundary}\r\n")
        add(
            f'Content-Disposition: form-data; name="files"; filename="{path}"\r\n'
        )
        add("Content-Type: application/octet-stream\r\n\r\n")
        add(data)
        add("\r\n")

    add(f"--{boundary}--\r\n")
    return bytes(body)


def build_upload_request(
    payload: dict, files: list[tuple[str, bytes]], token: str, boundary: str
) -> Request:
    """Create the authenticated multipart request without sending it."""
    body = build_multipart(payload, files, boundary)
    req = Request(
        "https://clawhub.ai/api/v1/skills",
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Accept", "application/json")
    return req


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish wcag-skill to ClawHub")
    parser.add_argument("--dry-run", action="store_true", help="Print payload, skip upload")
    args = parser.parse_args()

    token = get_token()
    print(f"✓ Token present ({len(token)} chars)")

    version = read_version(SKILL_DIR)
    print(f"✓ Version: {version}")

    files = collect_files(SKILL_DIR)
    print(f"✓ Files: {len(files)}")
    for path, data in files:
        print(f"    {path}  {len(data):,} bytes")

    total = sum(len(d) for _, d in files)
    print(f"✓ Total: {total:,} bytes ({total / 1024:.1f} KB)")

    # Build payload — files metadata only, actual bytes go as multipart fields
    payload = {
        "slug": SKILL_SLUG,
        "displayName": (
            "WCAG Accessibility — Testing, Fixing, and Building Accessible Pages"
        ),
        "version": version,
        "changelog": "",
        "acceptLicenseTerms": True,
        "tags": ["universal-design", "wcag", "accessibility"],
        "categories": ["development"],
        "topics": ["universal-design", "wcag", "accessibility"],
        "files": [
            {
                "path": rel,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for rel, data in files
        ],
    }

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — payload would be:")
        print("=" * 60)
        print(json.dumps(payload, indent=2))
        print("=" * 60)
        return

    boundary = f"----ClawHubUpload{uuid.uuid4().hex[:12]}"
    req = build_upload_request(payload, files, token, boundary)
    body = req.data

    print(f"✓ Uploading {len(body):,} bytes...")
    try:
        resp = urlopen(req, timeout=120)
        result = json.loads(resp.read())
        print(json.dumps(result, indent=2))
        if result.get("ok"):
            print("\n✅ Published — now pending security scan.")
            print(
                f"   View: https://clawhub.ai/turbolego/skills/{SKILL_SLUG}"
            )
        else:
            print(f"\n❌ Publish rejected: {result}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        if hasattr(e, "read"):
            body_text = e.read().decode(errors="replace")
            print(body_text[:1000], file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
