#!/usr/bin/env python3
"""Offline regression test for the ClawHub multipart publish request."""
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "scripts" / "publish-web.py"

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

print("Publish request regression test passed.")
