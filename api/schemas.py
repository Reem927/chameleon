"""Request validation for the demo API.

Rejects anything the engine or renderer should never see from a browser:
malformed shapes, absurd sizes, and asset ids that could reach outside
brand_kit/assets.
"""

from __future__ import annotations

import math
import re
from typing import Any

MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_CANVAS_SIDE = 10_000
MAX_ELEMENTS = 500
ELEMENT_TYPES = {"text", "image", "shape"}
# A bare file name: no folders, no "..", no URLs.
ASSET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class RequestError(ValueError):
    """Raised with a message that is safe to send back to the client."""


def validate_request(body: Any) -> tuple[dict, dict]:
    """Return ``(source, target_canvas)`` or raise :class:`RequestError`."""
    if not isinstance(body, dict):
        raise RequestError("body must be a JSON object")
    source = body.get("source")
    target = body.get("target_canvas")
    if not isinstance(source, dict):
        raise RequestError("source must be an object")
    _canvas(source.get("canvas"), "source.canvas")
    _canvas(target, "target_canvas")
    elements = source.get("elements")
    if not isinstance(elements, list) or not elements:
        raise RequestError("source.elements must be a non-empty list")
    if len(elements) > MAX_ELEMENTS:
        raise RequestError(f"source.elements has more than {MAX_ELEMENTS} items")
    seen = set()
    for index, element in enumerate(elements):
        label = f"source.elements[{index}]"
        if not isinstance(element, dict):
            raise RequestError(f"{label} must be an object")
        element_id = element.get("id")
        if not isinstance(element_id, str) or not element_id:
            raise RequestError(f"{label}.id must be a non-empty string")
        if element_id in seen:
            raise RequestError(f"duplicate element id {element_id!r}")
        seen.add(element_id)
        if element.get("type") not in ELEMENT_TYPES:
            raise RequestError(f"{label}.type must be one of {sorted(ELEMENT_TYPES)}")
        for key in ("x", "y", "width", "height"):
            if not _finite(element.get(key)):
                raise RequestError(f"{label}.{key} must be a finite number")
        if element["type"] == "image":
            asset_id = element.get("asset_id")
            if not isinstance(asset_id, str) or not ASSET_ID.match(asset_id) or ".." in asset_id:
                raise RequestError(f"{label}.asset_id must be a plain file name")
    return source, target


def _canvas(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise RequestError(f"{label} must be an object")
    for side in ("width", "height"):
        size = value.get(side)
        if not _finite(size) or not 0 < size <= MAX_CANVAS_SIDE:
            raise RequestError(f"{label}.{side} must be a number in (0, {MAX_CANVAS_SIDE}]")


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
