"""Deterministic layout candidates for the Chameleon resize engine."""

from __future__ import annotations

import math
from copy import deepcopy
from itertools import combinations
from statistics import fmean, pstdev
from typing import Any, Iterable, Mapping, Sequence

from engine.geometry import (
    Bounds,
    clamp_element,
    element_bounds,
    group_bounds,
    overlap_area,
    scale_element,
    translate_element,
    translate_group,
)


Design = dict[str, Any]
Unit = list[Mapping[str, Any]]

QUALITY_WEIGHTS = {
    "collision": 0.24,
    "text": 0.24,
    "hierarchy": 0.18,
    "canvas_use": 0.14,
    "alignment": 0.08,
    "balance_spacing": 0.06,
    "group_cohesion": 0.06,
}


def generate_candidates(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> list[tuple[str, Design]]:
    """Return complete candidates in a stable order."""
    return [
        ("preserve_and_repair", preserve_and_repair(source, target_canvas)),
        ("vertical_stack", vertical_stack(source, target_canvas)),
        ("horizontal_split", horizontal_split(source, target_canvas)),
        ("compact_banner", compact_banner(source, target_canvas)),
    ]


def strategy_order(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> list[str]:
    """Choose which general strategy to try first for the target shape."""
    source_ratio = source["canvas"]["width"] / source["canvas"]["height"]
    target_ratio = target_canvas["width"] / target_canvas["height"]
    unit_count = len(_content_units(source))

    if target_canvas["height"] <= 120 or (target_ratio >= 5 and unit_count > 6):
        first = "compact_banner"
    elif target_ratio > source_ratio * 1.5:
        first = "horizontal_split"
    elif target_ratio < source_ratio / 1.5:
        first = "vertical_stack"
    else:
        first = "preserve_and_repair"
    return [
        first,
        *(
            name
            for name in (
                "preserve_and_repair",
                "horizontal_split",
                "vertical_stack",
                "compact_banner",
            )
            if name != first
        ),
    ]


def preserve_and_repair(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> Design:
    """Fit the full foreground as one composition without stretching it."""
    backgrounds, decorations, content = _parts(source)
    foreground = [element for unit in content for element in unit] + decorations
    margin = _canvas_margin(target_canvas)
    safe_box = Bounds(
        margin,
        margin,
        target_canvas["width"] - margin,
        target_canvas["height"] - margin,
    )
    transformed = _background_map(backgrounds, target_canvas)
    if foreground:
        transformed.update(_fit_unit_to_box(foreground, safe_box))
    return _assemble(source, target_canvas, transformed)


def vertical_stack(source: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> Design:
    backgrounds, decorations, units = _parts(source)
    units.sort(key=lambda unit: (group_bounds(unit).center[0], group_bounds(unit).center[1]))
    transformed = _background_map(backgrounds, target_canvas)
    transformed.update(_place_decorations(decorations, source["canvas"], target_canvas))
    transformed.update(_pack_grid(units, target_canvas, rows=max(1, len(units)), columns=1))
    return _assemble(source, target_canvas, transformed)


def horizontal_split(source: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> Design:
    backgrounds, decorations, units = _parts(source)
    units.sort(key=lambda unit: (group_bounds(unit).center[1], group_bounds(unit).center[0]))
    transformed = _background_map(backgrounds, target_canvas)
    transformed.update(_place_decorations(decorations, source["canvas"], target_canvas))
    transformed.update(_pack_grid(units, target_canvas, rows=1, columns=max(1, len(units))))
    return _assemble(source, target_canvas, transformed)


def compact_banner(source: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> Design:
    backgrounds, decorations, units = _parts(source)
    units.sort(key=lambda unit: (group_bounds(unit).center[1], group_bounds(unit).center[0]))
    rows = 2 if len(units) > 8 else 1
    columns = max(1, math.ceil(len(units) / rows))
    transformed = _background_map(backgrounds, target_canvas)
    transformed.update(_place_decorations(decorations, source["canvas"], target_canvas))
    transformed.update(_pack_grid(units, target_canvas, rows=rows, columns=columns))
    return _assemble(source, target_canvas, transformed)


def safe_fallback(source: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> Design:
    """Small public fallback kept separate so ``resize`` can always call it."""
    return preserve_and_repair(source, target_canvas)


def score_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> float:
    """Return a deterministic 0..1 visual-quality score for a legal candidate."""
    breakdown = candidate_score_breakdown(source, target_canvas, candidate)
    return sum(breakdown[name] * weight for name, weight in QUALITY_WEIGHTS.items())


def candidate_score_breakdown(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, float]:
    """Expose local score parts for tests and development logs, never output JSON."""
    source_units, output_units = _matching_content_units(source, candidate)
    return {
        "collision": _collision_quality(source_units, output_units),
        "text": _text_quality(output_units),
        "hierarchy": _hierarchy_quality(source_units, output_units),
        "canvas_use": _canvas_use_quality(output_units, target_canvas),
        "alignment": _alignment_quality(output_units, target_canvas),
        "balance_spacing": _balance_spacing_quality(output_units, target_canvas),
        "group_cohesion": _group_cohesion_quality(source, candidate, target_canvas),
    }


def _parts(source: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[Unit]]:
    backgrounds = [
        element for element in source["elements"] if _is_background(element, source["canvas"])
    ]
    background_ids = {element["id"] for element in backgrounds}
    decorations = [
        element
        for element in source["elements"]
        if element["id"] not in background_ids
        and element["type"] == "shape"
        and not element.get("group_id")
    ]
    decoration_ids = {element["id"] for element in decorations}
    units = _content_units(source, background_ids | decoration_ids)
    return backgrounds, decorations, units


def _content_units(
    source: Mapping[str, Any], excluded_ids: set[str] | None = None
) -> list[Unit]:
    excluded_ids = excluded_ids or {
        element["id"]
        for element in source["elements"]
        if _is_background(element, source["canvas"])
        or (element["type"] == "shape" and not element.get("group_id"))
    }
    units: list[Unit] = []
    grouped: dict[str, Unit] = {}
    for element in source["elements"]:
        if element["id"] in excluded_ids:
            continue
        group_id = element.get("group_id")
        if group_id:
            if group_id not in grouped:
                grouped[group_id] = []
                units.append(grouped[group_id])
            grouped[group_id].append(element)
        else:
            units.append([element])
    return units


def _matching_content_units(
    source: Mapping[str, Any], candidate: Mapping[str, Any]
) -> tuple[list[Unit], list[Unit]]:
    source_units = _content_units(source)
    output_by_id = {element["id"]: element for element in candidate["elements"]}
    output_units = [
        [output_by_id[element["id"]] for element in unit] for unit in source_units
    ]
    return source_units, output_units


def _collision_quality(source_units: Sequence[Unit], output_units: Sequence[Unit]) -> float:
    new_overlaps = []
    for (source_first, source_second), (output_first, output_second) in zip(
        combinations(source_units, 2), combinations(output_units, 2)
    ):
        source_overlap = _unit_overlap_ratio(source_first, source_second)
        output_overlap = _unit_overlap_ratio(output_first, output_second)
        new_overlaps.append(max(0.0, output_overlap - source_overlap))
    if not new_overlaps:
        return 1.0
    penalty = 0.7 * max(new_overlaps) + 0.3 * fmean(new_overlaps)
    return 1.0 - _clamp01(penalty)


def _unit_overlap_ratio(first: Unit, second: Unit) -> float:
    first_bounds = group_bounds(first)
    second_bounds = group_bounds(second)
    smaller_area = min(_bounds_area(first_bounds), _bounds_area(second_bounds))
    if smaller_area <= 0:
        return 0.0
    return overlap_area(first_bounds, second_bounds) / smaller_area


def _text_quality(units: Sequence[Unit]) -> float:
    scores = []
    for element in (element for unit in units for element in unit):
        if element.get("type") != "text":
            continue
        font_size = float(element["font_size"])
        line_height = float(element.get("line_height", 1.2))
        columns = max(1.0, float(element["width"]) / max(1.0, font_size * 0.55))
        lines = max(1.0, float(element["height"]) / max(1.0, font_size * line_height))
        capacity = columns * lines
        content_length = max(1, len(element.get("content", "")))
        legibility = min(1.0, font_size / 12.0)
        fit = min(1.0, capacity / content_length)
        scores.append(0.7 * legibility + 0.3 * fit)
    return fmean(scores) if scores else 1.0


def _hierarchy_quality(source_units: Sequence[Unit], output_units: Sequence[Unit]) -> float:
    scales = []
    for source_unit, output_unit in zip(source_units, output_units):
        source_area = _bounds_area(group_bounds(source_unit))
        output_area = _bounds_area(group_bounds(output_unit))
        if source_area > 0 and output_area > 0:
            scales.append(math.sqrt(output_area / source_area))
    errors = [abs(math.log(first / second)) for first, second in combinations(scales, 2)]
    return math.exp(-fmean(errors)) if errors else 1.0


def _canvas_use_quality(units: Sequence[Unit], canvas: Mapping[str, Any]) -> float:
    if not units:
        return 1.0
    bounds = [group_bounds(unit) for unit in units]
    content_bounds = Bounds(
        min(item.left for item in bounds),
        min(item.top for item in bounds),
        max(item.right for item in bounds),
        max(item.bottom for item in bounds),
    )
    canvas_area = float(canvas["width"] * canvas["height"])
    spread = _clamp01(_bounds_area(content_bounds) / canvas_area)
    occupied = min(1.0, sum(_bounds_area(item) for item in bounds) / canvas_area / 0.35)
    return math.sqrt(spread * occupied)


def _alignment_quality(units: Sequence[Unit], canvas: Mapping[str, Any]) -> float:
    if len(units) <= 1:
        return 1.0
    bounds = [group_bounds(unit) for unit in units]
    tolerance_x = max(2.0, float(canvas["width"]) * 0.01)
    tolerance_y = max(2.0, float(canvas["height"]) * 0.01)
    aligned = 0
    for index, first in enumerate(bounds):
        first_x = (first.left, first.center[0], first.right)
        first_y = (first.top, first.center[1], first.bottom)
        if any(
            min(abs(a - b) for a in first_x for b in (other.left, other.center[0], other.right))
            <= tolerance_x
            or min(abs(a - b) for a in first_y for b in (other.top, other.center[1], other.bottom))
            <= tolerance_y
            for other_index, other in enumerate(bounds)
            if other_index != index
        ):
            aligned += 1
    return aligned / len(bounds)


def _balance_spacing_quality(units: Sequence[Unit], canvas: Mapping[str, Any]) -> float:
    if not units:
        return 1.0
    bounds = [group_bounds(unit) for unit in units]
    content_bounds = Bounds(
        min(item.left for item in bounds),
        min(item.top for item in bounds),
        max(item.right for item in bounds),
        max(item.bottom for item in bounds),
    )
    canvas_center = (float(canvas["width"]) / 2, float(canvas["height"]) / 2)
    distance = math.dist(content_bounds.center, canvas_center)
    half_diagonal = math.hypot(float(canvas["width"]), float(canvas["height"])) / 2
    balance = 1.0 - min(1.0, distance / max(half_diagonal, 1e-9))

    nearest_gaps = []
    for index, first in enumerate(bounds):
        gaps = [
            _bounds_gap(first, second)
            for other_index, second in enumerate(bounds)
            if other_index != index and _bounds_gap(first, second) > 1e-6
        ]
        if gaps:
            nearest_gaps.append(min(gaps))
    if len(nearest_gaps) <= 2 or fmean(nearest_gaps) <= 1e-9:
        spacing = 1.0
    else:
        spacing = 1.0 / (1.0 + pstdev(nearest_gaps) / fmean(nearest_gaps))
    return 0.6 * balance + 0.4 * spacing


def _group_cohesion_quality(
    source: Mapping[str, Any],
    candidate: Mapping[str, Any],
    canvas: Mapping[str, Any],
) -> float:
    output_by_id = {element["id"]: element for element in candidate["elements"]}
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for element in source["elements"]:
        if element.get("group_id"):
            groups.setdefault(element["group_id"], []).append(element)
    scores = []
    diagonal = max(1.0, math.hypot(float(canvas["width"]), float(canvas["height"])))
    for source_group in groups.values():
        if len(source_group) < 2:
            continue
        anchor = source_group[0]
        output_anchor = output_by_id[anchor["id"]]
        if anchor["width"] > 0:
            scale = output_anchor["width"] / anchor["width"]
        elif anchor["height"] > 0:
            scale = output_anchor["height"] / anchor["height"]
        else:
            continue
        offset_x = output_anchor["x"] - anchor["x"] * scale
        offset_y = output_anchor["y"] - anchor["y"] * scale
        errors = []
        for source_element in source_group:
            output_element = output_by_id[source_element["id"]]
            errors.extend(
                [
                    abs(output_element["x"] - (source_element["x"] * scale + offset_x)) / diagonal,
                    abs(output_element["y"] - (source_element["y"] * scale + offset_y)) / diagonal,
                    abs(output_element["width"] - source_element["width"] * scale) / diagonal,
                    abs(output_element["height"] - source_element["height"] * scale) / diagonal,
                ]
            )
        scores.append(math.exp(-4 * fmean(errors)))
    return fmean(scores) if scores else 1.0


def _bounds_area(bounds: Bounds) -> float:
    return max(0.0, bounds.width) * max(0.0, bounds.height)


def _bounds_gap(first: Bounds, second: Bounds) -> float:
    horizontal = max(first.left - second.right, second.left - first.right, 0.0)
    vertical = max(first.top - second.bottom, second.top - first.bottom, 0.0)
    return math.hypot(horizontal, vertical)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _is_background(element: Mapping[str, Any], canvas: Mapping[str, Any]) -> bool:
    if element.get("type") != "image" or element.get("fit") != "cover":
        return False
    rotation = float(element.get("rotation", 0)) % 360
    return (
        min(rotation, 360 - rotation) <= 1e-6
        and element["x"] <= 0
        and element["y"] <= 0
        and element["x"] + element["width"] >= canvas["width"]
        and element["y"] + element["height"] >= canvas["height"]
    )


def _background_map(
    backgrounds: Iterable[Mapping[str, Any]], target_canvas: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    transformed = {}
    for element in backgrounds:
        result = deepcopy(dict(element))
        result.update(
            x=0.0,
            y=0.0,
            width=float(target_canvas["width"]),
            height=float(target_canvas["height"]),
        )
        transformed[element["id"]] = result
    return transformed


def _place_decorations(
    decorations: Iterable[Mapping[str, Any]],
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    scale = min(
        target_canvas["width"] / source_canvas["width"],
        target_canvas["height"] / source_canvas["height"],
    )
    transformed = {}
    for element in decorations:
        center_x = (element["x"] + element["width"] / 2) / source_canvas["width"]
        center_y = (element["y"] + element["height"] / 2) / source_canvas["height"]
        result = deepcopy(dict(element))
        result["width"] = element["width"] * scale
        result["height"] = element["height"] * scale
        result["x"] = center_x * target_canvas["width"] - result["width"] / 2
        result["y"] = center_y * target_canvas["height"] - result["height"] / 2
        clamped = clamp_element(result, target_canvas)
        transformed[element["id"]] = clamped if clamped is not None else result
    return transformed


def _pack_grid(
    units: Sequence[Unit],
    canvas: Mapping[str, Any],
    *,
    rows: int,
    columns: int,
) -> dict[str, dict[str, Any]]:
    if not units:
        return {}
    margin = _canvas_margin(canvas)
    gap = min(
        max(1.0, margin / 2),
        canvas["width"] / (columns * 4),
        canvas["height"] / (rows * 4),
    )
    usable_width = canvas["width"] - 2 * margin - gap * (columns - 1)
    usable_height = canvas["height"] - 2 * margin - gap * (rows - 1)
    cell_width = usable_width / columns
    cell_height = usable_height / rows
    transformed = {}
    for index, unit in enumerate(units):
        row, column = divmod(index, columns)
        box = Bounds(
            margin + column * (cell_width + gap),
            margin + row * (cell_height + gap),
            margin + column * (cell_width + gap) + cell_width,
            margin + row * (cell_height + gap) + cell_height,
        )
        transformed.update(_fit_unit_to_box(unit, box))
    return transformed


def _fit_unit_to_box(
    elements: Sequence[Mapping[str, Any]], box: Bounds
) -> dict[str, dict[str, Any]]:
    bounds = group_bounds(elements)
    width_scale = box.width / bounds.width if bounds.width > 0 else math.inf
    height_scale = box.height / bounds.height if bounds.height > 0 else math.inf
    scale = min(width_scale, height_scale)
    if not math.isfinite(scale):
        scale = 1.0
    scaled = [scale_element(element, scale, origin=(bounds.left, bounds.top)) for element in elements]
    scaled_bounds = group_bounds(scaled)
    box_center = box.center
    dx = box_center[0] - scaled_bounds.center[0]
    dy = box_center[1] - scaled_bounds.center[1]
    moved = translate_group(scaled, dx, dy)
    return {element["id"]: element for element in moved}


def _assemble(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    transformed: Mapping[str, Mapping[str, Any]],
) -> Design:
    return {
        "canvas": {
            "width": target_canvas["width"],
            "height": target_canvas["height"],
        },
        "elements": [
            deepcopy(dict(transformed.get(element["id"], element)))
            for element in source["elements"]
        ],
    }


def _canvas_margin(canvas: Mapping[str, Any]) -> float:
    shortest_side = min(canvas["width"], canvas["height"])
    return min(max(2.0, shortest_side * 0.04), shortest_side * 0.2)
