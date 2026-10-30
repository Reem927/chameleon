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
    translate_group,
)
from engine.text_fit import fit_text, line_count_at, text_overflow, wrap_width


Design = dict[str, Any]
Unit = list[Mapping[str, Any]]

# The first seven parts keep their earlier proportions inside 0.80; the last
# four come from the layout papers and share 0.20 (D-023, D-025).
QUALITY_WEIGHTS = {
    "collision": 0.192,
    "text": 0.192,
    "hierarchy": 0.144,
    "canvas_use": 0.112,
    "alignment": 0.064,
    "balance_spacing": 0.048,
    "group_cohesion": 0.048,
    "reading_order": 0.06,
    "similarity": 0.06,
    "source_alignment": 0.04,
    "area_share": 0.04,
}
# Two units share a row when their vertical overlap is at least this share
# of the shorter one.
ROW_SHARE = 0.5
# Free change in a unit's share of the canvas (LayoutGAN's area margin).
AREA_SHARE_MARGIN = 0.3
# A backing card fits snugly around what it holds; a shape many times larger
# (a soft glow, a big circle) is decoration that happens to surround it.
BACKING_MAX_AREA_RATIO = 4.0
# How the flow strategies arrange content units: (direction, number of lines).
FLOW_STRATEGIES = {
    "horizontal_split": ("row", 1),
    "vertical_stack": ("column", 1),
    "compact_banner": ("row", 2),
}
# Graphic scale relative to text scale. 1.0 keeps the source balance between
# text and graphics; lower values give text priority on cramped canvases.
GRAPHIC_RATIOS = (1.0, 0.6, 0.3)
# Shortest comfortable line, in characters, when text wraps in a row.
MIN_LINE_CHARACTERS = 12
# Text is kept at least this large (or its source size, if smaller) whenever
# the layout still fits with that floor in place.
READABLE_FONT_SIZE = 7.0
# Text at or below this size earns no readability credit.
ILLEGIBLE_FONT_SIZE = 4.0
# Text at or above this size (or its source size) counts as fully legible.
COMFORTABLE_FONT_SIZE = 14.0


def generate_candidates(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> list[tuple[str, Design]]:
    """Return complete candidates in a stable order."""
    candidates = [("preserve_and_repair", preserve_and_repair(source, target_canvas))]
    for name, (axis, lines) in FLOW_STRATEGIES.items():
        for ratio in GRAPHIC_RATIOS:
            label = name if ratio == 1.0 else f"{name}@{ratio:g}"
            candidates.append(
                (
                    label,
                    flow_layout(
                        source, target_canvas, axis=axis, lines=lines, graphic_ratio=ratio
                    ),
                )
            )
    return candidates


def preserve_and_repair(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any]
) -> Design:
    """Scale the full foreground as one composition without stretching it.

    The composition grows no more than the canvas does and is scaled about
    the canvas centre like a `cover` background, so it stays registered with
    the background and a same-size target returns the source geometry.
    """
    backgrounds, decorations, content = _parts(source)
    backings = _backing_shapes(source, decorations, content)
    decorations = [element for element in decorations if element["id"] not in backings]
    foreground = [element for unit in content for element in unit] + decorations
    transformed = _background_map(backgrounds, target_canvas)
    if foreground:
        transformed.update(_place_composition(foreground, source["canvas"], target_canvas))
    for element_id, element in transformed.items():
        # Glyph widths do not scale exactly linearly, so text that just fit
        # can wrap one line more once scaled; refit only those boxes.
        if element.get("type") == "text" and text_overflow(element) > 0:
            transformed[element_id] = fit_text(
                element, element["width"], element["height"], max_font_size=element["font_size"]
            )
    transformed.update(_place_backings(backings, content, source, target_canvas, transformed))
    return _assemble(source, target_canvas, transformed)


