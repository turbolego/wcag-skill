#!/usr/bin/env python3
"""Check HTML5 tag coverage (against html_tags.json) and tag balance for WCAG pages.

Usage:
  python3 check-tag-coverage.py <index.html> [html_tags.json]

Prints expected/used/missing tag counts and reports unbalanced or unclosed tags.
Implements HTML5 optional-end-tag implied-closing rules (option, li, dt/dd,
tr/td/th, thead/tbody/tfoot, colgroup, p) so legally omitted end tags do not
cascade into false UNMATCHED/UNCLOSED reports for structural elements.
Exits nonzero if any tag is missing or a genuine structural mismatch exists.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Elements whose end tag may be legally omitted (HTML5 §13.1.2).
OPTIONAL_END_TAGS = {
    "option", "optgroup", "li", "dt", "dd", "tr", "td", "th",
    "thead", "tbody", "tfoot", "colgroup", "p",
}

_P_CLOSERS = {
    "address", "article", "aside", "blockquote", "details", "div", "dl",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3",
    "h4", "h5", "h6", "header", "hr", "main", "menu", "nav", "ol", "p",
    "pre", "section", "table", "ul",
}

# Tags that, when opened, implicitly close a given tag left open at the top
# of the stack (the HTML5 parser's implied end-tag behaviour). Note this
# includes void elements: e.g. an open <p> is implicitly closed by a following
# <hr>, <address>, <div>, etc.
AUTO_CLOSE_ON_OPEN = {
    "li": {"li"},
    "option": {"option"},
    "optgroup": {"option", "optgroup"},
    "dt": {"dt", "dd"},
    "dd": {"dt", "dd"},
    "tr": {"tr", "td", "th"},
    "td": {"td", "th"},
    "th": {"td", "th"},
    "thead": {"thead", "tbody", "tfoot"},
    "tbody": {"thead", "tbody", "tfoot"},
    "tfoot": {"thead", "tbody", "tfoot"},
    "colgroup": {"colgroup"},
}
for _closer in _P_CLOSERS:
    AUTO_CLOSE_ON_OPEN.setdefault(_closer, set()).add("p")

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
            self.implied_closes = []
            self.mismatches = []
            self.stray_end_tags = []

        def handle_starttag(self, tag, attrs):
            # Apply implied-close rules BEFORE the void check, so a void
            # element that closes an open optional-end-tag element (e.g. <hr>
            # closing an open <p>) is still recorded.
            closers = AUTO_CLOSE_ON_OPEN.get(tag)
            if closers:
                while self.stack and self.stack[-1] in closers:
                    self.implied_closes.append((self.stack.pop(), tag, self.getpos()))
            if tag in VOID:
                return
            self.stack.append(tag)

        def handle_endtag(self, tag):
            if tag in VOID:
                return
            if tag not in self.stack:
                # No matching open tag. A missing optional-end-tag element was
                # already implicitly closed in HTML5 parsing, so it is only
                # informational; any other stray end tag is a real error.
                note = "optional-end-tag element" if tag in OPTIONAL_END_TAGS else "no matching open tag"
                self.stray_end_tags.append((tag, self.getpos(), note))
                return
            idx = len(self.stack) - 1 - self.stack[::-1].index(tag)
            while len(self.stack) - 1 > idx:
                popped = self.stack.pop()
                if popped not in OPTIONAL_END_TAGS:
                    self.mismatches.append(
                        f"UNMATCHED </{tag}> at {self.getpos()} force-closed unclosed <{popped}>"
                    )
            self.stack.pop()

    p = P()
    p.feed(html)

    if p.implied_closes:
        print(f"INFO: {len(p.implied_closes)} optional end tag(s) legally omitted (implied close)")
    for tag, pos, note in p.stray_end_tags:
        # Non-optional stray end tags are errors; optional-end-tag strays that
        # were implicitly closed are informational.
        severity = "INFO" if tag in OPTIONAL_END_TAGS else "ERROR"
        print(f"{severity}: stray </{tag}> at {pos} ({note})")

    has_error = bool(p.mismatches) or any(
        tag not in OPTIONAL_END_TAGS for tag, _, _ in p.stray_end_tags
    )
    for m in p.mismatches:
        print(m)

    structural_unclosed = [t for t in p.stack if t not in OPTIONAL_END_TAGS]
    optional_unclosed = [t for t in p.stack if t in OPTIONAL_END_TAGS]
    if structural_unclosed:
        print("UNCLOSED (structural mismatch):", structural_unclosed)
        has_error = True
    if optional_unclosed:
        print("UNCLOSED (optional end tag, not an error):", optional_unclosed)
    if not has_error:
        print("Balance: OK")
    return has_error


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    html_path = sys.argv[1]
    default_tags = Path(__file__).resolve().parent.parent / "resources" / "html_tags.json"
    tags_path = sys.argv[2] if len(sys.argv) > 2 else str(default_tags)
    with open(html_path) as f:
        html = f.read()
    missing = check_coverage(html, tags_path)
    balance_error = check_balance(html)
    sys.exit(1 if (missing or balance_error) else 0)


if __name__ == "__main__":
    main()