import json
import unittest
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from engine.constraints import validate_candidate
from engine.layouts import generate_candidates, score_candidate
from engine.resize import resize


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "near_ratio": ROOT / "input" / "chameleon_sample_level1_warmup.json",
    "wide": ROOT / "input" / "chameleon_sample_level2_core.json",
    "extreme_short": ROOT / "input" / "chameleon_sample_level3_advanced.json",
}


def _load_sample(name):
    with SAMPLES[name].open(encoding="utf-8") as handle:
        return json.load(handle)


def _independent_xy_stretch(source, target_canvas):
    result = deepcopy(source)
    scale_x = target_canvas["width"] / source["canvas"]["width"]
    scale_y = target_canvas["height"] / source["canvas"]["height"]
    result["canvas"] = deepcopy(target_canvas)
    for element in result["elements"]:
        element["x"] *= scale_x
        element["width"] *= scale_x
        element["y"] *= scale_y
        element["height"] *= scale_y
    return result


class ResizeTests(unittest.TestCase):
    def test_official_samples_are_valid_deterministic_and_do_not_mutate_source(self):
        for name in SAMPLES:
            with self.subTest(sample=name):
                sample = _load_sample(name)
                source_before = deepcopy(sample["source"])

                first = resize(sample["source"], sample["target_canvas"])
                second = resize(sample["source"], sample["target_canvas"])

                self.assertEqual(first, second)
                self.assertEqual(sample["source"], source_before)
                self.assertEqual(
                    validate_candidate(sample["source"], sample["target_canvas"], first),
                    [],
                )

    def test_official_samples_choose_the_expected_highest_scoring_candidate(self):
        expected = {
            "near_ratio": "preserve_and_repair",
            "wide": "horizontal_split",
            "extreme_short": "compact_banner",
        }
        for name, expected_strategy in expected.items():
            with self.subTest(sample=name):
                sample = _load_sample(name)
                candidates = dict(
                    generate_candidates(sample["source"], sample["target_canvas"])
                )

                best_strategy = max(
                    candidates,
                    key=lambda strategy: score_candidate(
                        sample["source"], sample["target_canvas"], candidates[strategy]
                    ),
                )
                self.assertEqual(best_strategy.split("@")[0], expected_strategy)
                self.assertEqual(
                    resize(sample["source"], sample["target_canvas"]),
                    candidates[best_strategy],
                )

    def test_official_outputs_are_not_the_old_independent_axis_stretch(self):
        for name in SAMPLES:
            with self.subTest(sample=name):
                sample = _load_sample(name)
                old_output = _independent_xy_stretch(
                    sample["source"], sample["target_canvas"]
                )

                self.assertNotEqual(
                    resize(sample["source"], sample["target_canvas"]), old_output
                )

    def test_official_outputs_preserve_ids_fields_and_image_ratios(self):
        for name in SAMPLES:
            with self.subTest(sample=name):
                sample = _load_sample(name)
                output = resize(sample["source"], sample["target_canvas"])
                source_by_id = {
                    element["id"]: element for element in sample["source"]["elements"]
                }
                output_by_id = {
                    element["id"]: element for element in output["elements"]
                }

                self.assertEqual(list(output_by_id), list(source_by_id))
                for element_id, source_element in source_by_id.items():
                    output_element = output_by_id[element_id]
                    self.assertEqual(set(output_element), set(source_element))
                    if (
                        source_element["type"] == "image"
                        and source_element.get("fit", "contain") != "cover"
                    ):
                        source_ratio = source_element["width"] / source_element["height"]
                        output_ratio = output_element["width"] / output_element["height"]
                        self.assertLessEqual(abs(output_ratio / source_ratio - 1), 0.05)

    def test_group_members_keep_one_shared_internal_transform(self):
        for name in SAMPLES:
            sample = _load_sample(name)
            output = resize(sample["source"], sample["target_canvas"])
            output_by_id = {element["id"]: element for element in output["elements"]}
            groups = defaultdict(list)
            for element in sample["source"]["elements"]:
                if element.get("group_id"):
                    groups[element["group_id"]].append(element)

            for group_id, source_group in groups.items():
                with self.subTest(sample=name, group=group_id):
                    anchor = source_group[0]
                    output_anchor = output_by_id[anchor["id"]]
                    scale = output_anchor["width"] / anchor["width"]
                    for source_element in source_group:
                        output_element = output_by_id[source_element["id"]]
                        self.assertAlmostEqual(
                            output_element["width"], source_element["width"] * scale
                        )
                        self.assertAlmostEqual(
                            output_element["height"], source_element["height"] * scale
                        )
                        self.assertAlmostEqual(
                            output_element["x"] - output_anchor["x"],
                            (source_element["x"] - anchor["x"]) * scale,
                        )
                        self.assertAlmostEqual(
                            output_element["y"] - output_anchor["y"],
                            (source_element["y"] - anchor["y"]) * scale,
                        )

    def test_tall_target_returns_the_highest_scoring_legal_candidate(self):
        sample = _load_sample("near_ratio")
        target_canvas = {"width": 400, "height": 1600}
        output = resize(sample["source"], target_canvas)
        candidates = [
            candidate
            for _strategy, candidate in generate_candidates(sample["source"], target_canvas)
            if not validate_candidate(sample["source"], target_canvas, candidate)
        ]
        best = max(
            candidates,
            key=lambda candidate: score_candidate(sample["source"], target_canvas, candidate),
        )

        self.assertEqual(output, best)
        self.assertEqual(
            validate_candidate(sample["source"], target_canvas, output), []
        )


if __name__ == "__main__":
    unittest.main()
