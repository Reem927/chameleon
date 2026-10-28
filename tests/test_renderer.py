import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from renderer.converter.convert import render_design_to_png


ROOT = Path(__file__).resolve().parents[1]


class RendererIntegrationTests(unittest.TestCase):
    def render_source(self, sample_name):
        task = json.loads((ROOT / "input" / sample_name).read_text())
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "preview.png"
        warnings = render_design_to_png(
            task["source"], ROOT / "brand_kit" / "assets", output
        )
        return task, output, warnings

    def test_real_renderer_creates_a_png_at_the_canvas_size(self):
        task, output, warnings = self.render_source("chameleon_sample_level1_warmup.json")

        self.assertEqual(warnings, [])
        self.assertTrue(output.is_file())
        with Image.open(output) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (1080, 1080))
        self.assertEqual(task["source"]["canvas"], {"width": 1080, "height": 1080})

    def test_missing_level3_asset_uses_the_expected_placeholder_warning(self):
        _, output, warnings = self.render_source("chameleon_sample_level3_advanced.json")

        self.assertTrue(output.is_file())
        self.assertEqual(len(warnings), 1)
        self.assertIn("solstice_holiday_badge_2025.png", warnings[0])
        self.assertIn("holiday_watermark", warnings[0])


if __name__ == "__main__":
    unittest.main()
