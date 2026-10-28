#!/usr/bin/env python3
"""Offline regression tests for scan write-back and release verification."""
import contextlib
import importlib.util
import io
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("force_sync", ROOT / "scripts/clawhub-force-sync.py")
assert spec and spec.loader
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

with mock.patch.object(sync, "api_call", side_effect=[
    {"scanId": "scan-1", "status": "queued"},
    {"status": "succeeded", "writtenBack": True},
]) as api:
    sync.force_scan("https://registry.example", "example", "1.2.3", "test-token", 10)
    assert api.call_args_list[0].args[3]["update"] is True
    assert api.call_args_list[0].args[3]["source"]["version"] == "1.2.3"

for result in (
    {"status": "succeeded", "writtenBack": False},
    {"status": "succeeded"},
    {"status": "failed", "lastError": "rejected"},
):
    with mock.patch.object(sync, "api_call", side_effect=[{"scanId": "scan-1"}, result]):
        try:
            sync.force_scan("https://registry.example", "example", "1.2.3", "test-token", 10)
            raise AssertionError(f"Accepted unusable scan: {result}")
        except SystemExit:
            pass

for live, latest in (("1.2.2", "1.2.3"), ("1.2.3", "1.2.2")):
    with mock.patch.object(sync, "api_call", return_value={
        "latestVersion": {"version": live}, "skill": {"tags": {"latest": latest}},
    }):
        try:
            sync.wait_for_live("https://registry.example", "example", "1.2.3", -1)
            raise AssertionError("Live-version or tag mismatch was accepted")
        except SystemExit:
            pass

with mock.patch.object(sync, "api_call", return_value={
    "latestVersion": {"version": "1.2.3"}, "skill": {"tags": {"latest": "1.2.3"}},
}):
    sync.wait_for_live("https://registry.example", "example", "1.2.3", 10)

with contextlib.redirect_stdout(io.StringIO()), \
     mock.patch.object(sys, "argv", ["clawhub-force-sync.py", "--version", "1.2.3"]), \
     mock.patch.object(sync, "get_token", return_value="test-token"), \
     mock.patch.object(sync, "live_version", return_value="1.2.3"), \
     mock.patch.object(sync, "force_scan") as scan, \
     mock.patch.object(sync, "set_tag") as tag, \
     mock.patch.object(sync, "wait_for_live"):
    sync.main()
    scan.assert_not_called()
    tag.assert_called_once()

with contextlib.redirect_stdout(io.StringIO()), \
     mock.patch.object(sys, "argv", ["clawhub-force-sync.py", "--dry-run"]), \
     mock.patch.object(sync, "urlopen", side_effect=AssertionError("dry run made a network call")):
    sync.main()

with mock.patch.object(sync, "urlopen", return_value=io.BytesIO(b"not json")):
    try:
        sync.api_call("https://registry.example", "GET", "/api/v1/test", None, "")
        raise AssertionError("Invalid JSON response was accepted")
    except SystemExit as error:
        assert "invalid JSON" in str(error)

with mock.patch.object(sync, "api_call", return_value={}) as api:
    sync.set_tag("https://registry.example", "example", "1.2.3", "test-token", "latest")
    assert api.call_args.args[1:4] == ("POST", "/api/v1/skills/example/tags/latest", {"version": "1.2.3"})

print("ClawHub sync regression tests passed.")
