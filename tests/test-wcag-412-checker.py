import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/wcag-412-stateful-page.html"
CHECKER = ROOT / "scripts/check-wcag-412.py"
DEMO_PAGE = ROOT / "docs/index.html"


class Wcag412CheckerTests(unittest.TestCase):
    def test_inventories_stateful_and_static_controls_without_claiming_conformance(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(FIXTURE), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        components = report["components"]
        theme_toggle = next(component for component in components if component["id"] == "theme-toggle")

        self.assertEqual(report["criterion"], "4.1.2")
        self.assertIn("cannot calculate", report["limitation"])
        self.assertEqual(theme_toggle["status"], "4.1.2-dynamic-required")
        self.assertIn("aria-pressed", theme_toggle["reasons"])
        self.assertEqual(theme_toggle["interaction_test"], "DYNAMIC TEST REQUIRED")
        self.assertEqual(
            theme_toggle["accessible_name_and_semantics"],
            "verify in rendered accessibility tree",
        )
        self.assertTrue(any(component["status"] == "4.1.2-static" for component in components))
        broken_theme = next(
            component for component in components if component["id"] == "theme-toggle-broken"
        )
        self.assertEqual(broken_theme["status"], "4.1.2-dynamic-required")
        self.assertIn("application-declared dynamic state", broken_theme["reasons"])
        summary = next(component for component in components if component["tag"] == "summary")
        self.assertEqual(summary["status"], "4.1.2-dynamic-required")
        custom_control = next(component for component in components if component["id"] == "custom-control")
        self.assertEqual(custom_control["status"], "4.1.2-dynamic-required")
        live_region = next(component for component in components if component["id"] == "status")
        self.assertIn("4.1.2-manual-AT-review", live_region["review_statuses"])

    def test_native_controls_are_reported_and_hidden_inputs_are_excluded(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(FIXTURE), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        components = json.loads(result.stdout)["components"]
        tags = [component["tag"] for component in components]

        self.assertIn("input", tags)
        self.assertIn("details", tags)
        self.assertNotIn("input:hidden", tags)
        self.assertEqual(sum(component["tag"] == "input" for component in components), 1)

    def test_pages_demo_marks_both_theme_toggle_states_for_review(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), str(DEMO_PAGE), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        components = {
            component["id"]: component
            for component in json.loads(result.stdout)["components"]
        }

        self.assertEqual(
            components["theme-before-button"]["status"],
            "4.1.2-dynamic-required",
        )
        self.assertEqual(
            components["theme-after-button"]["status"],
            "4.1.2-dynamic-required",
        )
        self.assertIn("aria-pressed", components["theme-after-button"]["reasons"])


if __name__ == "__main__":
    unittest.main()
