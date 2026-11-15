import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "benchmark/scripts/check-tag-coverage.py"
BENCHMARK_RESOURCES = ROOT / "benchmark/resources"
RESOURCES = ROOT / "resources"


class LegacyTagCheckerTests(unittest.TestCase):
    def run_checker(self, html, *options):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text(html, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), *options, str(path)],
                capture_output=True, text=True, check=False,
            )

    def test_benchmark_mode_enforces_coverage_and_rejects_obsolete_tags(self):
        template = (ROOT / "benchmark/templates/index.html").read_text(encoding="utf-8")
        passing = self.run_checker(template)
        self.assertEqual(passing.returncode, 0, passing.stdout + passing.stderr)
        self.assertIn("Missing: 0", passing.stdout)
        failing = self.run_checker(template.replace("</body>", "<font>old</font></body>"))
        self.assertEqual(failing.returncode, 1, failing.stdout + failing.stderr)
        self.assertIn("Deprecated tags present: font", failing.stdout)
        self.assertIn("Missing: 0", failing.stdout)

    def test_worked_example_removes_obsolete_tags_without_losing_text_or_target(self):
        reference = (ROOT / "references/legacy-markup-repair.md").read_text(encoding="utf-8")
        before = reference.split("```html\n", 1)[1].split("\n```", 1)[0]
        after = reference.split("```html\n", 2)[2].split("\n```", 1)[0]
        self.assertIn("<font", before)
        self.assertNotIn("<font", after)
        for value in ("Fjordnytt", "Ny bru åpner lørdag", "Brua er ferdig.",
                      'href="#nyheter"', 'id="nyheter"', 'action="/search"',
                      'name="q"', 'type="submit"'):
            self.assertIn(value, before)
            self.assertIn(value, after)

    def test_required_and_obsolete_lists_remain_disjoint(self):
        tags = json.loads((BENCHMARK_RESOURCES / "html_tags.json").read_text())["tags"]
        legacy = json.loads((RESOURCES / "legacy_tags.json").read_text())["tags"]
        self.assertEqual(len(tags), 113)
        self.assertIn("selectedcontent", tags)
        self.assertIn("param", legacy)
        self.assertFalse(set(tags) & set(legacy))


if __name__ == "__main__":
    unittest.main()
