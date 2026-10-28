"""Hard validation for complete resized-design candidates."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping

from engine.geometry import is_on_canvas


COMMON_REQUIRED = {"id", "type", "x", "y", "width", "height"}
TYPE_REQUIRED = {
    "text": {"content", "font_family", "font_size", "color"},
    "image": {"asset_id"},
    "shape": {"shape_type", "fill_color"},
}
ENUMS = {
    "type": {"text", "image", "shape"},
    "fit": {"contain", "cover", "fill"},
    "shape_type": {"rectangle", "ellipse", "line"},
    "font_weight": {"regular", "bold"},
    "font_style": {"normal", "italic"},
    "text_align": {"left", "center", "right"},
}
MUTABLE_FIELDS = {"x", "y", "width", "height"}
IMAGE_RATIO_TOLERANCE = 0.05


def validate_candidate(
    source: Mapping[str, Any],
    target_canvas: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    image_ratio_tolerance: float = IMAGE_RATIO_TOLERANCE,
) -> list[str]:
    """Return every hard-rule problem found in a complete output candidate."""
    problems: list[str] = []

    _validate_canvas(target_canvas, "target canvas", problems)
    if not isinstance(candidate, Mapping):
        return ["candidate must be an object"]
    if set(candidate) != {"canvas", "elements"}:
        problems.append("candidate must contain only 'canvas' and 'elements'")

    output_canvas = candidate.get("canvas")
    _validate_canvas(output_canvas, "output canvas", problems)
    if isinstance(output_canvas, Mapping) and isinstance(target_canvas, Mapping):
        if dict(output_canvas) != dict(target_canvas):
            problems.append("output canvas must exactly match target_canvas")

    source_elements = source.get("elements") if isinstance(source, Mapping) else None
    output_elements = candidate.get("elements")
    if not isinstance(source_elements, list):
        problems.append("source elements must be a list")
        return problems
    if not isinstance(output_elements, list):
        problems.append("candidate elements must be a list")
        return problems

    source_ids = [_element_id(element) for element in source_elements]
    output_ids = [_element_id(element) for element in output_elements]
    if None in source_ids:
        problems.append("every source element must have a string id")
    if None in output_ids:
        problems.append("every output element must have a string id")

    source_counts = Counter(source_ids)
    output_counts = Counter(output_ids)
    duplicate_source_ids = sorted(str(key) for key, count in source_counts.items() if count > 1)
    duplicate_output_ids = sorted(str(key) for key, count in output_counts.items() if count > 1)
    if duplicate_source_ids:
        problems.append(f"source contains duplicate ids: {duplicate_source_ids}")
    if duplicate_output_ids:
        problems.append(f"output contains duplicate ids: {duplicate_output_ids}")
    if source_counts != output_counts:
        problems.append("output element ids and counts must exactly match the source")

    source_by_id = {
        element["id"]: element
        for element in source_elements
        if isinstance(element, Mapping) and isinstance(element.get("id"), str)
    }
    output_by_id = {
        element["id"]: element
        for element in output_elements
        if isinstance(element, Mapping) and isinstance(element.get("id"), str)
    }

    for index, element in enumerate(output_elements):
        _validate_element(element, index, output_canvas, problems)

    for element_id in sorted(source_by_id.keys() & output_by_id.keys()):
        original = source_by_id[element_id]
        output = output_by_id[element_id]
        if set(original) != set(output):
            problems.append(f"element '{element_id}' must preserve its exact field set")
        mutable = set(MUTABLE_FIELDS)
        if original.get("type") == "text":
            mutable.add("font_size")
        for key in (original.keys() & output.keys()) - mutable:
            if original[key] != output[key]:
                problems.append(f"element '{element_id}' changed protected field '{key}'")

        if original.get("type") == "image" and original.get("fit", "contain") != "cover":
            _validate_image_ratio(
                element_id, original, output, image_ratio_tolerance, problems
            )

    return problems


def candidate_is_valid(
    source: Mapping[str, Any], target_canvas: Mapping[str, Any], candidate: Mapping[str, Any]
) -> bool:
    return not validate_candidate(source, target_canvas, candidate)


def _validate_canvas(value: Any, label: str, problems: list[str]) -> None:
    if not isinstance(value, Mapping):
        problems.append(f"{label} must be an object")
        return
    if set(value) != {"width", "height"}:
        problems.append(f"{label} must contain only width and height")
    for key in ("width", "height"):
        dimension = value.get(key)
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 1:
            problems.append(f"{label} {key} must be a positive integer")


def _validate_element(
    element: Any, index: int, canvas: Any, problems: list[str]
) -> None:
    label = f"output element at index {index}"
    if not isinstance(element, Mapping):
        problems.append(f"{label} must be an object")
        return

    missing = COMMON_REQUIRED - set(element)
    if missing:
        problems.append(f"{label} is missing required fields: {sorted(missing)}")
    element_type = element.get("type")
    if not isinstance(element_type, str) or element_type not in ENUMS["type"]:
        problems.append(f"{label} has invalid type")
    else:
        type_missing = TYPE_REQUIRED[element_type] - set(element)
        if type_missing:
            problems.append(f"{label} is missing type fields: {sorted(type_missing)}")

    for field in ("x", "y", "width", "height", "rotation", "opacity"):
        if field in element and not _is_finite_number(element[field]):
            problems.append(f"{label} field '{field}' must be a finite number")
    for field in ("width", "height"):
        if _is_finite_number(element.get(field)) and element[field] < 0:
            problems.append(f"{label} field '{field}' must be non-negative")
    if "opacity" in element and _is_finite_number(element["opacity"]):
        if not 0 <= element["opacity"] <= 1:
            problems.append(f"{label} opacity must be between 0 and 1")
    if "z_index" in element and (
        isinstance(element["z_index"], bool) or not isinstance(element["z_index"], int)
    ):
        problems.append(f"{label} z_index must be an integer")
    if "group_id" in element and not (
        element["group_id"] is None or isinstance(element["group_id"], str)
    ):
        problems.append(f"{label} group_id must be a string or null")

    for field, allowed in ENUMS.items():
        if field in element and (
            not isinstance(element[field], str) or element[field] not in allowed
        ):
            problems.append(f"{label} has invalid {field}")
    if element_type == "text":
        if not _is_finite_number(element.get("font_size")) or element.get("font_size", 0) < 1:
            problems.append(f"{label} font_size must be a finite number at least 1")
        for field in ("content", "font_family", "color"):
            if field in element and not isinstance(element[field], str):
                problems.append(f"{label} {field} must be a string")
    if element_type == "image" and "asset_id" in element and not isinstance(element["asset_id"], str):
        problems.append(f"{label} asset_id must be a string")

    if isinstance(canvas, Mapping) and not missing:
        try:
            if not is_on_canvas(element, canvas):
                problems.append(f"{label} is outside the target canvas after rotation")
        except (KeyError, TypeError, ValueError):
            pass


def _validate_image_ratio(
    element_id: str,
    original: Mapping[str, Any],
    output: Mapping[str, Any],
    tolerance: float,
    problems: list[str],
) -> None:
    values = (original.get("width"), original.get("height"), output.get("width"), output.get("height"))
    if not all(_is_finite_number(value) and value > 0 for value in values):
        problems.append(f"image '{element_id}' must have positive dimensions for ratio checking")
        return
    source_ratio = original["width"] / original["height"]
    output_ratio = output["width"] / output["height"]
    change = abs(output_ratio / source_ratio - 1)
    if change > tolerance + 1e-12:
        problems.append(
            f"image '{element_id}' aspect ratio changed by {change:.2%}; limit is {tolerance:.2%}"
        )


def _element_id(element: Any) -> str | None:
    if isinstance(element, Mapping) and isinstance(element.get("id"), str):
        return element["id"]
    return None


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )
