"""Cleanup pass after a layout is built (plan Phase 10, LayoutRectifier)."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from engine.constraints import validate_candidate
from engine.geometry import element_bounds, overlap_area
from engine.layouts import (
    candidate_score_breakdown,
    flow_layout,
    generate_candidates,
    rectify_candidate,
    score_candidate,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
TARGETS = (
    {"width": 1080, "height": 1080},
    {"width": 1200, "height": 628},
    {"width": 728, "height": 90},
    {"width": 300, "height": 250},
    {"width": 160, "height": 600},
)


def _load_source(name):
    with (FIXTURES_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("source", data)


def _text(element_id, x, y, width=100, height=30, z_index=2):
    return {
        "id": element_id, "type": "text", "x": x, "y": y, "width": width, "height": height,
        "rotation": 0, "content": "Readable text", "font_family": "Solstice Sans",
        "font_size": 20, "line_height": 1.2, "color": "#111111", "z_index": z_index,
    }


def _line(element_id, x, y, width, opacity, z_index=1):
    return {
        "id": element_id, "type": "shape", "shape_type": "line", "fill_color": "#223344",
        "x": x, "y": y, "width": width, "height": 4, "rotation": 0, "z_index": z_index,
        "opacity": opacity,
    }


def _by_id(design):
    return {element["id"]: element for element in design["elements"]}


class DecorationBehindTextScoreTests(unittest.TestCase):
    def test_visible_decoration_newly_behind_text_lowers_collision(self):
        source = {"canvas": {"width": 600, "height": 400},
                  "elements": [_text("copy", 40, 40), _line("rule", 40, 300, 200, 0.5)]}
        cluttered = deepcopy(source)
        _by_id(cluttered)["rule"].update(y=52)
        breakdown = candidate_score_breakdown(source, source["canvas"], cluttered)
        self.assertLess(breakdown["collision"], 1.0)

    def test_faint_glow_behind_text_is_harmless(self):
        source = {"canvas": {"width": 600, "height": 400},
                  "elements": [_text("copy", 40, 40), _line("glow", 40, 300, 200, 0.12)]}
        faint = deepcopy(source)
        _by_id(faint)["glow"].update(y=52)
        breakdown = candidate_score_breakdown(source, source["canvas"], faint)
        self.assertEqual(breakdown["collision"], 1.0)


class RectifyTests(unittest.TestCase):
    def test_visible_decoration_is_moved_off_text(self):
        source = _load_source("layered")
        target = {"width": 1200, "height": 628}
        built = flow_layout(source, target, axis="column", lines=1, graphic_ratio=1.0)
        cleaned = rectify_candidate(source, target, built)
        elements = _by_id(cleaned)
        rule = element_bounds(elements["line_rule"])
        for text_id in ("card_copy", "overlay_title"):
            with self.subTest(text=text_id):
                self.assertEqual(overlap_area(rule, element_bounds(elements[text_id])), 0.0)

    def test_source_aligned_units_that_drifted_slightly_are_snapped(self):
        source = {"canvas": {"width": 600, "height": 400},
                  "elements": [_text("a", 40, 40), _text("b", 40, 200)]}
        drifted = deepcopy(source)
        _by_id(drifted)["b"].update(x=45)
        cleaned = rectify_candidate(source, source["canvas"], drifted)
        self.assertEqual(_by_id(cleaned)["b"]["x"], _by_id(cleaned)["a"]["x"])

    def test_new_unit_overlap_is_pushed_apart(self):
        source = {"canvas": {"width": 600, "height": 400},
                  "elements": [_text("a", 40, 40), _text("b", 300, 200)]}
        crowded = deepcopy(source)
        _by_id(crowded)["b"].update(x=60, y=50)
        cleaned = rectify_candidate(source, source["canvas"], crowded)
        elements = _by_id(cleaned)
        self.assertEqual(
            overlap_area(element_bounds(elements["a"]), element_bounds(elements["b"])), 0.0
        )

    def test_cleanup_never_breaks_hard_rules_or_lowers_the_score(self):
        for name in ("layered", "dense_12", "huge_25", "rotated", "card_5"):
            source = _load_source(name)
            for target in TARGETS:
                for strategy, candidate in generate_candidates(source, target):
                    # resize() drops invalid layouts before ranking; cleanup
                    # only promises to keep a valid layout valid.
                    if strategy.endswith("+clean") or validate_candidate(source, target, candidate):
                        continue
                    cleaned = rectify_candidate(source, target, candidate)
                    with self.subTest(fixture=name, target=target, strategy=strategy):
                        self.assertEqual(validate_candidate(source, target, cleaned), [])
                        self.assertGreaterEqual(
                            score_candidate(source, target, cleaned) + 1e-9,
                            score_candidate(source, target, candidate),
                        )

    def test_cleanup_only_moves_elements(self):
        source = _load_source("layered")
        target = {"width": 1200, "height": 628}
        built = flow_layout(source, target, axis="column", lines=1, graphic_ratio=1.0)
        cleaned = rectify_candidate(source, target, built)
        before, after = _by_id(built), _by_id(cleaned)
        for element_id, element in after.items():
            with self.subTest(element=element_id):
                for key, value in element.items():
                    if key not in ("x", "y"):
                        self.assertEqual(value, before[element_id][key])

    def test_cleanup_is_deterministic_and_does_not_mutate_its_input(self):
        source = _load_source("layered")
        target = {"width": 1200, "height": 628}
        built = flow_layout(source, target, axis="column", lines=1, graphic_ratio=1.0)
        snapshot = deepcopy(built)
        first = rectify_candidate(source, target, built)
        second = rectify_candidate(source, target, built)
        self.assertEqual(first, second)
        self.assertEqual(built, snapshot)

    def test_cleaned_variants_are_offered_to_the_ranker(self):
        source = _load_source("layered")
        names = [name for name, _ in generate_candidates(source, {"width": 1200, "height": 628})]
        self.assertTrue(any(name.endswith("+clean") for name in names))


if __name__ == "__main__":
    unittest.main()