def flow_layout(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    axis: str,
    lines: int,
    graphic_ratio: float,
) -> Design:
    """Lay content units out in reading order along rows or columns.

    Text is scaled by one shared factor so its size order survives, and it
    reflows into whatever box shape the slot allows. Graphics keep their
    proportions and scale by ``graphic_ratio`` times the text factor, so a
    lower ratio gives text priority when space is short.
    """
    backgrounds, decorations, units = _parts(source)
    backings = _backing_shapes(source, decorations, units)
    decorations = [element for element in decorations if element["id"] not in backings]
    units.sort(key=lambda unit: (group_bounds(unit).center[1], group_bounds(unit).center[0]))
    transformed = _background_map(backgrounds, target_canvas)
    transformed.update(_place_decorations(decorations, source["canvas"], target_canvas))
    if units:
        max_scale = max(
            1.0,
            min(
                target_canvas["width"] / source["canvas"]["width"],
                target_canvas["height"] / source["canvas"]["height"],
            ),
        )
        transformed.update(
            _pack_flow(
                units,
                _safe_box(target_canvas),
                axis=axis,
                lines=lines,
                graphic_ratio=graphic_ratio,
                max_scale=max_scale,
                gap=_canvas_margin(target_canvas) / 2,
            )
        )
    transformed.update(_place_backings(backings, units, source, target_canvas, transformed))
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
    source_canvas = source["canvas"]
    # LayoutRectifier measures faithfulness on a canvas of the same shape.
    # When the shape changes a lot no candidate can keep the source geometry,
    # so those parts may cost only as much as the aspect ratios agree. A copy
    # whose text can no longer be read is not the same design either, so the
    # credit is shared out only over text that stays readable.
    closeness = _aspect_closeness(source_canvas, target_canvas)
    readable = _readable_text_share(source_units, output_units)

    def faithful(value: float) -> float:
        return (1.0 - (1.0 - value) * closeness) * readable

    return {
        "collision": _collision_quality(source, candidate, source_units, output_units),
        "text": _text_quality(source_units, output_units),
        "hierarchy": _hierarchy_quality(source_units, output_units),
        "canvas_use": _canvas_use_quality(output_units, target_canvas),
        "alignment": _alignment_quality(output_units, target_canvas),
        "balance_spacing": _balance_spacing_quality(output_units, target_canvas),
        "group_cohesion": _group_cohesion_quality(source, candidate, target_canvas),
        "reading_order": _reading_order_quality(source_units, output_units),
        "similarity": faithful(
            _similarity_quality(source_units, output_units, source_canvas, target_canvas)
        ),
        "source_alignment": faithful(
            _source_alignment_quality(source_units, output_units, source_canvas, target_canvas)
        ),
        "area_share": faithful(
            _area_share_quality(source_units, output_units, source_canvas, target_canvas)
        ),
    }


def _readable_text_share(source_units: Sequence[Unit], output_units: Sequence[Unit]) -> float:
    """Share of text kept at the readable floor, or its source size if smaller."""
    total = readable = 0
    for source_unit, output_unit in zip(source_units, output_units):
        for original, element in zip(source_unit, output_unit):
            if element.get("type") != "text":
                continue
            total += 1
            floor = min(float(original["font_size"]), READABLE_FONT_SIZE)
            readable += float(element["font_size"]) >= floor - 1e-6
    return readable / total if total else 1.0


def _aspect_closeness(source_canvas: Mapping[str, Any], target_canvas: Mapping[str, Any]) -> float:
    """1 for the same aspect ratio, falling toward 0 as the shapes diverge."""
    source_ratio = source_canvas["width"] / source_canvas["height"]
    target_ratio = target_canvas["width"] / target_canvas["height"]
    return min(source_ratio, target_ratio) / max(source_ratio, target_ratio)


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


