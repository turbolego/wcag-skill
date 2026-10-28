#!/usr/bin/env python3
"""Force ClawHub's live version to match a target version.

publish-web.yml's previous design *waited* up to 30 minutes for ClawHub's
security-scan queue to naturally promote the just-published version, and
failed if it didn't. That passively left the repo running ahead of a stuck
ClawHub release. This script actively requests a scan and sync instead:

  1. Re-run the LLM security scan for the published version and write the
     result back to the version (POST /skills/-/scan with update:true), so a
     version stuck in "pending" actually gets recorded.
  2. Point the skill's `latest` tag at the target version
     (POST /skills/{slug}/tags/latest).
  3. Poll GET /skills/{slug} until `latestVersion.version` equals the target.

Every endpoint is owner-gated, so this needs the ClawHub token (the same
`CLAWHUB_TOKEN` the upload step uses). It is read from the environment and is
never printed.

Usage:
  python3 scripts/clawhub-force-sync.py
  python3 scripts/clawhub-force-sync.py --dry-run
"""
import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from skill_version import ROOT, check_versions, parse_version

DEFAULT_REGISTRY = "https://clawhub.ai"
DEFAULT_SLUG = "wcag-skill"


def get_token() -> str:
    token = os.environ.get("CLAWHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "CLAWHUB_TOKEN not set. Pass the ClawHub owner token "
            "(the same secret the upload step uses) via the environment."
        )
    return token


def api_call(base: str, method: str, path: str, body: dict | None, token: str):
    """Authenticated JSON call. Returns parsed JSON; raises SystemExit on error."""
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except HTTPError as e:
        detail = e.read().decode(errors="replace") if e.fp else ""
        raise SystemExit(f"API {method} {path} -> HTTP {e.code}: {detail[:500]}")
    except (URLError, TimeoutError) as e:
        raise SystemExit(f"API {method} {path} -> network error: {e}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"API {method} {path} -> invalid JSON response") from e


def live_version(base: str, slug: str) -> str:
    data = api_call(base, "GET", f"/api/v1/skills/{slug}", None, "")
    # This endpoint is public (no auth needed); the empty token is fine.
    return str(data.get("latestVersion", {}).get("version", "") or "")


def force_scan(base: str, slug: str, version: str, token: str, poll_timeout: int) -> None:
    """Re-run + write back the security scan so a pending version gets recorded."""
    print(f"[force-sync] Submitting scan-update for {slug} {version} ...")
    sub = api_call(
        base,
        "POST",
        "/api/v1/skills/-/scan",
        {"source": {"kind": "published", "slug": slug, "version": version}, "update": True},
        token,
    )
    scan_id = sub.get("scanId")
    if not scan_id:
        raise SystemExit(f"Scan submit returned no scanId: {json.dumps(sub)[:400]}")
    print(f"[force-sync] scanId={scan_id} initial status={sub.get('status')}")

    deadline = time.time() + poll_timeout
    while True:
        st = api_call(base, "GET", f"/api/v1/skills/-/scan/{scan_id}", None, token)
        status = st.get("status")
        queue = st.get("queue") or {}
        note = f" (queued ahead: {queue.get('queuedAhead')})" if queue.get("queuedAhead") is not None else ""
        print(f"[force-sync] scan {status}{note} writtenBack={st.get('writtenBack')}")
        if status == "succeeded":
            if st.get("writtenBack") is not True:
                raise SystemExit("Scan completed but was not written back; refusing to promote the version.")
            print("[force-sync] security scan completed and was written back to the version")
            return
        if status == "failed":
            raise SystemExit(
                f"Security scan FAILED for {slug} {version}: {st.get('lastError')!r}. "
                "Fix the flagged issue and re-publish."
            )
        if time.time() > deadline:
            raise SystemExit(
                f"Scan for {slug} {version} still {status!r} after {poll_timeout}s. "
                "Re-run; if the queue is stuck, check the scan report via `clawhub scan`."
            )
        time.sleep(5)


def set_tag(base: str, slug: str, version: str, token: str, tag: str) -> None:
    print(f"[force-sync] Pointing `{tag}` tag at {version} ...")
    api_call(
        base,
        "POST",
        f"/api/v1/skills/{slug}/tags/{tag}",
        {"version": version},
        token,
    )


def wait_for_live(base: str, slug: str, version: str, timeout: int, tag: str = "latest") -> None:
    print(f"[force-sync] Waiting for ClawHub live version to become {version} ...")
    deadline = time.time() + timeout
    while True:
        data = api_call(base, "GET", f"/api/v1/skills/{slug}", None, "")
        current = str((data.get("latestVersion") or {}).get("version") or "")
        tagged = (data.get("skill") or {}).get("tags", {}).get(tag)
        if current == version and tagged == version:
            print(f"[force-sync] ✅ ClawHub live version is now {version}")
            return
        if time.time() > deadline:
            raise SystemExit(
                f"ClawHub live={current!r}, {tag} tag={tagged!r} after {timeout}s, expected {version!r}. "
                "The scan may still be propagating; re-run this step."
            )
        print(f"[force-sync] live={current!r}, {tag} tag={tagged!r}, polling...")
        time.sleep(10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Force ClawHub's live version to match a target.")
    parser.add_argument("--slug", default=DEFAULT_SLUG)
    parser.add_argument("--version", help="Target version to make live (default: checked repository version)")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--tag", default="latest", help="Which tag to point at the version")
    parser.add_argument("--scan-timeout", type=int, default=600, help="Max seconds to wait for the security scan")
    parser.add_argument("--live-timeout", type=int, default=120, help="Max seconds to wait for the live tag to flip")
    parser.add_argument("--dry-run", action="store_true", help="Print the calls, do not execute")
    args = parser.parse_args()

    args.version = args.version or check_versions(ROOT)
    parse_version(args.version)
    token = get_token() if not args.dry_run else ""

    print(f"{'[dry-run]' if args.dry_run else '[force-sync]'} Target: {args.slug} @ {args.version}")
    print(
        f"  1) POST /api/v1/skills/-/scan  "
        f'{{"source":{{"kind":"published","slug":"{args.slug}","version":"{args.version}"}},'
        f'"update":true}}'
    )
    print(f"  2) GET  /api/v1/skills/-/scan/{{scanId}}  (poll until succeeded)")
    print(f"  3) POST /api/v1/skills/{args.slug}/tags/{args.tag}  {{\"version\":\"{args.version}\"}}")
    print(f"  4) GET  /api/v1/skills/{args.slug}  (wait until latestVersion == {args.version})")

    if args.dry_run:
        print("[dry-run] No calls executed.")
        return

    current = live_version(args.registry, args.slug)
    if current != args.version:
        force_scan(args.registry, args.slug, args.version, token, args.scan_timeout)
    set_tag(args.registry, args.slug, args.version, token, args.tag)
    wait_for_live(args.registry, args.slug, args.version, args.live_timeout, args.tag)


if __name__ == "__main__":
    main()
