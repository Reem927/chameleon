"""Measure and fit text the way the official renderer wraps it.

The renderer measures each character with the real font and wraps greedily
at spaces. We mirror that with Pillow and the brand-kit fonts so the engine
can choose a font size that will actually fit, without importing the
renderer. Unknown font families fall back to a conservative width estimate.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import ImageFont


FONTS_DIR = Path(__file__).resolve().parents[1] / "brand_kit" / "fonts"
# Linux Skia (the Docker renderer) hints glyph advances at the drawn size,
# and Pillow's basic layout reproduces those widths exactly. macOS Skia does
# not hint, so each advance is the larger of the hinted width and the exact
# width, measured at this large size where hinting is negligible.
REFERENCE_SIZE = 1000
DEFAULT_LINE_HEIGHT = 1.2
# The small margin covers glyph overhang and other renderer versions.
WIDTH_SAFETY = 0.98
# Average advance for fonts we cannot measure, in ems. Deliberately wide so
# unknown fonts err toward a smaller size rather than overflowing.
FALLBACK_ADVANCE = 0.68


def fit_text(
    element: Mapping[str, Any], width: float, height: float, *, max_font_size: float
) -> dict[str, Any]:
    """Return a copy sized to ``width`` with the largest font that fits.

    The box height shrinks to the wrapped lines so the text sits where it is
    placed instead of at the top of an oversized box.
    """
    result = deepcopy(dict(element))
    result["width"] = float(width)
    ceiling = max(1.0, float(max_font_size))

    if _fits(result, ceiling, width, height):
        size = ceiling
    else:
        # Search whole hundredths of a pixel so every size tried is one the
        # output can hold exactly and font loads stay cacheable.
        low, high = 100, max(100, math.floor(ceiling * 100))
        while high - low > 1:
            middle = (low + high) // 2
            if _fits(result, middle / 100, width, height):
                low = middle
            else:
                high = middle
        size = low / 100

    result["font_size"] = max(1.0, size)
    result["height"] = line_count(result) * result["font_size"] * _line_height(result)
    return result


def line_count(element: Mapping[str, Any]) -> int:
    """Number of lines the text wraps to at its current size and width."""
    return len(_line_widths(element, float(element["font_size"]), float(element["width"])))


def wrap_width(element: Mapping[str, Any], font_size: float, max_lines: int) -> float:
    """Narrowest box width that wraps the text into at most ``max_lines``.

    Used while planning layouts, so the size is rounded to a hundredth of a
    pixel to keep measurements cacheable. ``fit_text`` makes the exact fit.
    """
    content = str(element.get("content", ""))
    narrowest = _narrowest_wrap(
        content, _element_font_path(element), _planning_size(font_size), max(1, int(max_lines))
    )
    spacing = _letter_spacing(element) * len(content) / max(1, int(max_lines))
    return (narrowest + spacing) / WIDTH_SAFETY


def line_count_at(element: Mapping[str, Any], font_size: float, width: float) -> int:
    """Lines the text needs at about ``font_size`` in a box ``width`` wide."""
    return len(_line_widths(element, _planning_size(font_size), width * WIDTH_SAFETY))


def text_overflow(element: Mapping[str, Any]) -> float:
    """How far wrapped text exceeds its box, as a fraction (0 means it fits)."""
    size = float(element["font_size"])
    width = float(element["width"])
    height = float(element["height"])
    lines = _line_widths(element, size, width)
    spacing = _letter_spacing(element)
    widest = max(line + spacing * count for line, count in lines)
    needed_height = len(lines) * size * _line_height(element)
    overflow_x = max(0.0, widest / max(width, 1e-9) - 1)
    overflow_y = max(0.0, needed_height / max(height, 1e-9) - 1)
    return max(overflow_x, overflow_y)


def _fits(element: Mapping[str, Any], size: float, width: float, height: float) -> bool:
    usable = width * WIDTH_SAFETY
    lines = _line_widths(element, size, usable)
    spacing = _letter_spacing(element)
    widest = max(line + spacing * count for line, count in lines)
    return widest <= usable and len(lines) * size * _line_height(element) <= height + 1e-9


def _line_widths(
    element: Mapping[str, Any], size: float, max_width: float
) -> list[tuple[float, int]]:
    """Greedy wrap matching ``renderer/converter/wrap.py``.

    Returns ``(width, character_count)`` for every line.
    """
    content = str(element.get("content", ""))
    widths = _advances(_element_font_path(element), content, float(size))
    return _greedy_lines(content, widths, max_width)


def _greedy_lines(
    content: str, widths: Sequence[float], max_width: float
) -> list[tuple[float, int]]:
    characters = list(content)
    line_width = 0.0
    last_space = None
    for index, character in enumerate(characters):
        if character == "\n":
            line_width = 0.0
            last_space = None
            continue
        if line_width + widths[index] > max_width and last_space is not None:
            characters[last_space] = "\n"
            line_width = sum(
                widths[j] for j in range(last_space + 1, index + 1) if characters[j] != "\n"
            )
            last_space = None
        else:
            line_width += widths[index]
        if character == " ":
            last_space = index

    lines: list[tuple[float, int]] = []
    width, count = 0.0, 0
    for character, advance in zip(characters, widths):
        if character == "\n":
            lines.append((width, count))
            width, count = 0.0, 0
        else:
            width += advance
            count += 1
    lines.append((width, count))
    return lines


@lru_cache(maxsize=8192)
def _narrowest_wrap(content: str, font_path: Path | None, size: float, max_lines: int) -> float:
    advances = _advances(font_path, content, size)
    low = max(_widest_word(content, advances), 1e-6)
    high = max(sum(advances), low) + 1.0
    if len(_greedy_lines(content, advances, low)) <= max_lines:
        return low
    for _ in range(30):
        middle = (low + high) / 2
        if len(_greedy_lines(content, advances, middle)) <= max_lines:
            high = middle
        else:
            low = middle
    return high


def _widest_word(content: str, advances: Sequence[float]) -> float:
    longest = word = 0.0
    for character, advance in zip(content, advances):
        if character in " \n":
            word = 0.0
            continue
        word += advance
        longest = max(longest, word)
    return longest


def _planning_size(size: float) -> float:
    return max(0.01, round(float(size), 2))


def _element_font_path(element: Mapping[str, Any]) -> Path | None:
    return _font_path(
        str(element.get("font_family", "")),
        element.get("font_weight") == "bold",
        element.get("font_style") == "italic",
    )


@lru_cache(maxsize=16384)
def _advances(font_path: Path | None, content: str, size: float) -> tuple[float, ...]:
    """Per-character advances at ``size``, never below the exact width."""
    if font_path is None:
        return tuple(0.0 if character == "\n" else FALLBACK_ADVANCE * size for character in content)
    exact_font = _load_font(font_path, REFERENCE_SIZE)
    hinted_font = _load_font(font_path, size)
    return tuple(
        max(hinted_font.getlength(character), exact_font.getlength(character) * size / REFERENCE_SIZE)
        for character in content
    )


@lru_cache(maxsize=1024)
def _load_font(font_path: Path, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path), size, layout_engine=ImageFont.Layout.BASIC)


def _font_path(family: str, bold: bool, italic: bool) -> Path | None:
    faces = _font_faces().get(_normalize_family(family))
    if not faces:
        return None
    wanted = ("bold" if bold else "") + ("italic" if italic else "") or "regular"
    for style in (wanted, "bold" if bold else "regular", "regular"):
        if style in faces:
            return faces[style]
    return faces[sorted(faces)[0]]


@lru_cache(maxsize=1)
def _font_faces() -> dict[str, dict[str, Path]]:
    """Map normalized family names to their style files, e.g. ``SolsticeSans-Bold.ttf``."""
    faces: dict[str, dict[str, Path]] = {}
    if not FONTS_DIR.is_dir():
        return faces
    for path in sorted(FONTS_DIR.iterdir()):
        if path.suffix.lower() not in {".ttf", ".otf"}:
            continue
        family, _, suffix = path.stem.partition("-")
        suffix = suffix.lower() or "regular"
        bold = "bold" in suffix
        italic = "italic" in suffix
        style = ("bold" if bold else "") + ("italic" if italic else "") or "regular"
        faces.setdefault(_normalize_family(family), {})[style] = path
    return faces


def _normalize_family(family: str) -> str:
    return re.sub(r"[^a-z0-9]", "", family.lower())


def _line_height(element: Mapping[str, Any]) -> float:
    return float(element.get("line_height", DEFAULT_LINE_HEIGHT))


def _letter_spacing(element: Mapping[str, Any]) -> float:
    return float(element.get("letter_spacing", 0.0))
