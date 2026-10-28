import json
import unittest
from itertools import combinations
from pathlib import Path

from engine.constraints import validate_candidate
from engine.layouts import READABLE_FONT_SIZE
from engine.resize import resize
from engine.text_fit import text_overflow


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = (
    "chameleon_sample_level1_warmup.json",
    "chameleon_sample_level2_core.json",
    "chameleon_sample_level3_advanced.json",
)
# Common ad and social sizes, from extreme banners to tall stories.
TARGETS = (
    (1080, 1080),
    (1080, 1350),
    (1080, 1920),
    (1200, 628),
    (1600, 400),
    (970, 250),
    (728, 90),
    (320, 50),
    (300, 250),
    (160, 600),
)


def _load(name):
    with (ROOT / "input" / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _fonts(output):
    return {
        element["id"]: element["font_size"]
        for element in output["elements"]
        if element["type"] == "text"
    }


class ReadabilityTests(unittest.TestCase):
    def test_text_renders_inside_its_box_for_common_targets(self):
        for name in SAMPLES:
            source = _load(name)["source"]
            for width, height in TARGETS:
                target = {"width": width, "height": height}
                with self.subTest(sample=name, target=f"{width}x{height}"):
                    output = resize(source, target)
                    self.assertEqual(validate_candidate(source, target, output), [])
                    for element in output["elements"]:
                        if element["type"] == "text":
                            self.assertLessEqual(
                                text_overflow(element), 0.02, element["id"]
                            )

    def test_extreme_banner_keeps_key_text_readable(self):
        task = _load("chameleon_sample_level3_advanced.json")
        fonts = _fonts(resize(task["source"], task["target_canvas"]))

        self.assertGreaterEqual(fonts["headline"], 10)
        self.assertGreaterEqual(min(fonts.values()) + 1e-9, READABLE_FONT_SIZE)

    def test_wide_banner_keeps_supporting_text_readable(self):
        task = _load("chameleon_sample_level2_core.json")
        fonts = _fonts(resize(task["source"], task["target_canvas"]))

        self.assertGreaterEqual(fonts["headline"], 28)
        self.assertGreaterEqual(fonts["subhead"], 12)

    def test_standalone_text_keeps_its_size_order(self):
        for name in SAMPLES:
            task = _load(name)
            source_texts = [
                element
                for element in task["source"]["elements"]
                if element["type"] == "text" and not element.get("group_id")
            ]
            fonts = _fonts(resize(task["source"], task["target_canvas"]))
            for first, second in combinations(source_texts, 2):
                if first["font_size"] == second["font_size"]:
                    continue
                larger, smaller = sorted((first, second), key=lambda e: -e["font_size"])
                with self.subTest(sample=name, larger=larger["id"], smaller=smaller["id"]):
                    self.assertGreaterEqual(
                        fonts[larger["id"]], fonts[smaller["id"]] - 1e-9
                    )


if __name__ == "__main__":
    unittest.main()
