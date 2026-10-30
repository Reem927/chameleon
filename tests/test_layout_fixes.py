"""Regression tests for problems the fixture suite found (plan Phase 6)."""

import json
import unittest
from pathlib import Path

from engine.layouts import _backing_shapes, _parts, generate_candidates
from engine.text_fit import text_overflow


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _load_source(name):
    with (FIXTURES_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("source", data)


def _by_id(design):
    return {element["id"]: element for element in design["elements"]}


class FullCanvasShapeTests(unittest.TestCase):
    def test_full_canvas_rectangle_fills_every_target_like_a_cover_image(self):
        source = _load_source("dense_12")
        for target in ({"width": 1080, "height": 1920}, {"width": 728, "height": 90}):
            for name, candidate in generate_candidates(source, target):
                with self.subTest(target=target, strategy=name):
                    panel = _by_id(candidate)["panel"]
                    self.assertEqual(
                        (panel["x"], panel["y"], panel["width"], panel["height"]),
                        (0.0, 0.0, float(target["width"]), float(target["height"])),
                    )

    def test_partial_or_rotated_shapes_are_not_backgrounds(self):
        source = {
            "canvas": {"width": 400, "height": 400},
            "elements": [
                {
                    "id": "band", "type": "shape", "shape_type": "rectangle",
                    "fill_color": "#112233", "x": 0, "y": 0, "width": 400, "height": 200,
                    "rotation": 0,
                },
                {
                    "id": "tilted", "type": "shape", "shape_type": "rectangle",
                    "fill_color": "#445566", "x": 0, "y": 0, "width": 400, "height": 400,
                    "rotation": 10,
                },
            ],
        }
        target = {"width": 800, "height": 200}
        for name, candidate in generate_candidates(source, target):
            with self.subTest(strategy=name):
                elements = _by_id(candidate)
                for element_id in ("band", "tilted"):
                    self.assertNotEqual(
                        (elements[element_id]["width"], elements[element_id]["height"]),
                        (800.0, 200.0),
                    )


def _contains(parent, child, tolerance=0.5):
    return (
        parent["x"] <= child["x"] + tolerance
        and parent["y"] <= child["y"] + tolerance
        and parent["x"] + parent["width"] >= child["x"] + child["width"] - tolerance
        and parent["y"] + parent["height"] >= child["y"] + child["height"] - tolerance
    )


class BackingShapeTests(unittest.TestCase):
    TARGETS = (
        {"width": 1080, "height": 1080},
        {"width": 1080, "height": 1920},
        {"width": 1200, "height": 628},
        {"width": 728, "height": 90},
        {"width": 160, "height": 600},
    )

    def test_backing_shape_keeps_holding_its_text_in_every_layout(self):
        source = _load_source("layered")
        for target in self.TARGETS:
            for name, candidate in generate_candidates(source, target):
                with self.subTest(target=target, strategy=name):
                    elements = _by_id(candidate)
                    self.assertTrue(_contains(elements["card_back"], elements["card_copy"]))
                    self.assertTrue(_contains(elements["stripe"], elements["overlay_title"]))

    def test_full_width_backing_band_still_spans_the_target_width(self):
        source = _load_source("layered")
        for target in self.TARGETS:
            for name, candidate in generate_candidates(source, target):
                with self.subTest(target=target, strategy=name):
                    stripe = _by_id(candidate)["stripe"]
                    self.assertEqual(stripe["x"], 0.0)
                    self.assertEqual(stripe["width"], float(target["width"]))

    def test_backing_padding_never_covers_another_unit(self):
        source = _load_source("layered")
        for target in self.TARGETS:
            for name, candidate in generate_candidates(source, target):
                with self.subTest(target=target, strategy=name):
                    elements = _by_id(candidate)
                    card, title = elements["card_back"], elements["overlay_title"]
                    overlap_x = min(card["x"] + card["width"], title["x"] + title["width"]) - max(
                        card["x"], title["x"]
                    )
                    overlap_y = min(card["y"] + card["height"], title["y"] + title["height"]) - max(
                        card["y"], title["y"]
                    )
                    self.assertFalse(overlap_x > 0.5 and overlap_y > 0.5)

    def test_large_decorative_glow_around_a_unit_is_not_a_backing(self):
        with (ROOT / "input" / "chameleon_sample_level2_core.json").open(encoding="utf-8") as handle:
            source = json.load(handle)["source"]
        _backgrounds, decorations, units = _parts(source)
        self.assertEqual(_backing_shapes(source, decorations, units), {})

    def test_shape_above_the_text_is_not_a_backing(self):
        source = _load_source("layered")
        for element in source["elements"]:
            if element["id"] == "card_back":
                element["z_index"] = 9
        target = {"width": 1600, "height": 400}
        moved = [
            _contains(_by_id(candidate)["card_back"], _by_id(candidate)["card_copy"])
            for _name, candidate in generate_candidates(source, target)
        ]
        self.assertFalse(all(moved))


class UniformScaleTextTests(unittest.TestCase):
    def test_preserved_layout_text_still_fits_its_box_after_scaling(self):
        source = _load_source("huge_25")
        for target in ({"width": 300, "height": 250}, {"width": 600, "height": 600}):
            candidate = dict(generate_candidates(source, target))["preserve_and_repair"]
            for element in candidate["elements"]:
                if element["type"] != "text":
                    continue
                with self.subTest(target=target, element=element["id"]):
                    self.assertLessEqual(text_overflow(element), 0.0)

    def test_text_that_already_fits_is_left_unchanged(self):
        source = _load_source("huge_25")
        source_text = {e["id"]: e for e in source["elements"] if e["type"] == "text"}
        target = {"width": source["canvas"]["width"], "height": source["canvas"]["height"]}
        candidate = dict(generate_candidates(source, target))["preserve_and_repair"]
        scale = None
        for element in candidate["elements"]:
            if element["id"] in source_text and text_overflow(source_text[element["id"]]) == 0:
                original = source_text[element["id"]]
                ratio = element["font_size"] / original["font_size"]
                scale = ratio if scale is None else scale
                with self.subTest(element=element["id"]):
                    self.assertAlmostEqual(ratio, scale, places=6)
                    self.assertAlmostEqual(element["width"] / original["width"], scale, places=6)


class PreserveScaleTests(unittest.TestCase):
    def test_same_size_target_keeps_the_source_geometry(self):
        # Content of these fixtures sits inside the safe margin, so nothing
        # needs repair; tiny_text reaches into the margin and rightly shrinks.
        for name in ("missing_asset", "unknown_font"):
            source = _load_source(name)
            target = dict(source["canvas"])
            candidate = dict(generate_candidates(source, target))["preserve_and_repair"]
            output = _by_id(candidate)
            for original in source["elements"]:
                element = output[original["id"]]
                with self.subTest(fixture=name, element=original["id"]):
                    for key in ("x", "y", "width", "height"):
                        self.assertAlmostEqual(element[key], original[key], places=6)

    def test_content_never_grows_faster_than_the_canvas(self):
        source = _load_source("missing_asset")
        target = {"width": 2 * source["canvas"]["width"], "height": 2 * source["canvas"]["height"]}
        candidate = dict(generate_candidates(source, target))["preserve_and_repair"]
        output = _by_id(candidate)
        for original in source["elements"]:
            if original["type"] == "text":
                with self.subTest(element=original["id"]):
                    self.assertLessEqual(
                        output[original["id"]]["font_size"], 2 * original["font_size"] + 1e-6
                    )


if __name__ == "__main__":
    unittest.main()
