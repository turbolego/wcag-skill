#!/usr/bin/env python3
"""Offline regression test for the ClawHub multipart publish request."""
import importlib.util
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "scripts" / "publish-web.py"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("publish_web", SOURCE)
assert spec and spec.loader
publish_web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish_web)

boundary = "----TestBoundary"
request = publish_web.build_upload_request(
    {"slug": "test-skill"},
    [("plain.txt", b"accessible content")],
    "test-token",
    boundary,
)

assert request.get_method() == "POST"
assert request.get_header("Authorization") == "Bearer test-token"
assert request.get_header("Content-type") == f"multipart/form-data; boundary={boundary}"
assert request.data.startswith(f"--{boundary}\r\n".encode())
assert b'{"slug":"test-skill"}' in request.data
assert b'filename="plain.txt"' in request.data
assert b"accessible content" in request.data
assert request.data.endswith(f"--{boundary}--\r\n".encode())

with contextlib.redirect_stdout(io.StringIO()) as output, \
     mock.patch.object(sys, "argv", ["publish-web.py", "--dry-run"]), \
     mock.patch.object(publish_web, "urlopen", side_effect=AssertionError("dry run made a network call")):
    publish_web.main()
payload_text = output.getvalue().split("DRY RUN — payload would be:\n")[1]
payload = json.loads(payload_text.split("=" * 60)[1])
assert payload["version"] == publish_web.check_versions(ROOT)
assert payload["tags"] == ["latest"]
paths = {item["path"] for item in payload["files"]}
assert "SKILL.md" in paths
for name in ("publish-web.py", "bump-skill-version.py", "read-version.py",
             "skill_version.py", "clawhub-force-sync.py"):
    assert f"scripts/{name}" not in paths

with mock.patch.object(sys, "argv", ["publish-web.py", "--dry-run"]), \
     mock.patch.object(publish_web, "check_versions", side_effect=SystemExit("mismatch")), \
     mock.patch.object(publish_web, "urlopen") as upload:
    try:
        publish_web.main()
        raise AssertionError("upload allowed inconsistent versions")
    except SystemExit as error:
        assert str(error) == "mismatch"
    upload.assert_not_called()

print("Publish request regression test passed.")
