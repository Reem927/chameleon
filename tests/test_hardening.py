import unittest
from copy import deepcopy

from engine.constraints import validate_candidate
from engine.resize import resize


def stress_design():
    """A small synthetic design containing the hard cases absent from samples."""
    return {
        "canvas": {"width": 1200, "height": 800},
        "elements": [
            {
                "id": "background",
                "type": "shape",
                "x": 0,
                "y": 0,
                "width": 1200,
                "height": 800,
                "shape_type": "rectangle",
                "fill_color": "#182030",
                "z_index": 0,
            },
            {
                "id": "long-title",
                "type": "text",
                "x": 120,
                "y": 90,
                "width": 960,
                "height": 120,
                "content": "A deliberately long headline that must survive every canvas shape",
                "font_family": "SolsticeSans",
                "font_size": 48,
                "color": "#ffffff",
                "rotation": -4,
                "z_index": 2,
            },
            {
                "id": "card",
                "type": "shape",
                "x": 160,
                "y": 300,
                "width": 400,
                "height": 280,
                "shape_type": "rectangle",
                "fill_color": "#ff7744",
                "rotation": 8,
                "group_id": "offer",
                "z_index": 1,
            },
            {
                "id": "product",
                "type": "image",
                "x": 210,
                "y": 340,
                "width": 140,
                "height": 210,
                "asset_id": "synthetic-product",
                "fit": "contain",
                "rotation": 8,
                "group_id": "offer",
                "z_index": 2,
            },
            {
                "id": "offer-copy",
                "type": "text",
                "x": 375,
                "y": 365,
                "width": 145,
                "height": 110,
                "content": "Limited offer",
                "font_family": "SolsticeSans",
                "font_size": 28,
                "color": "#182030",
                "rotation": 8,
                "group_id": "offer",
                "z_index": 3,
            },
        ],
    }


class HardeningTests(unittest.TestCase):
    def test_varied_canvas_shapes_are_valid_deterministic_and_non_mutating(self):
        targets = (
            {"width": 300, "height": 1200},
            {"width": 1600, "height": 400},
            {"width": 320, "height": 100},
            {"width": 700, "height": 700},
        )
        for target in targets:
            with self.subTest(target=target):
                source = stress_design()
                source_before = deepcopy(source)

                first = resize(source, target)
                second = resize(source, target)

                self.assertEqual(first, second)
                self.assertEqual(source, source_before)
                self.assertEqual(validate_candidate(source, target, first), [])

    def test_long_text_rotation_and_group_metadata_are_preserved(self):
        source = stress_design()
        output = resize(source, {"width": 1600, "height": 400})
        source_by_id = {element["id"]: element for element in source["elements"]}

        for result in output["elements"]:
            original = source_by_id[result["id"]]
            for field in ("content", "rotation", "group_id"):
                if field in original:
                    self.assertEqual(result[field], original[field])

        product = next(element for element in output["elements"] if element["id"] == "product")
        self.assertAlmostEqual(product["width"] / product["height"], 2 / 3)


if __name__ == "__main__":
    unittest.main()
