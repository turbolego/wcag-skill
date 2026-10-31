#!/usr/bin/env python3
"""Wait for publication checks, then synchronize ClawHub's latest pointers.

Pending versions are hidden from public version reads. The authenticated
publication endpoint distinguishes pending uploads from missing ones and
reports failed or blocked pre-publication checks. An on-demand rescan is NOT
a substitute for those checks; use --rescan only for an already published
version. No client can force a pending artifact past ClawHub's release gate.

Requires the owner's CLAWHUB_TOKEN, read from the environment and never printed.

Usage:
  python3 scripts/clawhub-force-sync.py
  python3 scripts/clawhub-force-sync.py --dry-run
"""
import argparse
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from skill_version import ROOT, check_versions, parse_version

DEFAULT_REGISTRY = "https://clawhub.ai"
DEFAULT_SLUG = "wcag-skill"
TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}
GET_ATTEMPTS = 4


def get_token() -> str:
    token = os.environ.get("CLAWHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "CLAWHUB_TOKEN not set. Pass the ClawHub owner token "
            "(the same secret the upload step uses) via the environment."
        )
    return token


def api_call(base: str, method: str, path: str, body: dict | None, token: str):
    """Authenticated JSON call. Returns parsed JSON; raises SystemExit on error.

    Idempotent GET requests are retried on transient server and network errors.
    """
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
    attempts = GET_ATTEMPTS if method == "GET" else 1
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read()
            break
        except HTTPError as e:
            detail = e.read().decode(errors="replace") if e.fp else ""
            error = f"API {method} {path} -> HTTP {e.code}: {detail[:500]}"
            if e.code not in TRANSIENT_HTTP_CODES or attempt == attempts:
                raise SystemExit(error)
        except (URLError, TimeoutError) as e:
            error = f"API {method} {path} -> network error: {e}"
            if attempt == attempts:
                raise SystemExit(error)
        print(f"[force-sync] {error}; retrying ({attempt}/{attempts - 1})", flush=True)
        time.sleep(5 * attempt)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"API {method} {path} -> invalid JSON response") from e


def wait_for_publication(base: str, slug: str, version: str, token: str,
                        timeout: int, owner: str) -> None:
    path = (
        f"/api/v1/skills/{quote(slug, safe='')}/versions/{quote(version, safe='')}"
        f"/publication?{urlencode({'ownerHandle': owner})}"
    )
    deadline = time.monotonic() + timeout
    while True:
        publication = api_call(base, "GET", path, None, token)["publication"]
        if publication.get("version") != version:
            raise SystemExit(f"Publication API returned the wrong version: {publication}")
        stage = publication.get("stage")
        print(f"[force-sync] publication={stage} retrying={publication.get('retrying')} "
              f"checks={publication.get('checks')}", flush=True)
        if stage == "published":
            return
        if stage in {"failed", "blocked", "expired", "unavailable"} or (
            stage in {"checks_failed", "checks_incomplete"} and not publication.get("retrying")
        ):
            raise SystemExit(
                f"ClawHub cannot publish {slug} {version}: {publication}. "
                "The upload is retained; contact ClawHub support with this exact version. "
                "Do not bump again or try to bypass publication checks."
            )
        if stage not in {
            "pending_checks", "checks_failed", "checks_incomplete", "ready_to_finalize", "finalizing",
        }:
            raise SystemExit(f"Unknown ClawHub publication stage: {stage!r}")
        if time.monotonic() >= deadline:
            raise SystemExit(
                f"ClawHub publication for {slug} {version} is still {stage!r} after {timeout}s: "
                f"{publication.get('checks')}. The accepted upload needs ClawHub's workers; "
                "retry this version without bumping, or contact ClawHub support."
            )
        time.sleep(10)


def force_scan(base: str, slug: str, version: str, token: str, poll_timeout: int) -> None:
    """Re-run and write back an already published version's security scan."""
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
    parser.add_argument("--owner", default="turbolego", help="ClawHub publisher handle")
    parser.add_argument("--tag", default="latest", help="Which tag to point at the version")
    parser.add_argument("--scan-timeout", type=int, default=600, help="Max seconds for publication checks or rescan")
    parser.add_argument("--rescan", action="store_true", help="Also rescan an already published version")
    parser.add_argument("--live-timeout", type=int, default=120, help="Max seconds to wait for the live tag to flip")
    parser.add_argument("--dry-run", action="store_true", help="Print the calls, do not execute")
    args = parser.parse_args()

    args.version = args.version or check_versions(ROOT)
    parse_version(args.version)
    token = get_token() if not args.dry_run else ""

    print(f"{'[dry-run]' if args.dry_run else '[force-sync]'} Target: {args.slug} @ {args.version}")
    print(f"  1) GET /api/v1/skills/{args.slug}/versions/{args.version}/publication (wait until published)")
    if args.rescan:
        print("  2) POST /api/v1/skills/-/scan with update:true, then poll for write-back")
    print(f"  3) POST /api/v1/skills/{args.slug}/tags/{args.tag}  {{\"version\":\"{args.version}\"}}")
    print(f"  4) GET /api/v1/skills/{args.slug} (verify live version and tag)")

    if args.dry_run:
        print("[dry-run] No calls executed.")
        return

    wait_for_publication(args.registry, args.slug, args.version, token, args.scan_timeout, args.owner)
    if args.rescan:
        force_scan(args.registry, args.slug, args.version, token, args.scan_timeout)
    set_tag(args.registry, args.slug, args.version, token, args.tag)
    wait_for_live(args.registry, args.slug, args.version, args.live_timeout, args.tag)


if __name__ == "__main__":
    main()