def _collision_quality(
    source: Mapping[str, Any],
    candidate: Mapping[str, Any],
    source_units: Sequence[Unit],
    output_units: Sequence[Unit],
) -> float:
    """New overlaps between units, plus LayoutRectifier's parent/child rule.

    A backing shape must keep holding its unit, and any other shape drawn
    above a unit must not newly cover it. Shapes behind units hide nothing.
    """
    new_overlaps = []
    for (source_first, source_second), (output_first, output_second) in zip(
        combinations(source_units, 2), combinations(output_units, 2)
    ):
        source_overlap = _unit_overlap_ratio(source_first, source_second)
        output_overlap = _unit_overlap_ratio(output_first, output_second)
        new_overlaps.append(max(0.0, output_overlap - source_overlap))

    output_by_id = {element["id"]: element for element in candidate["elements"]}
    _backgrounds, decorations, units = _parts(source)
    backings = _backing_shapes(source, decorations, units)
    stacking = _stacking_order(source)
    for shape in decorations:
        output_shape = element_bounds(output_by_id[shape["id"]])
        for source_unit, output_unit in zip(source_units, output_units):
            child = group_bounds(output_unit)
            if _bounds_area(child) <= 0:
                continue
            covered = overlap_area(output_shape, child) / _bounds_area(child)
            if shape["id"] in backings and backings[shape["id"]][1] == source_unit:
                new_overlaps.append(1.0 - covered)
            elif any(stacking(shape) > stacking(element) for element in source_unit):
                before = group_bounds(source_unit)
                was_covered = overlap_area(element_bounds(shape), before) / _bounds_area(before)
                opacity = float(shape.get("opacity", 1.0))
                new_overlaps.append(max(0.0, covered - was_covered) * opacity)
    if not new_overlaps:
        return 1.0
    penalty = 0.7 * max(new_overlaps) + 0.3 * fmean(new_overlaps)
    return 1.0 - _clamp01(penalty)


def _reading_order_quality(
    source_units: Sequence[Unit],
    output_units: Sequence[Unit],
) -> float:
    """Share of unit pairs that keep their reading order (LayoutGAN Eq. 12).

    The paper reads "left to right, top to bottom" through a distance from
    the top-left corner; that proxy flips correct row-major order in a
    two-row banner, so the rule is applied as stated: units sharing a row
    read left to right, otherwise top to bottom.
    """
    pairs = kept = 0
    for (source_a, output_a), (source_b, output_b) in combinations(
        zip(source_units, output_units), 2
    ):
        before = _reads_before(group_bounds(source_a), group_bounds(source_b))
        if before == 0:
            continue
        pairs += 1
        kept += _reads_before(group_bounds(output_a), group_bounds(output_b)) == before
    return kept / pairs if pairs else 1.0


def _reads_before(first: Bounds, second: Bounds) -> int:
    """1 if ``first`` reads before ``second``, -1 if after, 0 if no order."""
    shared = min(first.bottom, second.bottom) - max(first.top, second.top)
    shortest = min(first.height, second.height)
    if shortest > 0 and shared >= ROW_SHARE * shortest:
        difference = second.left - first.left
    else:
        difference = second.center[1] - first.center[1]
    if abs(difference) < 1e-6:
        return 0
    return 1 if difference > 0 else -1


def _similarity_quality(
    source_units: Sequence[Unit],
    output_units: Sequence[Unit],
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
) -> float:
    """How closely units keep their place on the normalised canvas.

    Distance-IoU per unit, as LayoutRectifier uses, mapped to 0..1 so a unit
    that moves a little costs a little instead of dropping straight to zero.
    """
    values = []
    for source_unit, output_unit in zip(source_units, output_units):
        before = _normalised(group_bounds(source_unit), source_canvas)
        after = _normalised(group_bounds(output_unit), target_canvas)
        intersection = overlap_area(before, after)
        union = _bounds_area(before) + _bounds_area(after) - intersection
        iou = intersection / union if union > 0 else 1.0
        hull = Bounds(
            min(before.left, after.left),
            min(before.top, after.top),
            max(before.right, after.right),
            max(before.bottom, after.bottom),
        )
        diagonal_squared = hull.width**2 + hull.height**2
        distance_squared = (before.center[0] - after.center[0]) ** 2 + (
            before.center[1] - after.center[1]
        ) ** 2
        penalty = distance_squared / diagonal_squared if diagonal_squared > 0 else 0.0
        values.append(_clamp01((1.0 + iou - penalty) / 2.0) if iou < 1.0 else 1.0)
    return fmean(values) if values else 1.0


