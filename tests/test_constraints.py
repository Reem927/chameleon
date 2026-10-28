import math
import unittest
from copy import deepcopy

from engine.constraints import candidate_is_valid, validate_candidate


def source_design():
    return {
        "canvas": {"width": 200, "height": 200},
        "elements": [
            {
                "id": "title",
                "type": "text",
                "x": 10,
                "y": 10,
                "width": 80,
                "height": 20,
                "content": "Hello",
                "font_family": "SolsticeSans",
                "font_size": 16,
                "color": "#ffffff",
                "style_runs": [{"start": 0, "end": 5, "color": "#ffffff"}],
            },
            {
                "id": "photo",
                "type": "image",
                "x": 20,
                "y": 50,
                "width": 100,
                "height": 100,
                "asset_id": "bottle",
                "fit": "contain",
            },
            {
                "id": "panel",
                "type": "shape",
                "x": 0,
                "y": 0,
                "width": 200,
                "height": 200,
                "shape_type": "rectangle",
                "fill_color": "#123456",
            },
        ],
    }


def valid_candidate(source=None, canvas=None):
    source = source or source_design()
    canvas = canvas or {"width": 500, "height": 500}
    return {"canvas": deepcopy(canvas), "elements": deepcopy(source["elements"])}


class ConstraintTests(unittest.TestCase):
    def setUp(self):
        self.source = source_design()
        self.canvas = {"width": 500, "height": 500}
        self.candidate = valid_candidate(self.source, self.canvas)

    def problems(self):
        return validate_candidate(self.source, self.canvas, self.candidate)

    def assertProblemContains(self, text):
        self.assertTrue(
            any(text in problem for problem in self.problems()),
            f"expected a problem containing {text!r}; got {self.problems()!r}",
        )

    def test_valid_candidate_passes_and_validation_does_not_mutate_inputs(self):
        source_before = deepcopy(self.source)
        canvas_before = deepcopy(self.canvas)
        candidate_before = deepcopy(self.candidate)

        self.assertTrue(candidate_is_valid(self.source, self.canvas, self.candidate))
        self.assertEqual(self.source, source_before)
        self.assertEqual(self.canvas, canvas_before)
        self.assertEqual(self.candidate, candidate_before)

    def test_candidate_requires_exact_top_level_fields(self):
        self.candidate["debug"] = True

        self.assertProblemContains("only 'canvas' and 'elements'")

    def test_canvas_requires_exact_fields_and_target_value(self):
        self.candidate["canvas"]["unit"] = "px"

        self.assertProblemContains("only width and height")
        self.assertProblemContains("exactly match target_canvas")

    def test_output_id_counts_must_match_and_duplicates_are_reported(self):
        self.candidate["elements"].append(deepcopy(self.candidate["elements"][0]))

        self.assertProblemContains("output contains duplicate ids")
        self.assertProblemContains("ids and counts must exactly match")

    def test_duplicate_source_ids_are_reported(self):
        duplicate = deepcopy(self.source["elements"][0])
        self.source["elements"].append(duplicate)
        self.candidate = valid_candidate(self.source, self.canvas)

        self.assertProblemContains("source contains duplicate ids")

    def test_protected_nested_fields_cannot_change(self):
        self.candidate["elements"][0]["style_runs"][0]["color"] = "#000000"

        self.assertProblemContains("changed protected field 'style_runs'")

    def test_element_field_set_must_be_exact(self):
        self.candidate["elements"][0]["new_field"] = "not allowed"

        self.assertProblemContains("preserve its exact field set")

    def test_protected_type_and_content_cannot_change(self):
        self.candidate["elements"][0]["content"] = "Goodbye"

        self.assertProblemContains("changed protected field 'content'")

    def test_non_finite_element_numbers_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                self.candidate["elements"][0]["x"] = value
                self.assertProblemContains("field 'x' must be a finite number")

    def test_rotated_visible_bounds_must_remain_on_canvas(self):
        self.candidate["elements"][0].update(
            {"x": 0, "y": 0, "width": 20, "height": 20, "rotation": 45}
        )

        self.assertProblemContains("outside the target canvas after rotation")

    def test_image_aspect_ratio_accepts_exact_five_percent_change(self):
        self.candidate["elements"][1]["width"] = 105

        self.assertTrue(candidate_is_valid(self.source, self.canvas, self.candidate))

    def test_image_aspect_ratio_rejects_more_than_five_percent_change(self):
        self.candidate["elements"][1]["width"] = 105.01

        self.assertProblemContains("aspect ratio changed")

    def test_cover_image_is_exempt_from_aspect_ratio_rule(self):
        self.source["elements"][1]["fit"] = "cover"
        self.candidate = valid_candidate(self.source, self.canvas)
        self.candidate["elements"][1].update({"width": 200, "height": 50})

        self.assertTrue(candidate_is_valid(self.source, self.canvas, self.candidate))

    def test_each_element_type_requires_its_own_fields(self):
        cases = ((0, "content"), (1, "asset_id"), (2, "shape_type"))
        for index, field in cases:
            with self.subTest(field=field):
                candidate = valid_candidate(self.source, self.canvas)
                del candidate["elements"][index][field]
                problems = validate_candidate(self.source, self.canvas, candidate)
                self.assertTrue(any("missing type fields" in problem for problem in problems))

    def test_boolean_geometry_is_not_accepted_as_a_number(self):
        self.candidate["elements"][0]["width"] = True

        self.assertProblemContains("field 'width' must be a finite number")

    def test_invalid_or_malformed_enum_is_reported_without_crashing(self):
        self.candidate["elements"][1]["fit"] = []

        self.assertProblemContains("invalid fit")

    def test_zero_sized_normal_image_is_rejected_cleanly(self):
        self.candidate["elements"][1]["height"] = 0

        self.assertProblemContains("positive dimensions for ratio checking")


if __name__ == "__main__":
    unittest.main()
