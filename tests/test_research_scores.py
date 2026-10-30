"""Score parts borrowed from the layout papers (plan Phase 9, D-023, D-025).

reading_order and area_share come from Attribute-conditioned LayoutGAN;
source_alignment, similarity and the parent/child collision rule come from
LayoutRectifier.
"""

import json
import math
import unittest
from copy import deepcopy
from pathlib import Path

from engine.layouts import (
    QUALITY_WEIGHTS,
    candidate_score_breakdown,
    generate_candidates,
    score_candidate,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
NEW_PARTS = ("reading_order", "area_share", "source_alignment", "similarity")


def _text(element_id, x, y, width=100, height=30, font_size=20, z_index=2):
    return {
        "id": element_id, "type": "text", "x": x, "y": y, "width": width, "height": height,
        "rotation": 0, "content": "Readable text", "font_size": font_size,
        "line_height": 1.2, "z_index": z_index,
    }


def _shape(element_id, x, y, width, height, z_index=1):
    return {
        "id": element_id, "type": "shape", "shape_type": "rectangle", "fill_color": "#223344",
        "x": x, "y": y, "width": width, "height": height, "rotation": 0, "z_index": z_index,
    }


def _design(elements, width=600, height=400):
    return {"canvas": {"width": width, "height": height}, "elements": elements}


def _moved(design, element_id, **changes):
    result = deepcopy(design)
    for element in result["elements"]:
        if element["id"] == element_id:
            element.update(changes)
    return result


def _part(source, candidate, name):
    return candidate_score_breakdown(source, candidate["canvas"], candidate)[name]


class WeightTests(unittest.TestCase):
    def test_weights_sum_to_one_and_new_parts_share_a_fifth(self):
        self.assertAlmostEqual(sum(QUALITY_WEIGHTS.values()), 1.0)
        self.assertAlmostEqual(sum(QUALITY_WEIGHTS[name] for name in NEW_PARTS), 0.20)

    def test_every_part_is_between_zero_and_one(self):
        source = _design([_text("a", 40, 40), _text("b", 40, 120), _shape("card", 20, 20, 200, 60)])
        for name, value in candidate_score_breakdown(source, source["canvas"], source).items():
            with self.subTest(part=name):
                self.assertTrue(0.0 <= value <= 1.0)


class ReadingOrderTests(unittest.TestCase):
    def test_flipped_reading_order_scores_lower(self):
        source = _design([_text("first", 40, 40), _text("second", 40, 200)])
        kept = _moved(source, "second", y=150)
        flipped = _moved(_moved(source, "first", y=200), "second", y=40)
        self.assertEqual(_part(source, kept, "reading_order"), 1.0)
        self.assertLess(_part(source, flipped, "reading_order"), 1.0)

    def test_order_is_read_on_the_normalised_canvas(self):
        source = _design([_text("left", 20, 20), _text("right", 400, 40)], width=600, height=400)
        banner = deepcopy(source)
        banner["canvas"] = {"width": 1200, "height": 100}
        for element in banner["elements"]:
            element["x"] *= 2
            element["y"] /= 4
        self.assertEqual(_part(source, banner, "reading_order"), 1.0)


class ParentChildCollisionTests(unittest.TestCase):
    def setUp(self):
        self.source = _design([_shape("card", 20, 20, 140, 50, z_index=1), _text("copy", 40, 40)])

    def test_backing_shape_that_stops_holding_its_text_scores_lower(self):
        drifted = _moved(self.source, "card", x=300)
        self.assertEqual(_part(self.source, self.source, "collision"), 1.0)
        self.assertLess(_part(self.source, drifted, "collision"), 1.0)

    def test_shape_newly_drawn_over_text_scores_lower(self):
        source = _design([_shape("chip", 300, 300, 120, 60, z_index=5), _text("copy", 40, 40)])
        covering = _moved(source, "chip", x=40, y=40)
        self.assertLess(_part(source, covering, "collision"), 1.0)

    def test_faint_shape_newly_behind_text_is_harmless(self):
        source = _design([_shape("chip", 300, 300, 120, 60, z_index=0), _text("copy", 40, 40)])
        source["elements"][0]["opacity"] = 0.2
        behind = _moved(source, "chip", x=40, y=40)
        self.assertEqual(_part(source, behind, "collision"), 1.0)

    def test_visible_shape_behind_text_costs_less_than_one_on_top(self):
        below = _design([_shape("chip", 300, 300, 120, 60, z_index=0), _text("copy", 40, 40)])
        above = _design([_shape("chip", 300, 300, 120, 60, z_index=5), _text("copy", 40, 40)])
        behind_score = _part(below, _moved(below, "chip", x=40, y=40), "collision")
        covering_score = _part(above, _moved(above, "chip", x=40, y=40), "collision")
        self.assertLess(behind_score, 1.0)
        self.assertLess(covering_score, behind_score)


class AreaShareTests(unittest.TestCase):
    def test_growth_inside_the_thirty_percent_margin_is_free(self):
        source = _design([_text("a", 40, 40, width=100, height=30), _text("b", 40, 200)])
        within = _moved(source, "a", width=110, height=33)
        self.assertEqual(_part(source, within, "area_share"), 1.0)

    def test_large_change_in_canvas_share_scores_lower(self):
        source = _design([_text("a", 40, 40, width=100, height=30), _text("b", 40, 200)])
        blown_up = _moved(source, "a", width=300, height=90)
        self.assertLess(_part(source, blown_up, "area_share"), 1.0)


class SourceAlignmentTests(unittest.TestCase):
    def test_breaking_an_alignment_from_the_source_scores_lower(self):
        source = _design([_text("a", 40, 40), _text("b", 40, 200), _text("c", 400, 320)])
        broken = _moved(source, "b", x=140)
        self.assertEqual(_part(source, source, "source_alignment"), 1.0)
        self.assertLess(_part(source, broken, "source_alignment"), 1.0)

    def test_a_column_becoming_a_row_still_counts_as_aligned(self):
        source = _design([_text("a", 40, 40), _text("b", 40, 200)])
        row = _moved(source, "b", x=300, y=40)
        self.assertEqual(_part(source, row, "source_alignment"), 1.0)


class SimilarityTests(unittest.TestCase):
    def test_identity_is_fully_similar_and_moving_lowers_it(self):
        source = _design([_text("a", 40, 40), _text("b", 40, 200)])
        moved = _moved(source, "b", x=400, y=300)
        self.assertEqual(_part(source, source, "similarity"), 1.0)
        self.assertLess(_part(source, moved, "similarity"), 1.0)

    def test_exact_rescale_to_a_same_ratio_canvas_is_fully_similar(self):
        source = _design([_text("a", 40, 40), _text("b", 40, 200)])
        double = deepcopy(source)
        double["canvas"] = {"width": 1200, "height": 800}
        for element in double["elements"]:
            for key in ("x", "y", "width", "height", "font_size"):
                element[key] *= 2
        self.assertTrue(math.isclose(_part(source, double, "similarity"), 1.0))


class UnreadableTextIsNotFaithfulTests(unittest.TestCase):
    def test_same_geometry_with_unreadable_text_loses_faithfulness_credit(self):
        source = _design([_text("a", 40, 40, font_size=20), _text("b", 40, 200, font_size=20)])
        unreadable = _moved(source, "b", font_size=3)
        for name in ("similarity", "source_alignment", "area_share"):
            with self.subTest(part=name):
                self.assertEqual(_part(source, source, name), 1.0)
                self.assertLess(_part(source, unreadable, name), 1.0)

    def test_dense_design_in_a_small_ad_keeps_readable_text(self):
        with (FIXTURES_DIR / "dense_12.json").open(encoding="utf-8") as handle:
            data = json.load(handle)
        source = data.get("source", data)
        target = {"width": 300, "height": 250}
        best = max(
            (candidate for _name, candidate in generate_candidates(source, target)),
            key=lambda candidate: score_candidate(source, target, candidate),
        )
        smallest = min(e["font_size"] for e in best["elements"] if e["type"] == "text")
        self.assertGreaterEqual(smallest, 7.0 - 1e-6)


class FaithfulPreserveTests(unittest.TestCase):
    """Same-ratio targets should keep the design, not rebuild it (Phase 6 review)."""

    CASES = (
        ("minimal_2", {"width": 1080, "height": 1080}),
        ("minimal_2", {"width": 2160, "height": 2160}),
        ("style_runs", {"width": 1080, "height": 1350}),
        ("card_5", {"width": 2400, "height": 1800}),
    )

    def test_same_ratio_targets_choose_the_preserved_design(self):
        for name, target in self.CASES:
            with (FIXTURES_DIR / f"{name}.json").open(encoding="utf-8") as handle:
                data = json.load(handle)
            source = data.get("source", data)
            scores = {
                strategy: score_candidate(source, target, candidate)
                for strategy, candidate in generate_candidates(source, target)
            }
            with self.subTest(fixture=name, target=target):
                self.assertEqual(max(scores, key=scores.get), "preserve_and_repair")


if __name__ == "__main__":
    unittest.main()