def _source_alignment_quality(
    source_units: Sequence[Unit],
    output_units: Sequence[Unit],
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
) -> float:
    """Share of pairs aligned in the source that are still aligned.

    LayoutRectifier keeps each source alignment; a retarget may turn a column
    into a row, so any edge or centre alignment counts as kept.
    """
    pairs = kept = 0
    for (source_a, output_a), (source_b, output_b) in combinations(
        zip(source_units, output_units), 2
    ):
        if not _aligned(group_bounds(source_a), group_bounds(source_b), source_canvas):
            continue
        pairs += 1
        kept += _aligned(group_bounds(output_a), group_bounds(output_b), target_canvas)
    return kept / pairs if pairs else 1.0


def _area_share_quality(
    source_units: Sequence[Unit],
    output_units: Sequence[Unit],
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
) -> float:
    """Units keep their share of the canvas within LayoutGAN's 30% margin (Eq. 8)."""
    source_area = float(source_canvas["width"] * source_canvas["height"])
    target_area = float(target_canvas["width"] * target_canvas["height"])
    errors = []
    for source_unit, output_unit in zip(source_units, output_units):
        before = _bounds_area(group_bounds(source_unit)) / source_area
        if before <= 0:
            continue
        after = _bounds_area(group_bounds(output_unit)) / target_area
        errors.append(_clamp01(abs(after - before) / before - AREA_SHARE_MARGIN))
    return 1.0 - fmean(errors) if errors else 1.0


def _aligned(first: Bounds, second: Bounds, canvas: Mapping[str, Any]) -> bool:
    tolerance_x = max(2.0, float(canvas["width"]) * 0.01)
    tolerance_y = max(2.0, float(canvas["height"]) * 0.01)
    return any(
        abs(a - b) <= tolerance_x
        for a, b in (
            (first.left, second.left),
            (first.center[0], second.center[0]),
            (first.right, second.right),
        )
    ) or any(
        abs(a - b) <= tolerance_y
        for a, b in (
            (first.top, second.top),
            (first.center[1], second.center[1]),
            (first.bottom, second.bottom),
        )
    )


def _normalised(bounds: Bounds, canvas: Mapping[str, Any]) -> Bounds:
    width, height = float(canvas["width"]), float(canvas["height"])
    return Bounds(bounds.left / width, bounds.top / height, bounds.right / width, bounds.bottom / height)


def _unit_overlap_ratio(first: Unit, second: Unit) -> float:
    first_bounds = group_bounds(first)
    second_bounds = group_bounds(second)
    smaller_area = min(_bounds_area(first_bounds), _bounds_area(second_bounds))
    if smaller_area <= 0:
        return 0.0
    return overlap_area(first_bounds, second_bounds) / smaller_area


def _text_quality(source_units: Sequence[Unit], output_units: Sequence[Unit]) -> float:
    """Readability weighted by source prominence, plus the worst text.

    The worst-text part stops a large headline from hiding fine print that
    has become unreadable.
    """
    total = weight_sum = 0.0
    worst = 1.0
    for source_unit, output_unit in zip(source_units, output_units):
        for original, element in zip(source_unit, output_unit):
            if element.get("type") != "text":
                continue
            source_size = float(original["font_size"])
            target_size = min(source_size, COMFORTABLE_FONT_SIZE)
            legibility = _clamp01(
                (float(element["font_size"]) - ILLEGIBLE_FONT_SIZE)
                / max(target_size - ILLEGIBLE_FONT_SIZE, 1e-9)
            )
            fit = 1.0 - min(1.0, text_overflow(element))
            quality = 0.7 * legibility + 0.3 * fit
            total += source_size * quality
            weight_sum += source_size
            worst = min(worst, quality)
    if not weight_sum:
        return 1.0
    return 0.7 * total / weight_sum + 0.3 * worst


