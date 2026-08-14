#!/usr/bin/env python3
"""Check benchmark tag coverage and tag balance.

Usage:
  python3 benchmark/scripts/check-tag-coverage.py <index.html> [html_tags.json]

Prints expected/used/missing tag counts and reports unbalanced or unclosed tags.
Note: elements with optional end tags (option, li, p, dt, dd, tr, td, th) may
show as "unclosed" in the strict balance pass — the W3C validator accepts them;
treat section/div/main/table mismatches as the real errors.
"""

import json
import re
import sys
from pathlib import Path
from html.parser import HTMLParser

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

TAG_RE = r"<\s*([a-zA-Z][a-zA-Z0-9\-]*)\b"


def check_coverage(html, tags_path):
    with open(tags_path) as f:
        expected = set(json.load(f)["tags"])
    used = set(t.lower() for t in re.findall(TAG_RE, html))
    missing = sorted(expected - used)
    print(f"Expected: {len(expected)}  Used: {len(used)}  Missing: {len(missing)}")
    if missing:
        print("MISSING:", ", ".join(missing))
    return missing


def check_balance(html):
    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []

        def handle_starttag(self, tag, attrs):
            if tag not in VOID:
                self.stack.append(tag)

        def handle_endtag(self, tag):
            if tag in VOID:
                return
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            else:
                print(f"UNMATCHED </{tag}> at {self.getpos()} — stack top: {self.stack[-1] if self.stack else None}")

    p = P()
    p.feed(html)
    if p.stack:
        print("UNCLOSED (may include optional-end-tag elements):", p.stack)
    else:
        print("Balance: OK")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    html_path = sys.argv[1]
    default_tags = Path(__file__).resolve().parent.parent / "resources" / "html_tags.json"
    tags_path = sys.argv[2] if len(sys.argv) > 2 else default_tags
    with open(html_path) as f:
        html = f.read()
    missing = check_coverage(html, tags_path)
    check_balance(html)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
