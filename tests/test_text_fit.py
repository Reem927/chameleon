import unittest
from pathlib import Path

from engine.text_fit import fit_text, line_count
from renderer.converter.brand_fonts import load_brand_font_manager
from renderer.converter.convert import _normalize_weight, _weight_style_to_font_style
from renderer.converter.wrap import char_widths, wrap_text


ROOT = Path(__file__).resolve().parents[1]
FONT_MANAGER = load_brand_font_manager(str(ROOT / "brand_kit" / "fonts"))
LONG_COPY = (
    "Small-batch botanical infusions blended with wild honey, blood orange zest, "
    "and a whisper of smoked rosemary, bottled at the peak of golden hour."
)


def _text(content=LONG_COPY, font_family="Solstice Sans", font_weight="regular", **extra):
    element = {
        "id": "copy",
        "type": "text",
        "x": 0,
        "y": 0,
        "width": 400,
        "height": 100,
        "content": content,
        "font_family": font_family,
        "font_size": 30,
        "font_weight": font_weight,
        "color": "rgba(0,0,0,1)",
    }
    element.update(extra)
    return element


def _rendered_lines(element):
    """Wrap exactly like the official renderer and return the line widths."""
    weight = _normalize_weight(element.get("font_weight"))
    style = _weight_style_to_font_style(weight == "bold", element.get("font_style") == "italic")
    widths = char_widths(
        FONT_MANAGER,
        element["font_family"],
        weight,
        style,
        element["font_size"],
        element["content"],
    )
    wrapped = wrap_text(element["content"], widths, element["width"])
    lines, width = [], 0.0
    for character, advance in zip(wrapped, widths):
        if character == "\n":
            lines.append(width)
            width = 0.0
        else:
            width += advance
    lines.append(width)
    return lines


class TextFitTests(unittest.TestCase):
    def assertRendersInside(self, element):
        lines = _rendered_lines(element)
        line_height = element.get("line_height", 1.2)
        self.assertLessEqual(max(lines), element["width"] + 1e-6)
        self.assertLessEqual(
            len(lines) * element["font_size"] * line_height, element["height"] + 1e-6
        )

    def test_fitted_brand_text_stays_inside_its_box_when_rendered(self):
        for weight in ("regular", "bold"):
            with self.subTest(weight=weight):
                fitted = fit_text(_text(font_weight=weight), 300, 90, max_font_size=40)
                self.assertRendersInside(fitted)

    def test_fitted_size_is_the_largest_that_fits(self):
        fitted = fit_text(_text(), 300, 90, max_font_size=40)
        bigger = dict(fitted, font_size=fitted["font_size"] * 1.08, height=90)

        self.assertLess(fitted["font_size"], 40)
        lines = _rendered_lines(bigger)
        self.assertGreater(len(lines) * bigger["font_size"] * 1.2, 90)

    def test_short_text_is_capped_at_the_maximum_font_size(self):
        fitted = fit_text(_text(content="SALE"), 600, 300, max_font_size=24)

        self.assertEqual(fitted["font_size"], 24)
        self.assertRendersInside(fitted)

    def test_box_height_shrinks_to_the_wrapped_lines(self):
        fitted = fit_text(_text(content="SALE"), 600, 300, max_font_size=24)

        self.assertAlmostEqual(fitted["height"], 24 * 1.2)
        self.assertEqual(fitted["width"], 600)

    def test_a_long_single_word_shrinks_until_it_fits_the_width(self):
        fitted = fit_text(_text(content="Supercalifragilistic"), 80, 200, max_font_size=40)

        self.assertRendersInside(fitted)
        self.assertEqual(line_count(fitted), 1)

    def test_letter_spacing_and_line_height_are_respected(self):
        element = _text(letter_spacing=3, line_height=1.5)
        fitted = fit_text(element, 300, 120, max_font_size=40)

        lines = _rendered_lines(fitted)
        spaced = max(lines) + 3 * len(fitted["content"])
        self.assertLessEqual(len(lines) * fitted["font_size"] * 1.5, 120 + 1e-6)
        self.assertLess(line_count(fitted) * fitted["font_size"] * 1.5, 120 + 1e-6)
        self.assertGreater(spaced, max(lines))

    def test_unknown_font_family_uses_a_conservative_estimate(self):
        fitted = fit_text(_text(font_family="Not A Real Font"), 300, 90, max_font_size=40)

        self.assertGreaterEqual(fitted["font_size"], 1)
        self.assertLessEqual(line_count(fitted) * fitted["font_size"] * 1.2, 90 + 1e-6)

    def test_fit_never_mutates_the_input_element(self):
        element = _text()
        before = dict(element)
        fit_text(element, 300, 90, max_font_size=40)

        self.assertEqual(element, before)


if __name__ == "__main__":
    unittest.main()
