"""Cleanup pass after a layout is built, after LayoutRectifier (Shen et al. 2025).

Step A snaps units that were aligned in the source and have drifted slightly
apart. Step B pushes apart overlaps the layout created, including visible
decorations that ended up behind text. Elements only move, never resize, so
image ratios, text fitting and group shapes are untouched. Every move must
keep the hard rules and must not lower the score; the pass is bounded and
deterministic.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from engine.geometry import Bounds, element_bounds, group_bounds, overlap_area


Design = dict[str, Any]
Move = tuple[Sequence[str], float, float]
# LayoutRectifier alternates its two stages five times.
MAX_ROUNDS = 5
# Edges closer than this share of the canvas side count as meant to align.
SNAP_SHARE = 0.02
# Units overlapping by more than this share of the smaller one, beyond the
# source overlap, count as a new collision.
OVERLAP_SHARE = 0.01


def rectify(
    candidate: Mapping[str, Any],
    source_canvas: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    *,
    units: Sequence[Sequence[Mapping[str, Any]]],
    attached: Sequence[Sequence[str]],
    blockers: Sequence[bool],
    decorations: Sequence[Mapping[str, Any]],
    score: Callable[[Mapping[str, Any]], float],
    is_valid: Callable[[Mapping[str, Any]], bool],
) -> Design:
    """Return a cleaned copy of ``candidate``.

    ``units`` are the source content units in reading order, ``attached``
    lists for each unit the ids that move with it (its backing shapes), and
    ``blockers`` marks units a decoration must not sit on (units with text).
    ``decorations`` are the visible, free-standing source shapes.
    """
    design = deepcopy(dict(candidate))
    unit_ids = [
        [element["id"] for element in unit] + list(extra) for unit, extra in zip(units, attached)
    ]
    pairs = [(a, b) for a in range(len(units)) for b in range(a + 1, len(units))]
    # Step A (snap), then step B (push apart), as in LayoutRectifier.
    steps: list[Callable[[Design], list[Move]]] = [
        *(
            lambda d, a=a, b=b: _snap_moves(d, source_canvas, target_canvas, units, unit_ids, a, b)
            for a, b in pairs
        ),
        *(
            lambda d, a=a, b=b: _push_unit_moves(d, target_canvas, units, unit_ids, a, b)
            for a, b in pairs
        ),
        *(
            lambda d, shape=shape: _push_decoration_moves(d, target_canvas, shape, unit_ids, blockers)
            for shape in decorations
        ),
    ]
    current = None  # scored only once a move is worth trying
    for _ in range(MAX_ROUNDS):
        changed = False
        for step in steps:
            for ids, dx, dy in step(design):
                trial = _translated(design, ids, dx, dy)
                if not is_valid(trial):
                    continue
                if current is None:
                    current = score(design)
                trial_score = score(trial)
                if trial_score + 1e-12 < current:
                    continue
                design, current, changed = trial, trial_score, True
                break
        if not changed:
            break
    return design


def _snap_moves(design, source_canvas, target_canvas, units, unit_ids, index_a, index_b):
    source_a, source_b = group_bounds(units[index_a]), group_bounds(units[index_b])
    output_a = _bounds_of(design, unit_ids[index_a])
    output_b = _bounds_of(design, unit_ids[index_b])
    moves = []
    for axis, side in (("x", "width"), ("y", "height")):
        aligned = _tolerance(source_canvas, side)
        snap = max(2.0, float(target_canvas[side]) * SNAP_SHARE)
        for kind in range(3):
            if abs(_edge(source_a, axis, kind) - _edge(source_b, axis, kind)) > aligned:
                continue
            delta = _edge(output_a, axis, kind) - _edge(output_b, axis, kind)
            if 0.5 < abs(delta) <= snap:
                moves.append(
                    (unit_ids[index_b], delta, 0.0) if axis == "x" else (unit_ids[index_b], 0.0, delta)
                )
    return moves


def _push_unit_moves(design, canvas, units, unit_ids, index_a, index_b):
    before = _overlap_share(group_bounds(units[index_a]), group_bounds(units[index_b]))
    output_a = _bounds_of(design, unit_ids[index_a])
    output_b = _bounds_of(design, unit_ids[index_b])
    if _overlap_share(output_a, output_b) <= before + OVERLAP_SHARE:
        return []
    # Move the smaller unit; ties move the later one in reading order.
    if _area(output_a) < _area(output_b):
        mover, moving, fixed = unit_ids[index_a], output_a, output_b
    else:
        mover, moving, fixed = unit_ids[index_b], output_b, output_a
    return [(mover, dx, dy) for dx, dy in _escapes(moving, fixed, _gap(canvas))]


def _push_decoration_moves(design, canvas, decoration, unit_ids, blockers):
    shape = element_bounds(_element(design, decoration["id"]))
    for ids, blocks in zip(unit_ids, blockers):
        if blocks and overlap_area(shape, _bounds_of(design, ids)) > 0:
            unit = _bounds_of(design, ids)
            return [([decoration["id"]], dx, dy) for dx, dy in _escapes(shape, unit, _gap(canvas))]
    return []


def _escapes(mover: Bounds, fixed: Bounds, gap: float) -> list[tuple[float, float]]:
    """The four ways out of ``fixed``, shortest first."""
    options = [
        (fixed.left - gap - mover.right, 0.0),
        (fixed.right + gap - mover.left, 0.0),
        (0.0, fixed.top - gap - mover.bottom),
        (0.0, fixed.bottom + gap - mover.top),
    ]
    return sorted(options, key=lambda move: (abs(move[0]) + abs(move[1]), move))


def _translated(design: Mapping[str, Any], ids: Sequence[str], dx: float, dy: float) -> Design:
    moving = set(ids)
    result = deepcopy(dict(design))
    for element in result["elements"]:
        if element["id"] in moving:
            element["x"] = element["x"] + dx
            element["y"] = element["y"] + dy
    return result


def _bounds_of(design: Mapping[str, Any], ids: Sequence[str]) -> Bounds:
    wanted = set(ids)
    return group_bounds(element for element in design["elements"] if element["id"] in wanted)


def _element(design: Mapping[str, Any], element_id: str) -> Mapping[str, Any]:
    return next(element for element in design["elements"] if element["id"] == element_id)


def _edge(bounds: Bounds, axis: str, kind: int) -> float:
    if axis == "x":
        return (bounds.left, bounds.center[0], bounds.right)[kind]
    return (bounds.top, bounds.center[1], bounds.bottom)[kind]


def _tolerance(canvas: Mapping[str, Any], side: str) -> float:
    """Alignment tolerance used by the score: 1% of the side, at least 2px."""
    return max(2.0, float(canvas[side]) * 0.01)


def _overlap_share(first: Bounds, second: Bounds) -> float:
    smaller = min(_area(first), _area(second))
    return overlap_area(first, second) / smaller if smaller > 0 else 0.0


def _area(bounds: Bounds) -> float:
    return max(0.0, bounds.width) * max(0.0, bounds.height)


def _gap(canvas: Mapping[str, Any]) -> float:
    return max(1.0, min(float(canvas["width"]), float(canvas["height"])) * 0.01)
