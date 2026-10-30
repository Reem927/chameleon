"""Decision policy and its features (plan Phase 4, D-024)."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

from engine import resize as resize_module
from engine.decision_features import extract_features
from engine.decision_policy import DENSE_UNITS, suggest_policies
from engine.layouts import generate_candidates
from engine.ranking import family, rank_candidates


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_source(name):
    with (FIXTURES_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("source", data)


def _chosen_family(source, target):
    policies = suggest_policies(source, target)
    _best, diagnostics = rank_candidates(
        source, target, generate_candidates(source, target, policies), policies
    )
    return family(diagnostics["strategy"])


class FeatureTests(unittest.TestCase):
    def test_features_ignore_ids_and_do_not_mutate_input(self):
        source = _load_source("dense_12")
        snapshot = deepcopy(source)
        renamed = deepcopy(source)
        for index, element in enumerate(renamed["elements"]):
            element["id"] = f"element_{index}"
            if element.get("group_id"):
                element["group_id"] = "g_" + element["group_id"][::-1]
        target = {"width": 300, "height": 250}
        self.assertEqual(extract_features(source, target), extract_features(renamed, target))
        self.assertEqual(source, snapshot)

    def test_aspect_features_describe_the_shape_change(self):
        features = extract_features(_load_source("minimal_2"), {"width": 1080, "height": 1080})
        self.assertEqual(features["aspect_change"], 0.0)
        self.assertEqual(features["aspect_closeness"], 1.0)


class PolicyTests(unittest.TestCase):
    def test_dense_designs_get_more_lines_and_sparse_designs_get_nothing(self):
        target = {"width": 300, "height": 250}
        dense = suggest_policies(_load_source("huge_25"), target)
        self.assertGreaterEqual(extract_features(_load_source("huge_25"), target)["content_units"], DENSE_UNITS)
        self.assertEqual([p["strategy"] for p in dense], ["two_columns", "three_rows"])
        self.assertEqual(suggest_policies(_load_source("minimal_2"), target), [])

    def test_policy_is_deterministic(self):
        source = _load_source("huge_25")
        target = {"width": 1200, "height": 628}
        self.assertEqual(suggest_policies(source, target), suggest_policies(source, target))

    def test_policy_changes_the_chosen_layout_in_distinct_scenarios(self):
        # PLAN.md Gate B: the decision model must change the choice on at
        # least two general scenarios, not always pick a fixed layout.
        source = _load_source("huge_25")
        for target, expected in (
            ({"width": 300, "height": 250}, "two_columns"),
            ({"width": 1200, "height": 628}, "three_rows"),
        ):
            with self.subTest(target=target):
                self.assertEqual(_chosen_family(source, target), expected)

    def test_policy_only_adds_layouts_never_removes_them(self):
        source = _load_source("huge_25")
        target = {"width": 300, "height": 250}
        base = [name for name, _ in generate_candidates(source, target)]
        with_policy = [
            name for name, _ in generate_candidates(source, target, suggest_policies(source, target))
        ]
        self.assertTrue(set(base) <= set(with_policy))

    def test_resize_falls_back_to_no_policy_when_the_policy_fails(self):
        source = _load_source("huge_25")
        target = {"width": 300, "height": 250}
        with mock.patch.object(resize_module, "suggest_policies", side_effect=RuntimeError("boom")):
            broken = resize_module.resize(source, target)
        with mock.patch.object(resize_module, "suggest_policies", return_value=[]):
            without = resize_module.resize(source, target)
        self.assertEqual(broken, without)


if __name__ == "__main__":
    unittest.main()
