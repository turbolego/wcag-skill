#!/usr/bin/env python3
"""Check benchmark tag coverage and tag balance.

Usage:
  python3 benchmark/scripts/check-tag-coverage.py <index.html> [html_tags.json]

Prints expected/used/missing tag counts and reports tag balance. The balance
check implements the HTML5 "optional end tag" implied-closing rules (for
option, li, dt/dd, tr/td/th, thead/tbody/tfoot, colgroup, and p) so that a
legally omitted end tag does not cascade into false UNMATCHED/UNCLOSED
reports for enclosing structural elements such as div/section/main/table.
Exits nonzero if any tag is missing or a genuine structural mismatch exists.
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
# of the stack (the HTML5 parser's implied end-tag behaviour).
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
# Any flow-content element (including another <p>) implicitly closes an
# open <p> left on top of the stack.
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
            closers = AUTO_CLOSE_ON_OPEN.get(tag)
            if closers:
                while self.stack and self.stack[-1] in closers:
                    self.implied_closes.append((self.stack.pop(), tag, self.getpos()))
            if tag not in VOID:
                self.stack.append(tag)

        def handle_endtag(self, tag):
            if tag in VOID:
                return
            if tag not in self.stack:
                # Already closed implicitly, or a stray/mismatched tag.
                self.stray_end_tags.append((tag, self.getpos()))
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

    structural_unclosed = [t for t in p.stack if t not in OPTIONAL_END_TAGS]
    optional_unclosed = [t for t in p.stack if t in OPTIONAL_END_TAGS]

    if p.implied_closes:
        print(f"INFO: {len(p.implied_closes)} optional end tag(s) legally omitted (implied close)")
    if p.stray_end_tags:
        for tag, pos in p.stray_end_tags:
            note = "optional-end-tag element" if tag in OPTIONAL_END_TAGS else "no matching open tag"
            print(f"INFO: stray </{tag}> at {pos} ({note})")

    has_error = bool(p.mismatches or structural_unclosed)
    for m in p.mismatches:
        print(m)
    if optional_unclosed:
        print("UNCLOSED (optional end tag, not an error):", optional_unclosed)
    if structural_unclosed:
        print("UNCLOSED (structural mismatch):", structural_unclosed)
    if not has_error:
        print("Balance: OK")
    return has_error


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
    balance_error = check_balance(html)
    sys.exit(1 if (missing or balance_error) else 0)


if __name__ == "__main__":
    main()

