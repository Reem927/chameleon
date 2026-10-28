import math
import unittest
from copy import deepcopy

from engine.geometry import (
    Bounds,
    clamp_element,
    clamp_group,
    element_bounds,
    overlap_area,
    scale_element,
    translate_group,
)


class GeometryTests(unittest.TestCase):
    def test_rotated_bounds_use_the_element_center(self):
        bounds = element_bounds(
            {"x": 10, "y": 20, "width": 40, "height": 20, "rotation": 90}
        )

        self.assertAlmostEqual(bounds.left, 20)
        self.assertAlmostEqual(bounds.top, 10)
        self.assertAlmostEqual(bounds.right, 40)
        self.assertAlmostEqual(bounds.bottom, 50)
        self.assertEqual(bounds.center, (30, 30))

    def test_overlap_area_handles_partial_touching_and_separate_bounds(self):
        first = Bounds(0, 0, 10, 10)

        self.assertEqual(overlap_area(first, Bounds(5, 4, 12, 8)), 20)
        self.assertEqual(overlap_area(first, Bounds(10, 2, 20, 8)), 0)
        self.assertEqual(overlap_area(first, Bounds(11, 2, 20, 8)), 0)

    def test_translation_returns_deep_copies_without_mutating_nested_fields(self):
        elements = [
            {
                "id": "title",
                "x": 2,
                "y": 3,
                "width": 10,
                "height": 5,
                "style_runs": [{"start": 0, "end": 2, "color": "#fff"}],
            }
        ]
        original = deepcopy(elements)

        moved = translate_group(elements, 5, -1)
        moved[0]["style_runs"][0]["color"] = "#000"

        self.assertEqual(elements, original)
        self.assertEqual((moved[0]["x"], moved[0]["y"]), (7, 2))
        self.assertEqual(elements[0]["style_runs"][0]["color"], "#fff")

    def test_uniform_scale_uses_origin_and_scales_text_size(self):
        element = {
            "type": "text",
            "x": 15,
            "y": 25,
            "width": 20,
            "height": 10,
            "font_size": 12,
            "metadata": {"locked": True},
        }
        original = deepcopy(element)

        scaled = scale_element(element, 0.5, origin=(5, 5))
        scaled["metadata"]["locked"] = False

        self.assertEqual(element, original)
        self.assertEqual(
            (scaled["x"], scaled["y"], scaled["width"], scaled["height"]),
            (10, 15, 10, 5),
        )
        self.assertEqual(scaled["font_size"], 6)
        self.assertTrue(element["metadata"]["locked"])

    def test_group_clamp_uses_one_translation_for_every_element(self):
        elements = [
            {"id": "a", "x": -5, "y": 4, "width": 10, "height": 10},
            {"id": "b", "x": 20, "y": 9, "width": 10, "height": 10},
        ]
        original = deepcopy(elements)

        clamped = clamp_group(elements, {"width": 50, "height": 30})

        self.assertIsNotNone(clamped)
        self.assertEqual(elements, original)
        self.assertEqual([(item["x"], item["y"]) for item in clamped], [(0, 4), (25, 9)])

    def test_rotated_element_is_clamped_using_visible_bounds(self):
        element = {"x": 0, "y": 0, "width": 20, "height": 20, "rotation": 45}

        clamped = clamp_element(element, {"width": 40, "height": 40})

        self.assertIsNotNone(clamped)
        bounds = element_bounds(clamped)
        self.assertAlmostEqual(bounds.left, 0)
        self.assertAlmostEqual(bounds.top, 0)

    def test_oversized_group_cannot_be_clamped(self):
        elements = [{"x": 0, "y": 0, "width": 51, "height": 10}]

        self.assertIsNone(clamp_group(elements, {"width": 50, "height": 50}))

    def test_non_finite_geometry_is_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    element_bounds({"x": value, "y": 0, "width": 1, "height": 1})
                with self.assertRaises(ValueError):
                    scale_element({"x": 0, "y": 0, "width": 1, "height": 1}, value)


if __name__ == "__main__":
    unittest.main()
