import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check-legacy-markup.py"
RULES = json.loads((ROOT / "resources/legacy_tags.json").read_text(encoding="utf-8"))


class LegacyMarkupCheckerTests(unittest.TestCase):
    def run_checker(self, *paths):
        return subprocess.run(
            [sys.executable, str(CHECKER), *(str(path) for path in paths)],
            capture_output=True, text=True, check=False,
        )

    def test_reports_case_insensitive_elements_with_paths_and_lines_as_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text(
                '<!-- <font> comment -->\n'
                '<p title="<center>">&lt;marquee&gt; is text</p>\n'
                '<font>one</font><FONT>two</FONT><font-awesome>custom</font-awesome>\n'
                '<marquee>three</marquee>\n',
                encoding="utf-8",
            )
            result = self.run_checker(page)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"{page}:3: <font>", result.stdout)
        self.assertIn(f"{page}:4: <marquee>", result.stdout)
        self.assertIn("font: 2 occurrence(s)", result.stdout)
        self.assertIn("Total: 3 occurrence(s) across 2 element type(s)", result.stdout)
        self.assertIn("review warnings, not automatic WCAG failures", result.stdout)
        self.assertNotIn("<center>", result.stdout)
        self.assertNotIn("font-awesome", result.stdout)

    def test_ignores_escaped_markup_examples_and_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "examples.html"
            page.write_text(
                '<!-- <font>comment</font> -->'
                '<pre><code>&lt;font&gt;example&lt;/font&gt;</code></pre>'
                '<p><code>&lt;marquee&gt;example&lt;/marquee&gt;</code></p>'
                '<script>const text = "<blink>";</script>'
                '<style>.x::before { content: "<center>"; }</style>',
                encoding="utf-8",
            )
            result = self.run_checker(page)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No obsolete elements found.", result.stdout)
        self.assertIn("Total: 0 occurrence(s) across 0 element type(s)", result.stdout)

    def test_reports_obsolete_elements_inside_preformatted_containers(self):
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "nested.html"
            page.write_text(
                '<pre><font color="red">news</font></pre>\n'
                '<code><center>example</center></code>\n'
                '<kbd><blink>key</blink></kbd>\n'
                '<samp><big>output</big></samp>\n',
                encoding="utf-8",
            )
            result = self.run_checker(page)
        self.assertEqual(result.returncode, 0, result.stderr)
        for line, tag in enumerate(("font", "center", "blink", "big"), 1):
            self.assertIn(f"{page}:{line}: <{tag}>", result.stdout)
        self.assertIn("Total: 4 occurrence(s) across 4 element type(s)", result.stdout)

    def test_recursively_scans_html_files_in_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<font>one</font>", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "page.XHTML").write_text("<center>two</center>", encoding="utf-8")
            (nested / "ignored.txt").write_text("<blink>not HTML input</blink>", encoding="utf-8")
            result = self.run_checker(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("index.html:1: <font>", result.stdout)
        self.assertIn("page.XHTML:1: <center>", result.stdout)
        self.assertNotIn("ignored.txt", result.stdout)
        self.assertIn("Total: 2 occurrence(s) across 2 element type(s)", result.stdout)

    def test_reports_invalid_input_without_success_shaped_fallback(self):
        result = self.run_checker(Path("/path/that/does/not/exist.html"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("Legacy markup check failed:", result.stderr)

    def test_uses_same_tag_inventory_as_benchmark_checker(self):
        self.assertEqual(len(RULES["tags"]), 29)
        benchmark_list = json.loads(
            (ROOT / "benchmark/resources/html_tags.json").read_text(encoding="utf-8")
        )["tags"]
        self.assertFalse(set(RULES["tags"]) & set(benchmark_list))


if __name__ == "__main__":
    unittest.main()
