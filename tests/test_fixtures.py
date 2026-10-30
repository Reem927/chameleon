"""Hard-rule checks for resize() on hand-written designs it has never seen.

Each fixture in tests/fixtures is resized into common ad and social formats
plus same-ratio canvases at half and double the source size. Only hard rules
are asserted here; tests/fixture_report.py measures quality.
"""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from engine.constraints import COMMON_REQUIRED, TYPE_REQUIRED, validate_candidate
from engine.geometry import is_on_canvas
from engine.resize import resize


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_NAMES = (
    "minimal_2",
    "card_5",
    "dense_12",
    "huge_25",
    "long_words",
    "style_runs",
    "rotated",
    "layered",
    "missing_asset",
    "unknown_font",
    "tiny_text",
    "wide_source",
    "tall_source",
)
FIXED_TARGETS = (
    (1080, 1080),
    (1080, 1350),
    (1080, 1920),
    (1200, 628),
    (1600, 400),
    (728, 90),
    (320, 50),
    (300, 250),
    (160, 600),
)
SAME_RATIO_SCALES = (0.5, 2.0)


def load_fixture(name):
    with (FIXTURES_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def targets_for(source):
    """Fixed targets plus same-ratio canvases scaled from the source."""
    targets = [{"width": width, "height": height} for width, height in FIXED_TARGETS]
    canvas = source["canvas"]
    for scale in SAME_RATIO_SCALES:
        targets.append(
            {
                "width": max(1, round(canvas["width"] * scale)),
                "height": max(1, round(canvas["height"] * scale)),
            }
        )
    return targets


def target_label(target):
    return f"{target['width']}x{target['height']}"


def may_bleed(element):
    """Cover images and faint decorative shapes may extend past the canvas."""
    if element["type"] == "image":
        return element.get("fit") == "cover"
    return element["type"] == "shape" and element.get("opacity", 1) <= 0.3


class FixtureInputTests(unittest.TestCase):
    def test_every_fixture_file_is_listed(self):
        on_disk = sorted(path.stem for path in FIXTURES_DIR.glob("*.json"))
        self.assertEqual(on_disk, sorted(FIXTURE_NAMES))

    def test_fixtures_are_schema_valid_inputs(self):
        for name in FIXTURE_NAMES:
            source = load_fixture(name)
            with self.subTest(fixture=name):
                self.assertEqual(set(source), {"canvas", "elements"})
                canvas = source["canvas"]
                self.assertEqual(set(canvas), {"width", "height"})
                self.assertTrue(all(isinstance(v, int) and v > 0 for v in canvas.values()))
                ids = [element["id"] for element in source["elements"]]
                self.assertTrue(all(isinstance(element_id, str) for element_id in ids))
                self.assertEqual(len(ids), len(set(ids)))
                for element in source["elements"]:
                    required = COMMON_REQUIRED | TYPE_REQUIRED[element["type"]]
                    self.assertLessEqual(required, set(element), element["id"])
                    self.assertGreater(element["width"], 0, element["id"])
                    self.assertGreater(element["height"], 0, element["id"])
                    if not may_bleed(element):
                        self.assertTrue(is_on_canvas(element, canvas), element["id"])


class FixtureResizeTests(unittest.TestCase):
    def test_resize_meets_hard_rules_for_every_target(self):
        for name in FIXTURE_NAMES:
            pristine = load_fixture(name)
            for target in targets_for(pristine):
                with self.subTest(fixture=name, target=target_label(target)):
                    source = deepcopy(pristine)
                    first = resize(source, dict(target))
                    second = resize(source, dict(target))
                    self.assertEqual(source, pristine, "source was mutated")
                    self.assertEqual(first, second, "output is not deterministic")
                    self.assertEqual(validate_candidate(source, target, first), [])


if __name__ == "__main__":
    unittest.main()
