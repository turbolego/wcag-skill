import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
FRONTMATTER = SKILL.split("---", 2)[1]
DECLARED = set(re.findall(r"^\s*- name: ([A-Z0-9_]+)$", FRONTMATTER, re.MULTILINE))

# Optional environment variables read by bundled runtime scripts and templates.
USED = {
    "scripts/a11y-audit.sh": {
        "AXE_CHROME_PATH", "AXE_CHROMEDRIVER_PATH", "AXE_CHROME_EXTRA_ARGS", "CI",
    },
    "scripts/a11y-audit-limited.sh": {
        "NODE_OPTIONS", "ULIMIT_PERCENT", "ULIMIT_MIN_MB", "NODE_PERCENT", "NODE_MIN_MB",
    },
    "templates/playwright-state.spec.ts": {"WCAG_TEST_URL"},
}


class SkillCapabilityTests(unittest.TestCase):
    def test_allowed_tools_is_an_explicit_minimal_list(self):
        match = re.search(r"^allowed-tools:\s*(\[.*\])$", FRONTMATTER, re.MULTILINE)
        self.assertIsNotNone(match, "SKILL.md must declare allowed-tools")
        self.assertEqual(
            json.loads(match.group(1)),
            ["exec", "read", "write", "edit", "shell", "env"],
        )

    def test_every_environment_variable_read_is_declared(self):
        for path, names in USED.items():
            source = (ROOT / path).read_text(encoding="utf-8")
            for name in names:
                with self.subTest(path=path, name=name):
                    self.assertRegex(source, rf"(\$\{{{name}\b|process\.env\.{name}\b)")
                    self.assertIn(name, DECLARED)

    def test_no_credentials_are_declared(self):
        self.assertFalse({n for n in DECLARED if re.search("TOKEN|SECRET|KEY|PASSWORD", n)})

    def test_capability_table_covers_bundled_scripts(self):
        section = SKILL.split("## Capabilities and boundaries", 1)[1].split("\n## ", 1)[0]
        for path in (
            "scripts/a11y-audit.sh", "scripts/a11y-audit-limited.sh",
            "scripts/run-w3c-validator.mjs", "scripts/check-wcag-412.py",
            "benchmark/scripts/check-tag-coverage.py", "templates/playwright-state.spec.ts",
        ):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())
                self.assertIn(f"`{path}", section)
        for phrase in (
            "does not sandbox shell commands",
            "No script requires or reads credentials",
            "Audit only URLs you are authorized to test",
            "Use a dedicated output directory",
            "Keep the Chrome sandbox enabled outside isolated CI",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, " ".join(section.split()))


if __name__ == "__main__":
    unittest.main()
