import json
import unittest
from copy import deepcopy
from pathlib import Path

from engine.layouts import (
    candidate_score_breakdown,
    generate_candidates,
    score_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "chameleon_sample_level1_warmup.json": "preserve_and_repair",
    "chameleon_sample_level2_core.json": "horizontal_split",
    "chameleon_sample_level3_advanced.json": "compact_banner",
}


def _text(element_id, x, y, width=100, height=30, font_size=20, group_id=None):
    element = {
        "id": element_id,
        "type": "text",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "rotation": 0,
        "content": "Readable text",
        "font_size": font_size,
        "line_height": 1.2,
    }
    if group_id:
        element["group_id"] = group_id
    return element


def _design(elements, width=600, height=300):
    return {"canvas": {"width": width, "height": height}, "elements": elements}


class QualityScoreTests(unittest.TestCase):
    def test_official_samples_rank_expected_strategy(self):
        for filename, expected in SAMPLES.items():
            with self.subTest(sample=filename):
                with (ROOT / "input" / filename).open(encoding="utf-8") as handle:
                    sample = json.load(handle)
                scores = [
                    (
                        score_candidate(
                            sample["source"], sample["target_canvas"], candidate
                        ),
                        name,
                    )
                    for name, candidate in generate_candidates(
                        sample["source"], sample["target_canvas"]
                    )
                ]

                best = max(scores, key=lambda item: item[0])[1]
                self.assertEqual(best.split("@")[0], expected)

    def test_new_unit_overlap_lowers_score_but_group_overlap_is_not_a_collision(self):
        source = _design(
            [
                _text("group-a", 40, 40, group_id="group"),
                _text("group-b", 80, 50, group_id="group"),
                _text("other", 350, 40),
            ]
        )
        clean = deepcopy(source)
        separate_overlap = deepcopy(source)
        separate_overlap["elements"][2].update(x=50, y=45)
        within_group_overlap = deepcopy(source)
        within_group_overlap["elements"][1].update(x=40, y=40)

        clean_collision = candidate_score_breakdown(
            source, source["canvas"], clean
        )["collision"]
        overlap_collision = candidate_score_breakdown(
            source, source["canvas"], separate_overlap
        )["collision"]
        grouped_collision = candidate_score_breakdown(
            source, source["canvas"], within_group_overlap
        )["collision"]

        self.assertLess(overlap_collision, clean_collision)
        self.assertEqual(grouped_collision, clean_collision)
        self.assertLess(
            score_candidate(source, source["canvas"], separate_overlap),
            score_candidate(source, source["canvas"], clean),
        )

    def test_larger_readable_text_scores_better(self):
        source = _design([_text("copy", 100, 100)])
        small = deepcopy(source)
        small["elements"][0].update(width=50, height=10, font_size=5)
        readable = deepcopy(source)
        readable["elements"][0].update(width=150, height=35, font_size=18)

        small_text = candidate_score_breakdown(source, source["canvas"], small)["text"]
        readable_text = candidate_score_breakdown(source, source["canvas"], readable)[
            "text"
        ]

        self.assertGreater(readable_text, small_text)

    def test_shared_unit_scale_preserves_hierarchy_better_than_distortion(self):
        source = _design(
            [_text("headline", 40, 40, 200, 60), _text("caption", 300, 80, 80, 20)]
        )
        preserved = deepcopy(source)
        for element in preserved["elements"]:
            element.update(
                x=element["x"] * 0.5,
                y=element["y"] * 0.5,
                width=element["width"] * 0.5,
                height=element["height"] * 0.5,
                font_size=element["font_size"] * 0.5,
            )
        distorted = deepcopy(preserved)
        distorted["elements"][1].update(width=16, height=4, font_size=2)

        preserved_hierarchy = candidate_score_breakdown(
            source, source["canvas"], preserved
        )["hierarchy"]
        distorted_hierarchy = candidate_score_breakdown(
            source, source["canvas"], distorted
        )["hierarchy"]

        self.assertGreater(preserved_hierarchy, distorted_hierarchy)

    def test_broken_group_scores_lower(self):
        source = _design(
            [
                _text("group-a", 100, 100, group_id="group"),
                _text("group-b", 220, 100, group_id="group"),
            ]
        )
        coherent = deepcopy(source)
        broken = deepcopy(source)
        broken["elements"][1].update(x=100, y=100)

        coherent_score = candidate_score_breakdown(
            source, source["canvas"], coherent
        )["group_cohesion"]
        broken_score = candidate_score_breakdown(source, source["canvas"], broken)[
            "group_cohesion"
        ]

        self.assertGreater(coherent_score, broken_score)
        self.assertGreater(
            score_candidate(source, source["canvas"], coherent),
            score_candidate(source, source["canvas"], broken),
        )

    def test_centered_useful_arrangement_beats_tiny_corner_arrangement(self):
        source = _design(
            [_text("one", 80, 120), _text("two", 250, 120), _text("three", 420, 120)]
        )
        useful = deepcopy(source)
        tiny_corner = deepcopy(source)
        for index, element in enumerate(tiny_corner["elements"]):
            element.update(
                x=5 + index * 12,
                y=5,
                width=10,
                height=3,
                font_size=2,
            )

        useful_parts = candidate_score_breakdown(source, source["canvas"], useful)
        tiny_parts = candidate_score_breakdown(source, source["canvas"], tiny_corner)

        self.assertGreater(useful_parts["canvas_use"], tiny_parts["canvas_use"])
        self.assertGreater(useful_parts["balance_spacing"], tiny_parts["balance_spacing"])
        self.assertGreater(
            score_candidate(source, source["canvas"], useful),
            score_candidate(source, source["canvas"], tiny_corner),
        )

    def test_scoring_is_deterministic_and_does_not_mutate_inputs(self):
        source = _design([_text("one", 50, 50), _text("two", 300, 150)])
        candidate = deepcopy(source)
        source_before = deepcopy(source)
        candidate_before = deepcopy(candidate)

        first = score_candidate(source, source["canvas"], candidate)
        second = score_candidate(source, source["canvas"], candidate)

        self.assertEqual(first, second)
        self.assertEqual(source, source_before)
        self.assertEqual(candidate, candidate_before)


if __name__ == "__main__":
    unittest.main()
