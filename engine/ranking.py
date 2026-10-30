"""Hard-gated ranking of complete candidates (plan Phase 4).

Reuses the one scorer in engine/layouts.py. Diagnostics are for the demo API
and tests only and never reach the output JSON.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from engine.constraints import validate_candidate
from engine.layouts import QUALITY_WEIGHTS, candidate_score_breakdown


def rank_candidates(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    candidates: Iterable[tuple[str, Mapping[str, Any]]],
    policies: Sequence[Mapping[str, Any]] = (),
) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    """Return the best legal candidate (or None) and diagnostics.

    The total is the weighted score plus the policy weight of the
    candidate's layout family. Ties keep the earlier candidate.
    """
    weights = {policy["strategy"]: float(policy.get("weight", 0.0)) for policy in policies}
    best = None
    best_total = float("-inf")
    rows = []
    for name, candidate in candidates:
        problems = validate_candidate(source, target_canvas, candidate)
        row: dict[str, Any] = {"name": name, "legal": not problems}
        if problems:
            row["problems"] = problems
        else:
            breakdown = candidate_score_breakdown(source, target_canvas, candidate)
            weight = weights.get(family(name), 0.0)
            total = sum(breakdown[part] * QUALITY_WEIGHTS[part] for part in QUALITY_WEIGHTS) + weight
            row.update(weight=weight, total=total, breakdown=breakdown)
            if total > best_total:
                best, best_total = candidate, total
        rows.append(row)
    chosen = next((row["name"] for row in rows if row.get("total") == best_total), None)
    diagnostics = {
        "strategy": chosen,
        "candidate_scores": rows,
        "policies": [dict(policy) for policy in policies],
        "warnings": [] if best is not None else ["no legal candidate; caller must fall back"],
    }
    return best, diagnostics


def family(name: str) -> str:
    """Layout family of a candidate name, e.g. ``compact_banner@0.6+clean``."""
    return name.split("+")[0].split("@")[0]