def _hierarchy_quality(source_units: Sequence[Unit], output_units: Sequence[Unit]) -> float:
    """How well relative sizes survive.

    Text is compared with text and graphics with graphics by how much each
    scaled. Between text and graphics only a flipped size order counts,
    because banners legitimately shrink pictures more than words.
    """
    sizes = []
    for source_unit, output_unit in zip(source_units, output_units):
        source_size = math.sqrt(_bounds_area(group_bounds(source_unit)))
        if source_size <= 0:
            continue
        if _is_reflowable(source_unit):
            scale = float(output_unit[0]["font_size"]) / float(source_unit[0]["font_size"])
        else:
            scale = math.sqrt(_bounds_area(group_bounds(output_unit))) / source_size
        if scale > 0:
            sizes.append((_carries_text(source_unit), source_size, scale))

    errors = []
    for (text_a, size_a, scale_a), (text_b, size_b, scale_b) in combinations(sizes, 2):
        change = math.log(scale_a / scale_b)
        source_order = math.log(size_a / size_b)
        output_order = source_order + change
        flipped = output_order * source_order < 0
        if text_a != text_b:
            errors.append(abs(output_order) if flipped else 0.0)
        elif text_a and not flipped:
            # Lifting small text toward a readable size narrows the gap to
            # large text without breaking the order, so it costs half.
            errors.append(abs(change) / 2)
        else:
            errors.append(abs(change))
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
    """A `cover` image or a plain rectangle that fills the whole canvas.

    A solid rectangle has no pixels to distort, so like a `cover` image it
    stretches to fill the target instead of shrinking into a band.
    """
    is_cover_image = element.get("type") == "image" and element.get("fit") == "cover"
    is_fill_rectangle = (
        element.get("type") == "shape" and element.get("shape_type") == "rectangle"
    )
    if not (is_cover_image or is_fill_rectangle):
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


def _backing_shapes(
    source: Mapping[str, Any],
    decorations: Sequence[Mapping[str, Any]],
    units: Sequence[Unit],
) -> dict[str, tuple[Mapping[str, Any], Unit]]:
    """Map each ungrouped shape drawn behind exactly one content unit to it.

    This is LayoutRectifier's parent/child containment read from the source:
    the shape is the parent and must keep holding its child after resizing.
    """
    stacking = _stacking_order(source)
    backings = {}
    for shape in decorations:
        rotation = float(shape.get("rotation", 0)) % 360
        if shape.get("shape_type") == "line" or min(rotation, 360 - rotation) > 1e-6:
            continue
        shape_bounds = element_bounds(shape)
        held = [
            unit
            for unit in units
            if _bounds_contain(shape_bounds, group_bounds(unit))
            and _bounds_area(shape_bounds)
            <= BACKING_MAX_AREA_RATIO * _bounds_area(group_bounds(unit))
            and all(stacking(shape) < stacking(element) for element in unit)
        ]
        if len(held) == 1:
            backings[shape["id"]] = (shape, held[0])
    return backings


