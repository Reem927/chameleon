"""Local decision policy: which layouts to try and how to weight them (plan Phase 4).

A small set of readable rules, not a trained model: the approved-model list
and size limit are unknown (D-022). Policies may only add layout families and
add a weight to a family's score; they never remove a layout (D-024). Every
rule must be backed by the fixture report (see docs/model-notes.md).
"""

from __future__ import annotations

from typing import Any, Mapping

from engine.decision_features import extract_features


# ORC Layout's balanced flow: a design with this many content units reads
# better wrapped into more lines. Measured on the fixtures: designs with 11
# and 18 units gain 3-5px of text; designs with 2-5 units lose size.
DENSE_UNITS = 8


def suggest_policies(source: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> list[dict]:
    """Return policy hints in a stable order; never design JSON.

    Each hint is ``{"strategy": name, "weight": float, "reason": str}``.
    ``strategy`` names a layout family; an extra family is only built when a
    hint names it. ``weight`` is added to that family's score.
    """
    features = extract_features(source, target_canvas)
    policies = []
    if features["content_units"] >= DENSE_UNITS:
        reason = f"{int(features['content_units'])} content units: try more lines (balanced flow)"
        policies.append({"strategy": "two_columns", "weight": 0.0, "reason": reason})
        policies.append({"strategy": "three_rows", "weight": 0.0, "reason": reason})
    return policies
