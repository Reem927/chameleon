"""Hard-gated ranking and its diagnostics (plan Phase 4)."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from engine.layouts import QUALITY_WEIGHTS, generate_candidates, score_candidate
from engine.ranking import family, rank_candidates


ROOT = Path(__file__).resolve().parents[1]


def _sample(name):
    with (ROOT / "input" / name).open(encoding="utf-8") as handle:
        return json.load(handle)


class RankingTests(unittest.TestCase):
    def setUp(self):
        sample = _sample("chameleon_sample_level2_core.json")
        self.source, self.target = sample["source"], sample["target_canvas"]
        self.candidates = generate_candidates(self.source, self.target)

    def test_best_candidate_matches_the_highest_score(self):
        best, diagnostics = rank_candidates(self.source, self.target, self.candidates)
        expected = max(
            (c for _n, c in self.candidates),
            key=lambda c: score_candidate(self.source, self.target, c),
        )
        self.assertEqual(best, expected)
        self.assertEqual(diagnostics["warnings"], [])

    def test_diagnostics_list_every_candidate_with_the_full_breakdown(self):
        _best, diagnostics = rank_candidates(self.source, self.target, self.candidates)
        self.assertEqual(
            [row["name"] for row in diagnostics["candidate_scores"]],
            [name for name, _ in self.candidates],
        )
        for row in diagnostics["candidate_scores"]:
            with self.subTest(candidate=row["name"]):
                if row["legal"]:
                    self.assertEqual(set(row["breakdown"]), set(QUALITY_WEIGHTS))

    def test_illegal_candidates_are_never_chosen(self):
        broken = deepcopy(self.candidates[0][1])
        broken["elements"].pop()
        best, diagnostics = rank_candidates(self.source, self.target, [("broken", broken)])
        self.assertIsNone(best)
        self.assertFalse(diagnostics["candidate_scores"][0]["legal"])
        self.assertTrue(diagnostics["warnings"])

    def test_policy_weight_can_change_the_choice(self):
        _best, plain = rank_candidates(self.source, self.target, self.candidates)
        loser = next(
            row["name"] for row in plain["candidate_scores"]
            if row["legal"] and family(row["name"]) != family(plain["strategy"])
        )
        policies = [{"strategy": family(loser), "weight": 1.0}]
        _best, weighted = rank_candidates(self.source, self.target, self.candidates, policies)
        self.assertEqual(family(weighted["strategy"]), family(loser))

    def test_diagnostics_never_reach_the_design(self):
        best, _diagnostics = rank_candidates(self.source, self.target, self.candidates)
        self.assertEqual(set(best), {"canvas", "elements"})

    def test_family_strips_ratio_and_cleanup_suffixes(self):
        self.assertEqual(family("compact_banner@0.6+clean"), "compact_banner")
        self.assertEqual(family("preserve_and_repair"), "preserve_and_repair")


if __name__ == "__main__":
    unittest.main()
