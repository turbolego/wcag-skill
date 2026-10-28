import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
AAA_MATRIX = (ROOT / "references/aaa-evidence-matrix.md").read_text(
    encoding="utf-8"
)


class WcagFocusGuidanceTests(unittest.TestCase):
    def assert_guidance(self, text, pattern):
        self.assertIsNotNone(
            re.search(pattern, text, re.IGNORECASE | re.DOTALL),
            f"Missing required guidance: {pattern}",
        )

    def test_focus_visible_is_aa_criterion_247(self):
        self.assert_guidance(
            SKILL, r"AA,\s*WCAG 2\.2 SC\s+2\.4\.7 Focus Visible"
        )

    def test_skill_does_not_misclassify_focus_appearance_as_aa_2411(self):
        self.assertIsNone(
            re.search(r"2\.4\.11\s+Focus Appearance", SKILL, re.IGNORECASE),
            "SC 2.4.11 is Focus Not Obscured (Minimum), not Focus Appearance",
        )

    def test_non_text_contrast_is_separate_aa_criterion_1411(self):
        self.assert_guidance(
            SKILL,
            r"SC 1\.4\.11 Non-text Contrast \(AA\).{0,180}3:1.{0,100}exceptions",
        )

    def test_focus_not_obscured_minimum_is_aa_criterion_2411(self):
        self.assert_guidance(
            SKILL,
            r"2\.4\.11 Focus Not Obscured \(Minimum, AA\).{0,120}not entirely hidden",
        )
        self.assert_guidance(
            AAA_MATRIX, r"2\.4\.11\s+Focus Not Obscured \(Minimum\)"
        )

    def test_focus_not_obscured_enhanced_is_aaa_criterion_2412(self):
        self.assert_guidance(
            SKILL,
            r"2\.4\.12 Focus Not Obscured \(Enhanced, AAA\).{0,200}no\s+part",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"2\.4\.12\s*\|\s*Focus Not Obscured \(Enhanced, AAA\)",
        )
        self.assert_guidance(
            AAA_MATRIX, r"no part of a focused component may be hidden by author-created content"
        )

    def test_aaa_matrix_states_focus_not_obscured_level_and_requirement(self):
        self.assert_guidance(
            AAA_MATRIX,
            r"\|\s*2\.4\.12\s*\|\s*Focus Not Obscured \(Enhanced, AAA\)\s*\|"
            r".{0,180}no part of a focused component may be hidden by author-created content",
        )

    def test_focus_appearance_is_aaa_criterion_2413(self):
        self.assert_guidance(
            SKILL, r"Focus Appearance \(SC 2\.4\.13, AAA\)"
        )
        self.assert_guidance(
            SKILL, r"two-CSS-pixel-thick perimeter of the unfocused component"
        )
        self.assert_guidance(
            SKILL, r"3:1 contrast between the same pixels in focused and unfocused states"
        )
        self.assert_guidance(
            SKILL, r"2\.4\.13\s+Focus Appearance \(AAA\)"
        )
        self.assert_guidance(
            SKILL, r"These are AAA requirements, not AA requirements"
        )
        self.assert_guidance(
            SKILL, r"an optional recommendation for AA\s+projects"
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"\|\s*2\.4\.13\s*\|\s*Focus Appearance \(AAA\)\s*\|"
            r".{0,250}two-CSS-pixel-thick perimeter of the unfocused component or sub-component"
            r".{0,200}same pixels.{0,100}3:1 contrast",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"the user agent determines the indicator and the author cannot adjust it",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"the indicator and its background color are not modified by the author",
        )

    def test_aaa_matrix_separates_inherited_aa_focus_criteria(self):
        self.assert_guidance(
            AAA_MATRIX,
            r"\|\s*1\.4\.11\s*\|\s*Non-text Contrast \(AA\)\s*\|"
            r".{0,400}≥3:1.{0,200}distinct from SC 2\.4\.13",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"except inactive components or appearances determined by the user agent "
            r"and not modified by the author",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"parts of graphics required to understand content \(except an essential presentation\)",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"\|\s*2\.4\.7\s*\|\s*Focus Visible \(AA\)\s*\|"
            r".{0,180}at least one mode of operation in which its keyboard focus indicator is visible"
            r".{0,100}Keep the indicator visible while focus is shown",
        )
        self.assert_guidance(
            AAA_MATRIX,
            r"\|\s*2\.4\.11\s*\|\s*Focus Not Obscured \(Minimum, AA\)\s*\|"
            r".{0,180}not entirely hidden.{0,230}reveal the focused component without advancing focus"
            r".{0,150}SC 2\.4\.12",
        )

    def test_skip_mechanism_is_not_limited_to_skip_links(self):
        self.assert_guidance(
            SKILL,
            r"mechanism to\s+bypass repeated blocks where applicable \(such as a skip link\)",
        )

    def test_dragging_requires_a_single_pointer_non_dragging_alternative(self):
        self.assert_guidance(
            SKILL,
            r"all functionality that uses dragging can also be achieved by a single\s+"
            r"pointer without dragging \(AA\)",
        )
        self.assert_guidance(
            SKILL,
            r"unless dragging is essential or the\s+functionality is determined by "
            r"the user agent and not modified by the\s+author",
        )
        self.assertIsNone(
            re.search(r"dragging.{0,100}cancellation", SKILL, re.IGNORECASE | re.DOTALL),
            "Cancellation alone is not an alternative under SC 2.5.7",
        )

    def test_dragging_target_size_is_not_mislabeled_as_an_aaa_requirement(self):
        self.assert_guidance(
            SKILL,
            r"Pointer target \(SC 2\.5\.8 AA / SC 2\.5\.5 AAA\)",
        )
        self.assert_guidance(SKILL, r"Dragging movements \(SC 2\.5\.7\)")
        self.assert_guidance(SKILL, r"Same AA requirement")
        self.assertIsNone(
            re.search(
                r"Dragging movements.{0,150}AAA requires pointer target",
                SKILL,
                re.IGNORECASE | re.DOTALL,
            ),
            "44x44 target size belongs to SC 2.5.5, not SC 2.5.7",
        )


if __name__ == "__main__":
    unittest.main()
