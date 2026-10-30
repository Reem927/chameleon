"""Facts the decision policy reads from a design and its target (plan Phase 4).

Only geometry and element types are used: never ids, file names, colours or
text meaning, so the same rules apply to any design.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from engine.layouts import content_units


def extract_features(source: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> dict[str, float]:
    """Return a flat, deterministic feature dictionary."""
    source_canvas = source["canvas"]
    source_ratio = source_canvas["width"] / source_canvas["height"]
    target_ratio = target_canvas["width"] / target_canvas["height"]
    units = content_units(source)
    elements = source["elements"]
    texts = [element for element in elements if element.get("type") == "text"]
    return {
        "aspect_change": math.log(target_ratio / source_ratio),
        "aspect_closeness": min(source_ratio, target_ratio) / max(source_ratio, target_ratio),
        "width_scale": target_canvas["width"] / source_canvas["width"],
        "height_scale": target_canvas["height"] / source_canvas["height"],
        "content_units": float(len(units)),
        "text_units": float(sum(any(e.get("type") == "text" for e in unit) for unit in units)),
        "groups": float(len({e["group_id"] for e in elements if e.get("group_id")})),
        "rotated": float(sum(1 for e in elements if float(e.get("rotation", 0)) % 360 != 0)),
        "text_characters": float(sum(len(str(e.get("content", ""))) for e in texts)),
    }
