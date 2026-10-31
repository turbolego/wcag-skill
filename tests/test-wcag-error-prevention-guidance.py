import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (ROOT / "references/manual-test-protocol.md").read_text(
    encoding="utf-8"
)
AAA_MATRIX = (ROOT / "references/aaa-evidence-matrix.md").read_text(
    encoding="utf-8"
)


class ErrorPreventionGuidanceTests(unittest.TestCase):
    def assert_guidance(self, text, pattern):
        self.assertIsNotNone(
            re.search(pattern, " ".join(text.split()), re.IGNORECASE | re.DOTALL),
            f"Missing required guidance: {pattern}",
        )

    def test_matrix_describes_all_three_alternatives_and_at_least_one(self):
        self.assert_guidance(
            AAA_MATRIX,
            r"3\.3\.6\s*\|\s*Error Prevention \(All\)\s*\|"
            r".{0,180}at least one:.{0,100}submissions are reversible;"
            r".{0,100}checked for input errors.{0,160}required information omitted"
            r".{0,100}outside the required format or allowed values"
            r".{0,100}opportunity to correct"
            r".{0,100}review, confirm, and correct information before finalizing",
        )
        self.assert_guidance(AAA_MATRIX, r"Record which alternative is met")

    def test_protocol_scopes_submissions_and_uses_safe_test_data(self):
        self.assert_guidance(
            PROTOCOL, r"every page that requires users to submit information"
        )
        self.assert_guidance(PROTOCOL, r"at least\s+one SC 3\.3\.6 safeguard")
        self.assert_guidance(
            PROTOCOL,
            r"input errors \(required information omitted or values outside the"
            r"\s+required format or allowed values\)",
        )
        self.assert_guidance(
            PROTOCOL,
            r"authorized\s+staging/test environment with synthetic records and"
            r"\s+sandbox\s+payments",
        )
        self.assert_guidance(
            PROTOCOL,
            r"not perform live transactions, legal commitments, or record\s+changes",
        )
        self.assert_guidance(
            PROTOCOL, r"explicit authorization\. If safe testing is unavailable"
        )
        self.assert_guidance(
            PROTOCOL,
            r"record any test limitation rather than\s+executing a"
            r"\s+consequential action",
        )

    def test_authorization_is_scoped_and_accounts_are_restricted(self):
        self.assert_guidance(
            PROTOCOL,
            r"authorization scope: environment, permitted operations, synthetic "
            r"records, and transaction limits",
        )
        self.assert_guidance(
            PROTOCOL,
            r"read-only accounts for inspection and narrowly scoped test accounts "
            r"for state-changing tests",
        )
        self.assert_guidance(
            PROTOCOL,
            r"enforce restrictions through the application/provider or tool host",
        )

    def test_mock_success_does_not_prove_production_conformance(self):
        self.assert_guidance(
            PROTOCOL,
            r"Mock or staging success is evidence for that environment, "
            r"not proof of production behavior",
        )
        self.assert_guidance(
            PROTOCOL,
            r"unexecuted checks as `Needs human review`, not `Pass` or `Not applicable`",
        )

    def test_removing_each_mitigation_is_detected(self):
        for phrase in (
            "synthetic records",
            "sandbox payments",
            "explicit authorization",
            "authorization scope",
            "read-only accounts",
            "not proof of production",
            "Needs human review",
        ):
            with self.subTest(phrase=phrase):
                normalized = " ".join(PROTOCOL.split())
                self.assertIn(phrase, normalized)
                with self.assertRaises(AssertionError):
                    self.assert_guidance(normalized.replace(phrase, ""), re.escape(phrase))


if __name__ == "__main__":
    unittest.main()