def _place_backings(
    backings: Mapping[str, tuple[Mapping[str, Any], Unit]],
    units: Sequence[Unit],
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    transformed: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Wrap each backing shape around its unit's new box with scaled padding.

    A shape that spans the whole source width or height keeps spanning the
    target, so a full-width band behind a title stays a full-width band.
    Padding stops at any other unit drawn below the shape that the shape did
    not overlap in the source; passing behind a unit hides nothing.
    """
    source_canvas = source["canvas"]
    stacking = _stacking_order(source)
    placed = {}
    for shape_id, (shape, unit) in backings.items():
        before = group_bounds(unit)
        after = group_bounds([transformed.get(element["id"], element) for element in unit])
        scale = (
            math.sqrt(_bounds_area(after) / _bounds_area(before))
            if _bounds_area(before) > 0
            else 1.0
        )
        left = after.left - (before.left - shape["x"]) * scale
        top = after.top - (before.top - shape["y"]) * scale
        right = after.right + (shape["x"] + shape["width"] - before.right) * scale
        bottom = after.bottom + (shape["y"] + shape["height"] - before.bottom) * scale
        if shape["x"] <= 0 and shape["x"] + shape["width"] >= source_canvas["width"]:
            left, right = 0.0, float(target_canvas["width"])
        if shape["y"] <= 0 and shape["y"] + shape["height"] >= source_canvas["height"]:
            top, bottom = 0.0, float(target_canvas["height"])
        for other in units:
            if (
                other is unit
                or overlap_area(element_bounds(shape), group_bounds(other)) > 0
                or all(stacking(element) > stacking(shape) for element in other)
            ):
                continue
            blocker = group_bounds([transformed.get(element["id"], element) for element in other])
            if overlap_area(Bounds(left, top, right, bottom), blocker) <= 0:
                continue
            if blocker.bottom <= after.top:
                top = max(top, blocker.bottom)
            elif blocker.top >= after.bottom:
                bottom = min(bottom, blocker.top)
            elif blocker.right <= after.left:
                left = max(left, blocker.right)
            elif blocker.left >= after.right:
                right = min(right, blocker.left)
        left, top = max(0.0, left), max(0.0, top)
        right = min(float(target_canvas["width"]), right)
        bottom = min(float(target_canvas["height"]), bottom)
        result = deepcopy(dict(shape))
        result.update(x=left, y=top, width=right - left, height=bottom - top)
        placed[shape_id] = result
    return placed


def _stacking_order(source: Mapping[str, Any]):
    """Sort key for paint order: `z_index`, then position in the element list."""
    order = {element["id"]: index for index, element in enumerate(source["elements"])}

    def stacking(element: Mapping[str, Any]) -> tuple[float, int]:
        return (float(element.get("z_index", 0)), order[element["id"]])

    return stacking


def _bounds_contain(outer: Bounds, inner: Bounds, tolerance: float = 0.5) -> bool:
    return (
        outer.left <= inner.left + tolerance
        and outer.top <= inner.top + tolerance
        and outer.right >= inner.right - tolerance
        and outer.bottom >= inner.bottom - tolerance
    )


def _pack_flow(
    units: Sequence[Unit],
    box: Bounds,
    *,
    axis: str,
    lines: int,
    graphic_ratio: float,
    max_scale: float,
    gap: float,
) -> dict[str, dict[str, Any]]:
    horizontal = axis == "row"
    main_size = box.width if horizontal else box.height
    lines = max(1, min(lines, len(units)))
    cross_size = ((box.height if horizontal else box.width) - gap * (lines - 1)) / lines

    best = None
    for floor in (READABLE_FONT_SIZE, 1.0):
        for runs in _contiguous_splits(units, lines):
            scale = _largest_scale(
                runs, main_size, cross_size, horizontal, graphic_ratio, max_scale, gap, floor
            )
            if scale is not None and (best is None or scale > best[0] + 1e-9):
                best = (scale, runs)
        if best is not None:
            break
    if best is None:
        best = (0.0, [list(units)])
        floor = 1.0
    scale, runs = best

    transformed: dict[str, dict[str, Any]] = {}
    for line_index, run in enumerate(runs):
        cross_start = (box.top if horizontal else box.left) + line_index * (cross_size + gap)
        extents = [
            _main_extent(unit, scale, cross_size, horizontal, graphic_ratio, floor)
            for unit in run
        ]
        free = max(0.0, main_size - sum(extents) - gap * (len(run) - 1))
        if horizontal:
            # Spare width first lets text wrap onto fewer, longer lines, up
            # to a single line. Whatever is left spreads around the units.
            wanted = [
                _single_line_width(unit, scale, cross_size, floor) - extent
                if _is_reflowable(unit)
                else 0.0
                for unit, extent in zip(run, extents)
            ]
            wanted = [max(0.0, value) for value in wanted]
            share = min(1.0, free / sum(wanted)) if sum(wanted) > 0 else 0.0
            extents = [extent + value * share for extent, value in zip(extents, wanted)]
            free -= sum(wanted) * share
        spacing = free / (len(run) + 1)
        position = (box.left if horizontal else box.top) + spacing
        for unit, extent in zip(run, extents):
            if horizontal:
                slot = Bounds(position, cross_start, position + extent, cross_start + cross_size)
            else:
                slot = Bounds(cross_start, position, cross_start + cross_size, position + extent)
            transformed.update(_place_in_slot(unit, slot, scale, floor))
            position += extent + gap + spacing
    return transformed


def _contiguous_splits(units: Sequence[Unit], lines: int) -> list[list[list[Unit]]]:
    """Every way to cut the ordered units into ``lines`` non-empty runs."""
    if lines == 1:
        return [[list(units)]]
    splits = []
    for cut in range(1, len(units) - lines + 2):
        for rest in _contiguous_splits(units[cut:], lines - 1):
            splits.append([list(units[:cut]), *rest])
    return splits


def _largest_scale(
    runs: Sequence[Sequence[Unit]],
    main_size: float,
    cross_size: float,
    horizontal: bool,
    graphic_ratio: float,
    max_scale: float,
    gap: float,
    floor: float,
) -> float | None:
    """Largest shared text scale that fits, or ``None`` if nothing fits."""

    def fits(scale: float) -> bool:
        return all(
            sum(
                _main_extent(unit, scale, cross_size, horizontal, graphic_ratio, floor)
                for unit in run
            )
            + gap * (len(run) - 1)
            <= main_size
            for run in runs
        )

    if fits(max_scale):
        return max_scale
    if not fits(1e-6):
        return None
    low, high = 0.0, max_scale
    for _ in range(30):
        middle = (low + high) / 2
        if fits(middle):
            low = middle
        else:
            high = middle
    return low


def _main_extent(
    unit: Unit,
    scale: float,
    cross_size: float,
    horizontal: bool,
    graphic_ratio: float,
    floor: float,
) -> float:
    """Length a unit needs along the flow direction at ``scale``."""
    if _is_reflowable(unit):
        element = unit[0]
        font_size = _text_font_size(element, scale, cross_size, horizontal, floor)
        line_height = font_size * float(element.get("line_height", 1.2))
        if horizontal:
            line_slots = max(1, math.floor(cross_size / max(line_height, 1e-9)))
            # Very short lines read badly, so text never wraps narrower than
            # about MIN_LINE_CHARACTERS per line, even if the height allows.
            line_slots = min(
                line_slots,
                max(1, math.ceil(len(str(element.get("content", ""))) / MIN_LINE_CHARACTERS)),
            )
            return wrap_width(element, font_size, line_slots)
        return line_count_at(element, font_size, cross_size) * line_height

    bounds = group_bounds(unit)
    along, across = (bounds.width, bounds.height) if horizontal else (bounds.height, bounds.width)
    unit_scale = _rigid_scale(unit, scale, graphic_ratio, floor)
    if across > 0:
        unit_scale = min(unit_scale, cross_size / across)
    return along * unit_scale


def _single_line_width(unit: Unit, scale: float, cross_size: float, floor: float) -> float:
    element = unit[0]
    font_size = _text_font_size(element, scale, cross_size, True, floor)
    return wrap_width(element, font_size, 1)


def _rigid_scale(unit: Unit, scale: float, graphic_ratio: float, floor: float) -> float:
    """Scale for a unit that keeps its shape.

    Units with text follow the text scale, raised so their smallest label
    stays readable. Pure graphics follow ``graphic_ratio`` times that scale.
    """
    label_sizes = [float(e["font_size"]) for e in unit if e.get("type") == "text"]
    if not label_sizes:
        return scale * graphic_ratio
    smallest = min(label_sizes)
    return max(scale, min(smallest, floor) / smallest)


def _readable_font_size(element: Mapping[str, Any], scale: float, floor: float) -> float:
    font_size = float(element["font_size"])
    return max(font_size * scale, min(font_size, floor))


def _text_font_size(
    element: Mapping[str, Any],
    scale: float,
    cross_size: float,
    horizontal: bool,
    floor: float,
) -> float:
    font_size = _readable_font_size(element, scale, floor)
    if horizontal:
        font_size = min(font_size, cross_size / float(element.get("line_height", 1.2)))
    return max(1.0, font_size)


def _place_in_slot(
    unit: Unit, slot: Bounds, scale: float, floor: float
) -> dict[str, dict[str, Any]]:
    if not _is_reflowable(unit):
        return _fit_unit_to_box(unit, slot)
    element = unit[0]
    font_size = min(
        _readable_font_size(element, scale, floor),
        slot.height / float(element.get("line_height", 1.2)),
    )
    fitted = fit_text(element, slot.width, slot.height, max_font_size=font_size)
    fitted["x"] = slot.center[0] - fitted["width"] / 2
    fitted["y"] = slot.center[1] - fitted["height"] / 2
    return {fitted["id"]: fitted}


def _is_reflowable(unit: Unit) -> bool:
    """A lone upright text element can change its box shape and wrap."""
    if len(unit) != 1 or unit[0].get("type") != "text":
        return False
    rotation = float(unit[0].get("rotation", 0)) % 360
    return min(rotation, 360 - rotation) <= 1e-6


def _carries_text(unit: Unit) -> bool:
    return any(element.get("type") == "text" for element in unit)


def _place_composition(
    elements: Sequence[Mapping[str, Any]],
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    bounds = group_bounds(elements)
    box = _safe_box(target_canvas)
    width_ratio = target_canvas["width"] / source_canvas["width"]
    height_ratio = target_canvas["height"] / source_canvas["height"]
    fit = min(
        box.width / bounds.width if bounds.width > 0 else math.inf,
        box.height / bounds.height if bounds.height > 0 else math.inf,
    )
    scale = min(fit, max(width_ratio, height_ratio))
    scaled = [scale_element(element, scale, origin=(bounds.left, bounds.top)) for element in elements]
    scaled_bounds = group_bounds(scaled)
    # Scale about the canvas centre, the way a `cover` background is cropped,
    # so the content stays where it sat on its background.
    dx = (bounds.center[0] - source_canvas["width"] / 2) * scale + target_canvas[
        "width"
    ] / 2 - scaled_bounds.center[0]
    dy = (bounds.center[1] - source_canvas["height"] / 2) * scale + target_canvas[
        "height"
    ] / 2 - scaled_bounds.center[1]
    dx = _shift_into(scaled_bounds.left + dx, scaled_bounds.right + dx, box.left, box.right) + dx
    dy = _shift_into(scaled_bounds.top + dy, scaled_bounds.bottom + dy, box.top, box.bottom) + dy
    moved = translate_group(scaled, dx, dy)
    return {element["id"]: element for element in moved}


def _shift_into(low: float, high: float, box_low: float, box_high: float) -> float:
    """Smallest shift that moves [low, high] inside [box_low, box_high]."""
    if low < box_low:
        return box_low - low
    if high > box_high:
        return box_high - high
    return 0.0


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


def _safe_box(canvas: Mapping[str, Any]) -> Bounds:
    margin = _canvas_margin(canvas)
    return Bounds(margin, margin, canvas["width"] - margin, canvas["height"] - margin)


def _canvas_margin(canvas: Mapping[str, Any]) -> float:
    shortest_side = min(canvas["width"], canvas["height"])
    return min(max(2.0, shortest_side * 0.04), shortest_side * 0.2)
