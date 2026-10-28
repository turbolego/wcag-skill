#!/usr/bin/env python3
"""Offline regression test for the ClawHub multipart publish request."""
import importlib.util
import contextlib
import io
import json
import os
import sys
import tempfile
import textwrap
from pathlib import Path
from urllib.error import HTTPError
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

# Execute the workflow's actual resolver against owner-only pending records.
workflow = (ROOT / ".github/workflows/publish-web.yml").read_text()
resolver = textwrap.dedent(
    workflow.split('python3 - "$TARGET" <<\'PY\'\n', 1)[1].split("\n          PY", 1)[0]
)
for stage in ("pending_checks", "published"):
    with tempfile.TemporaryDirectory() as temporary:
        output_path = Path(temporary) / "output"
        with contextlib.redirect_stdout(io.StringIO()), \
             mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path), "CLAWHUB_TOKEN": "test-token"}), \
             mock.patch.object(sys, "argv", ["-", "1.2.3"]), \
             mock.patch("urllib.request.urlopen", side_effect=[
                 io.BytesIO(json.dumps({"latestVersion": {"version": "1.2.2"}}).encode()),
                 io.BytesIO(json.dumps({"publication": {"version": "1.2.3", "stage": stage}}).encode()),
             ]) as fetch:
            exec(compile(resolver, "publish-web.yml resolver", "exec"), {})
        assert "recorded=1" in output_path.read_text()
        owner_request = fetch.call_args_list[1].args[0]
        assert owner_request.full_url.endswith("/versions/1.2.3/publication?ownerHandle=turbolego")
        assert owner_request.get_header("Authorization") == "Bearer " + "test-token"

for stage in ("pending_checks", "checks_failed", "blocked", "published"):
    with tempfile.TemporaryDirectory() as temporary:
        output_path = Path(temporary) / "output"
        with contextlib.redirect_stdout(io.StringIO()), \
             mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path),
                                         "CLAWHUB_TOKEN": "test-token", "CREATE_RELEASE": "true"}), \
             mock.patch.object(sys, "argv", ["-", "1.2.3"]), \
             mock.patch("urllib.request.urlopen", side_effect=[
                 io.BytesIO(json.dumps({"latestVersion": {"version": "1.2.2"}}).encode()),
                 io.BytesIO(json.dumps({"publication": {"version": "1.2.3", "stage": stage}}).encode()),
             ]):
            try:
                exec(compile(resolver, "publish-web.yml resolver", "exec"), {})
                assert stage == "published", "Bumping past an unpublished release was allowed"
            except SystemExit as error:
                assert stage != "published"
                assert "Refusing to bump past retained release" in str(error)
                assert not output_path.exists()

assert workflow.index("- name: Resolve target") < workflow.index("- name: Create synchronized")
assert 'steps.target.outputs.version != steps.resolve.outputs.target' in workflow

for status in (404, 401):
    with tempfile.TemporaryDirectory() as temporary:
        output_path = Path(temporary) / "output"
        with contextlib.redirect_stdout(io.StringIO()), \
             mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_path), "CLAWHUB_TOKEN": "test-token"}), \
             mock.patch.object(sys, "argv", ["-", "1.2.3"]), \
             mock.patch("urllib.request.urlopen", side_effect=[
                 io.BytesIO(json.dumps({"latestVersion": {"version": "1.2.2"}}).encode()),
                 HTTPError("https://registry.example", status, "test", {}, None),
             ]):
            try:
                exec(compile(resolver, "publish-web.yml resolver", "exec"), {})
                assert status == 404, "Invalid owner credentials were accepted"
                assert "recorded=0" in output_path.read_text()
            except HTTPError as error:
                assert status == 401 and error.code == 401

print("Publish request regression test passed.")
