"""Small geometry helpers used by layout generation and validation."""

from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


EPSILON = 1e-6


@dataclass(frozen=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[float, float]:
        return ((self.left + self.right) / 2, (self.top + self.bottom) / 2)


def element_bounds(element: Mapping[str, Any]) -> Bounds:
    """Return the visible axis-aligned bounds after rotation about the center."""
    x = _finite_number(element["x"], "x")
    y = _finite_number(element["y"], "y")
    width = _finite_number(element["width"], "width")
    height = _finite_number(element["height"], "height")
    rotation = _finite_number(element.get("rotation", 0), "rotation")
    if width < 0 or height < 0:
        raise ValueError("width and height must be non-negative")

    radians = math.radians(rotation)
    visible_width = abs(width * math.cos(radians)) + abs(height * math.sin(radians))
    visible_height = abs(width * math.sin(radians)) + abs(height * math.cos(radians))
    center_x = x + width / 2
    center_y = y + height / 2
    return Bounds(
        center_x - visible_width / 2,
        center_y - visible_height / 2,
        center_x + visible_width / 2,
        center_y + visible_height / 2,
    )


def union_bounds(bounds: Iterable[Bounds]) -> Bounds:
    items = list(bounds)
    if not items:
        raise ValueError("at least one bounds value is required")
    return Bounds(
        min(item.left for item in items),
        min(item.top for item in items),
        max(item.right for item in items),
        max(item.bottom for item in items),
    )


def group_bounds(elements: Iterable[Mapping[str, Any]]) -> Bounds:
    return union_bounds(element_bounds(element) for element in elements)


def overlap_area(first: Bounds, second: Bounds) -> float:
    width = max(0.0, min(first.right, second.right) - max(first.left, second.left))
    height = max(0.0, min(first.bottom, second.bottom) - max(first.top, second.top))
    return width * height


def translate_element(element: Mapping[str, Any], dx: float, dy: float) -> dict[str, Any]:
    dx = _finite_number(dx, "dx")
    dy = _finite_number(dy, "dy")
    result = deepcopy(dict(element))
    result["x"] = _finite_number(result["x"], "x") + dx
    result["y"] = _finite_number(result["y"], "y") + dy
    return result


def translate_group(
    elements: Iterable[Mapping[str, Any]], dx: float, dy: float
) -> list[dict[str, Any]]:
    return [translate_element(element, dx, dy) for element in elements]


def scale_element(
    element: Mapping[str, Any],
    scale: float,
    origin: tuple[float, float] = (0.0, 0.0),
) -> dict[str, Any]:
    """Scale geometry uniformly around ``origin`` and scale text size."""
    scale = _finite_number(scale, "scale")
    origin_x = _finite_number(origin[0], "origin x")
    origin_y = _finite_number(origin[1], "origin y")
    if scale < 0:
        raise ValueError("scale must be non-negative")

    result = deepcopy(dict(element))
    result["x"] = origin_x + (_finite_number(result["x"], "x") - origin_x) * scale
    result["y"] = origin_y + (_finite_number(result["y"], "y") - origin_y) * scale
    result["width"] = _finite_number(result["width"], "width") * scale
    result["height"] = _finite_number(result["height"], "height") * scale
    if result.get("type") == "text" and "font_size" in result:
        result["font_size"] = max(1.0, _finite_number(result["font_size"], "font_size") * scale)
    return result


def translation_to_fit(
    bounds: Bounds, canvas: Mapping[str, Any], epsilon: float = EPSILON
) -> tuple[float, float] | None:
    """Return one translation that fits ``bounds``, or ``None`` if impossible."""
    width = _finite_number(canvas["width"], "canvas width")
    height = _finite_number(canvas["height"], "canvas height")
    if bounds.width > width + epsilon or bounds.height > height + epsilon:
        return None

    dx = -bounds.left if bounds.left < -epsilon else 0.0
    if bounds.right + dx > width + epsilon:
        dx += width - (bounds.right + dx)

    dy = -bounds.top if bounds.top < -epsilon else 0.0
    if bounds.bottom + dy > height + epsilon:
        dy += height - (bounds.bottom + dy)
    return dx, dy


def clamp_element(
    element: Mapping[str, Any], canvas: Mapping[str, Any]
) -> dict[str, Any] | None:
    translation = translation_to_fit(element_bounds(element), canvas)
    if translation is None:
        return None
    return translate_element(element, *translation)


def clamp_group(
    elements: Sequence[Mapping[str, Any]], canvas: Mapping[str, Any]
) -> list[dict[str, Any]] | None:
    translation = translation_to_fit(group_bounds(elements), canvas)
    if translation is None:
        return None
    return translate_group(elements, *translation)


def is_on_canvas(
    element: Mapping[str, Any], canvas: Mapping[str, Any], epsilon: float = EPSILON
) -> bool:
    bounds = element_bounds(element)
    width = _finite_number(canvas["width"], "canvas width")
    height = _finite_number(canvas["height"], "canvas height")
    return (
        bounds.left >= -epsilon
        and bounds.top >= -epsilon
        and bounds.right <= width + epsilon
        and bounds.bottom <= height + epsilon
    )


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number
